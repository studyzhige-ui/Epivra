"""Windows LPAC launch boundary. Never launches an unrestricted analysis process."""
import ctypes as c
import os
import subprocess
import threading
from ctypes import wintypes as w
from pathlib import Path

from .local_security import private_directory

P = c.c_void_p
SIZE = c.c_size_t
ACL_LOCK = threading.Lock()
kernel = c.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
security = c.WinDLL("advapi32", use_last_error=True) if os.name == "nt" else None
userenv = c.WinDLL("userenv", use_last_error=True) if os.name == "nt" else None


class Startup(c.Structure):
    _fields_ = [("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR),
                ("title", w.LPWSTR), ("x", w.DWORD), ("y", w.DWORD),
                ("xs", w.DWORD), ("ys", w.DWORD), ("xc", w.DWORD), ("yc", w.DWORD),
                ("fill", w.DWORD), ("flags", w.DWORD), ("show", w.WORD),
                ("reserved_size", w.WORD), ("reserved_ptr", P),
                ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE)]


class StartupEx(c.Structure):
    _fields_ = [("base", Startup), ("attributes", P)]


class ProcessInfo(c.Structure):
    _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE), ("pid", w.DWORD), ("tid", w.DWORD)]


class Capabilities(c.Structure):
    _fields_ = [("sid", P), ("capabilities", P), ("count", w.DWORD), ("reserved", w.DWORD)]


class SidAttributes(c.Structure):
    _fields_ = [("sid", P), ("attributes", w.DWORD)]


class BasicLimits(c.Structure):
    _fields_ = [("process_time", c.c_longlong), ("job_time", c.c_longlong),
                ("flags", w.DWORD), ("min_working", SIZE), ("max_working", SIZE),
                ("active", w.DWORD), ("affinity", SIZE), ("priority", w.DWORD),
                ("scheduling", w.DWORD)]


class ExtendedLimits(c.Structure):
    _fields_ = [("basic", BasicLimits), ("io", c.c_ulonglong * 6),
                ("process_memory", SIZE), ("job_memory", SIZE),
                ("peak_process", SIZE), ("peak_job", SIZE)]


def api(dll, name, args, result=w.BOOL):
    fn = getattr(dll, name)
    fn.argtypes, fn.restype = args, result
    return fn


def checked(value):
    if not value:
        raise c.WinError(c.get_last_error())
    return value


class WindowsProcess:
    """One LPAC SID and a non-inherited kill-on-close Job per execution."""
    def __init__(self, command, readonly, writable, cwd, env, config, moniker):
        import msvcrt
        self.handles = []
        self.sid = P()
        self.profile = moniker
        self.granted = []
        self.capability_allocations = []
        self.process = None
        self.job = None
        self.output = None
        self._close = api(kernel, "CloseHandle", [w.HANDLE])
        self._wait = api(kernel, "WaitForSingleObject", [w.HANDLE, w.DWORD], w.DWORD)
        self._exit = api(kernel, "GetExitCodeProcess", [w.HANDLE, c.POINTER(w.DWORD)])
        self._terminate = api(kernel, "TerminateJobObject", [w.HANDLE, w.UINT])
        self._delete = api(userenv, "DeleteAppContainerProfile", [w.LPCWSTR], c.c_long)
        attrs = None
        read_fd = write_fd = null_fd = None
        try:
            hr = api(userenv, "CreateAppContainerProfile",
                     [w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, P, w.DWORD, c.POINTER(P)], c.c_long)(
                         moniker, moniker, "Epivra restricted analysis", None, 0, c.byref(self.sid))
            if hr < 0:
                raise OSError(f"Cannot create analysis AppContainer: 0x{hr & 0xffffffff:08x}")
            text_sid = w.LPWSTR()
            checked(api(security, "ConvertSidToStringSidW", [P, c.POINTER(w.LPWSTR)])(self.sid, c.byref(text_sid)))
            self.sid_text = text_sid.value
            api(kernel, "LocalFree", [P], P)(c.cast(text_sid, P))
            # AppContainer profiles otherwise create an implicit writable tree
            # outside our monitored outputs/scratch. Remove that default grant.
            profile_path = w.LPWSTR()
            hr = api(userenv, "GetAppContainerFolderPath",
                     [w.LPCWSTR, c.POINTER(w.LPWSTR)], c.c_long)(self.sid_text, c.byref(profile_path))
            if hr < 0:
                raise OSError("Cannot resolve private analysis profile")
            try:
                profile_root = Path(profile_path.value).parent
                if profile_root.name.casefold() != moniker.casefold():
                    raise ValueError("Unexpected private analysis profile path")
                private_directory(profile_root)
                self._acl(profile_root, "/grant", f"*{self.sid_text}:RX")
            finally:
                api(c.WinDLL("ole32"), "CoTaskMemFree", [P], None)(c.cast(profile_path, P))
            # Only application-owned, credential-free runtime and per-job copies.
            for path, access in [(p, "RX") for p in readonly] + [(p, "M") for p in writable]:
                # Protected input/runtime files do not inherit their directory's
                # ACL. Apply explicit RX to existing entries; new output children
                # instead inherit write access from their empty job directory.
                rights = "RX" if access == "RX" else "(OI)(CI)M"
                self._acl(path, "/grant", f"*{self.sid_text}:{rights}")
                if access == "RX":
                    self.granted.append(path)
            for path in writable:
                self._acl(path, "/setintegritylevel", "(OI)(CI)L")
            self.job = checked(api(kernel, "CreateJobObjectW", [P, w.LPCWSTR], w.HANDLE)(None, None))
            self.handles.append(self.job)
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000 | 0x100 | 0x8  # KILL_ON_CLOSE, PROCESS_MEMORY, ACTIVE_PROCESS
            limits.basic.active = 1
            limits.process_memory = config["memory_mb"] * 1024 * 1024
            set_job = api(kernel, "SetInformationJobObject", [w.HANDLE, c.c_int, P, w.DWORD])
            checked(set_job(self.job, 9, c.byref(limits), c.sizeof(limits)))
            ui = w.DWORD(255)
            checked(set_job(self.job, 4, c.byref(ui), c.sizeof(ui)))
            cpu = (w.DWORD * 2)(5, min(10000, max(1, int(10000 * config["cpus"] / (os.cpu_count() or 1)))))
            checked(set_job(self.job, 15, c.byref(cpu), c.sizeof(cpu)))
            # Explicit inherited handle allowlist; no credentials, database or Job handle.
            read_fd, write_fd = os.pipe()
            null_fd = os.open(os.devnull, os.O_RDONLY)
            for fd in (write_fd, null_fd):
                os.set_inheritable(fd, True)
            output_handle, input_handle = msvcrt.get_osfhandle(write_fd), msvcrt.get_osfhandle(null_fd)
            size = SIZE()
            initialize = api(kernel, "InitializeProcThreadAttributeList", [P, w.DWORD, w.DWORD, c.POINTER(SIZE)])
            initialize(None, 4, 0, c.byref(size))
            attrs = c.create_string_buffer(size.value)
            checked(initialize(attrs, 4, 0, c.byref(size)))
            update = api(kernel, "UpdateProcThreadAttribute", [P, w.DWORD, SIZE, P, SIZE, P, P])
            # The CPython loader requires system registry reads in LPAC. This
            # capability is separate from network and COM; neither is granted.
            groups, values = P(), P()
            group_count, value_count = w.DWORD(), w.DWORD()
            derive = api(c.WinDLL("kernelbase", use_last_error=True), "DeriveCapabilitySidsFromName",
                         [w.LPCWSTR, c.POINTER(P), c.POINTER(w.DWORD), c.POINTER(P), c.POINTER(w.DWORD)])
            checked(derive("registryRead", c.byref(groups), c.byref(group_count), c.byref(values), c.byref(value_count)))
            entries = []
            for array, count in ((groups, group_count), (values, value_count)):
                for i in range(count.value):
                    value = c.cast(array, c.POINTER(P))[i]
                    self.capability_allocations.append(value)
                    if array is values:
                        entries.append(SidAttributes(value, 4))
                self.capability_allocations.append(array)
            entries = (SidAttributes * len(entries))(*entries)
            caps = Capabilities(self.sid, c.cast(entries, P), len(entries), 0)
            lpac = w.DWORD(1)
            inherited = (w.HANDLE * 2)(output_handle, input_handle)
            jobs = (w.HANDLE * 1)(self.job)
            for attribute, value in ((0x20009, caps), (0x2000f, lpac), (0x20002, inherited), (0x2000d, jobs)):
                checked(update(attrs, 0, attribute, c.byref(value), c.sizeof(value), None, None))
            startup = StartupEx()
            startup.base.cb = c.sizeof(startup)
            startup.base.flags = 0x100
            startup.base.stdin = input_handle
            startup.base.stdout = startup.base.stderr = output_handle
            startup.attributes = c.cast(attrs, P)
            info = ProcessInfo()
            environment = c.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(env.items())) + "\0\0")
            create = api(kernel, "CreateProcessW",
                         [w.LPCWSTR, w.LPWSTR, P, P, w.BOOL, w.DWORD, P, w.LPCWSTR, P, P])
            checked(create(command[0], c.create_unicode_buffer(subprocess.list2cmdline(command)),
                           None, None, True, 0x80000 | 0x400 | 0x4 | 0x08000000,
                           environment, str(cwd), c.byref(startup), c.byref(info)))
            self.process = info.process
            self.handles.extend([info.process, info.thread])
            self.pid = info.pid  # Job membership was atomic with process creation.
            self.thread = info.thread
            self.output = os.fdopen(read_fd, "rb", buffering=0)
            read_fd = None
        except BaseException:
            self.close()
            raise
        finally:
            if attrs is not None:
                api(kernel, "DeleteProcThreadAttributeList", [P], None)(attrs)
            for fd in (read_fd, write_fd, null_fd):
                if fd is not None:
                    os.close(fd)

    def _acl(self, path, action, value):
        with ACL_LOCK:
            result = subprocess.run(
                [os.path.join(os.environ["SYSTEMROOT"], "System32", "icacls.exe"),
                 str(path), action, value, "/T", "/Q"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=90)
        if result.returncode:
            raise OSError("Cannot establish private analysis filesystem permissions")

    def start(self):
        if api(kernel, "ResumeThread", [w.HANDLE], w.DWORD)(self.thread) == 0xffffffff:
            raise c.WinError(c.get_last_error())

    def poll(self):
        if self._wait(self.process, 0) == 258:
            return None
        code = w.DWORD()
        checked(self._exit(self.process, c.byref(code)))
        return code.value

    def kill(self):
        if self.job:
            checked(self._terminate(self.job, 1))

    def close(self):
        if self.job:
            checked(self._terminate(self.job, 1))
        if self.process and self._wait(self.process, 15000) != 0:
            raise OSError("Could not verify native analysis process termination")
        for handle in reversed(self.handles):
            self._close(handle)
        self.handles.clear()
        self.job = self.process = None
        failures = []
        for path in self.granted:
            try:
                self._acl(path, "/remove:g", f"*{self.sid_text}")
            except OSError:
                failures.append(str(path))
        self.granted = [path for path in self.granted if str(path) in failures]
        if self.sid and not failures:
            hr = self._delete(self.profile)
            if hr < 0 and (hr & 0xffffffff) not in {0x80070002, 0x80070003}:
                raise OSError("Could not delete native analysis profile")
            api(security, "FreeSid", [P], P)(self.sid)
            self.sid = P()
        for allocation in self.capability_allocations:
            api(kernel, "LocalFree", [P], P)(allocation)
        self.capability_allocations.clear()
        if failures:
            raise OSError("Analysis permission cleanup failed")

def cleanup_profile(moniker, paths):
    """Revoke a crashed host's deterministic per-job SID; never launch recovery code."""
    sid = P()
    derive = api(userenv, "DeriveAppContainerSidFromAppContainerName", [w.LPCWSTR, c.POINTER(P)], c.c_long)
    if derive(moniker, c.byref(sid)) < 0:
        raise OSError("Cannot derive native analysis recovery identity")
    value = w.LPWSTR()
    try:
        checked(api(security, "ConvertSidToStringSidW", [P, c.POINTER(w.LPWSTR)])(sid, c.byref(value)))
        holder = WindowsProcess.__new__(WindowsProcess)
        for path in paths:
            if path.exists():
                holder._acl(path, "/remove:g", "*" + value.value)
        hr = api(userenv, "DeleteAppContainerProfile", [w.LPCWSTR], c.c_long)(moniker)
        if hr < 0 and (hr & 0xffffffff) not in {0x80070002, 0x80070003}:
            raise OSError("Cannot delete native analysis recovery profile")
    finally:
        if value:
            api(kernel, "LocalFree", [P], P)(c.cast(value, P))
        api(security, "FreeSid", [P], P)(sid)
