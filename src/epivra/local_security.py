"""Private local state permissions; no authority over user source directories."""

import os
import stat
from pathlib import Path


def protect(path: Path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("private state must not be a link or reparse point")
    if os.name != "nt":
        if info.st_uid != os.getuid():
            raise PermissionError("private state must belong to the current user")
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(pointer),
        ctypes.POINTER(wintypes.DWORD),
    ]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    api.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, pointer]
    api.SetFileSecurityW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    api.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(pointer),
        pointer,
        pointer,
        pointer,
        ctypes.POINTER(pointer),
    ]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    api.OpenProcessToken.restype = wintypes.BOOL
    api.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        pointer,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    api.GetTokenInformation.restype = wintypes.BOOL
    api.EqualSid.argtypes = [pointer, pointer]
    api.EqualSid.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    owner, original, token = pointer(), pointer(), wintypes.HANDLE()
    error = api.GetNamedSecurityInfoW(
        str(path), 1, 1, ctypes.byref(owner), None, None, None, ctypes.byref(original)
    )
    if error:
        raise ctypes.WinError(error)
    try:
        if not api.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            size = wintypes.DWORD()
            api.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
            buffer = ctypes.create_string_buffer(size.value)
            if not api.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            user_sid = ctypes.cast(buffer, ctypes.POINTER(pointer))[0]
            if not api.EqualSid(owner, user_sid):
                raise PermissionError("private state must belong to the current user")
        finally:
            kernel.CloseHandle(token)
    finally:
        kernel.LocalFree(original)
    descriptor = pointer()
    inherit = "OICI" if path.is_dir() else ""
    sddl = f"D:P(A;{inherit};FA;;;OW)(A;{inherit};FA;;;SY)"
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), None
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not api.SetFileSecurityW(str(path), 0x80000004, descriptor):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def private_directory(path: Path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    protect(path)
    # Existing children may carry explicit ACLs that do not inherit the new DACL.
    for root, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            protect(Path(root) / name)
