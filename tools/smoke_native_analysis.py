"""Offline native sandbox acceptance. Always copies the supplied credential-free runtime."""
import argparse
import asyncio
import base64
import hashlib
import json
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path

from epivra.analysis import DEFAULTS
from epivra.native_analysis import NativeSandbox, regular


async def verify(runtime, scientific=False):
    with tempfile.TemporaryDirectory(prefix="epivra-native-acceptance-") as folder:
        root = Path(folder)
        isolated_runtime = root / "runtime"
        shutil.copytree(runtime, isolated_runtime, symlinks=True)
        secret = root / "fake-secret.txt"
        secret.write_text("FAKE-TEST-SECRET", encoding="utf-8")
        sandbox = NativeSandbox(root, isolated_runtime)
        passed = []
        async def run(name, code, **limits):
            source = root / ("source-" + name)
            source.mkdir()
            (source / "data").mkdir()
            (source / "data/sample.csv").write_text("x\n1\n2\n3\n", encoding="utf-8")
            (source / "analysis.py").write_text(code, encoding="utf-8")
            job = hashlib.sha256(name.encode()).hexdigest()
            try:
                return await sandbox.run(job, source, {**DEFAULTS, **limits}, True, lambda: None)
            finally:
                await sandbox.cleanup(job)
        normal = await run("normal", "import csv,statistics,json\nprint('中文日志')\n"
                           "values=[float(r['x']) for r in csv.DictReader((INPUT_DIR/'sample.csv').open())]\n"
                           "(OUTPUT_DIR/'summary.json').write_text(json.dumps({'mean':statistics.mean(values)}))\n")
        assert normal["status"] == "succeeded", normal
        assert json.loads(base64.b64decode(normal["files"][0]["data"])) == {"mean": 2.0}
        assert "中文日志" in normal["log"], normal
        passed.append("authorized-input-computation-output")
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener6 = socket.socket(socket.AF_INET6)
        listener6.bind(("::1", 0))
        listener6.listen()
        for endpoint in (listener, listener6):
            with socket.create_connection(endpoint.getsockname()[:2], timeout=2):
                peer, _ = endpoint.accept()
                peer.close()
        try:
            code = f"SECRET={str(secret)!r}\nRUNTIME={str(isolated_runtime)!r}\nPORT={listener.getsockname()[1]}\nPORT6={listener6.getsockname()[1]}\n"
            code += """import pathlib,socket,subprocess,sys,json
blocked=[]
def deny(name,fn):
    try: fn()
    except (OSError,PermissionError): blocked.append(name)
    else: raise AssertionError('isolation failed: '+name)
deny('outside-read',lambda:pathlib.Path(SECRET).read_text())
deny('outside-write',lambda:pathlib.Path(SECRET).write_text('bad'))
deny('input-write',lambda:(INPUT_DIR/'sample.csv').write_text('bad'))
deny('runtime-write',lambda:(pathlib.Path(RUNTIME)/'bad-marker').write_text('bad'))
deny('network-v4',lambda:socket.create_connection(('127.0.0.1',PORT),timeout=1))
deny('network-v6',lambda:socket.create_connection(('::1',PORT6),timeout=1))
deny('child-process',lambda:subprocess.Popen([sys.executable,'-I','-c','pass']))
(OUTPUT_DIR/'blocked.json').write_text(json.dumps(blocked))
"""
            if sys.platform == "win32":
                profile_probe = """
import ctypes as c
from ctypes import wintypes as w
security=c.WinDLL('advapi32')
token=w.HANDLE()
security.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)]
assert security.OpenProcessToken(w.HANDLE(-1),8,c.byref(token))
security.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)]
needed=w.DWORD()
security.GetTokenInformation(token,31,None,0,c.byref(needed))
information=c.create_string_buffer(needed.value)
assert security.GetTokenInformation(token,31,information,needed,c.byref(needed))
sid=c.cast(information,c.POINTER(c.c_void_p))[0]
userenv=c.WinDLL('userenv')
sid_text=w.LPWSTR()
security=c.WinDLL('advapi32')
security.ConvertSidToStringSidW.argtypes=[c.c_void_p,c.POINTER(w.LPWSTR)]
assert security.ConvertSidToStringSidW(sid,c.byref(sid_text))
profile=w.LPWSTR()
userenv.GetAppContainerFolderPath.argtypes=[w.LPCWSTR,c.POINTER(w.LPWSTR)]
assert userenv.GetAppContainerFolderPath(sid_text,c.byref(profile))>=0
profile_root=pathlib.Path(profile.value)
assert profile_root.is_dir()
assert profile_root.parent.is_dir()
assert not (profile_root/'unmonitored-directory').exists()
for name,operation in [
    ('implicit-profile-root-write',lambda:(profile_root/'unmonitored.txt').write_text('bad')),
    ('implicit-profile-parent-write',lambda:(profile_root.parent/'unmonitored.txt').write_text('bad')),
    ('implicit-profile-directory-create',lambda:(profile_root/'unmonitored-directory').mkdir()),
]:
    try:
        operation()
    except PermissionError as error:
        assert error.errno==13 and error.winerror in {None,5},error
        blocked.append(name)
    else:
        raise AssertionError('implicit profile remains writable: '+name+' '+str(profile_root))
security.SetNamedSecurityInfoW.argtypes=[w.LPWSTR,w.DWORD,w.DWORD,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p]
security.SetNamedSecurityInfoW.restype=w.DWORD
assert security.SetNamedSecurityInfoW(str(profile_root),1,4,None,None,None,None)==5
blocked.append('implicit-profile-acl-change')

"""
                code = code.replace("(OUTPUT_DIR/'blocked.json')",
                                    profile_probe + chr(10) + "(OUTPUT_DIR/'blocked.json')")
            result = await run("isolation", code)
            assert result["status"] == "succeeded", result
            blocked = json.loads(base64.b64decode(result["files"][0]["data"]))
            assert len(blocked) == (11 if sys.platform == "win32" else 7), blocked
            assert secret.read_text(encoding="utf-8") == "FAKE-TEST-SECRET"
            passed.extend(blocked)
        finally:
            listener.close()
            listener6.close()
        result = await run("timeout", "while True: pass\n", timeout=1)
        assert result["status"] == "timeout", result
        passed.append("wall-timeout")
        result = await run("log-limit", "import os\nwhile True: os.write(1,b'x'*65536)\n")
        assert result["status"] == "resource_limit", result
        passed.append("bounded-log")
        result = await run("memory-limit", """
try:
    value=bytearray(256*1024*1024)
except MemoryError:
    (OUTPUT_DIR/'memory-limit.txt').write_text('blocked')
else:
    raise AssertionError('memory limit not enforced')
""", memory_mb=64)
        assert result["status"] == "succeeded", result
        assert base64.b64decode(result["files"][0]["data"]) == b"blocked", result
        passed.append("allocation-exceeds-memory-limit")
        try:
            result = await run("scratch-limit", """
import os,time
from pathlib import Path
try:
    (Path(os.environ['TMPDIR'])/'oversize.bin').write_bytes(b'x'*(2*1024*1024))
except OSError:
    (OUTPUT_DIR/'scratch-limit.txt').write_text('blocked')
else:
    time.sleep(30)
""", output_mb=1)
        except ValueError as error:
            assert "limit exceeded" in str(error), error
        else:
            assert result["status"] == "succeeded", result
            assert any(item["name"] == "scratch-limit.txt" for item in result["files"]), result
        passed.append("scratch-monitor-limit")
        source = root / "source-cancel"
        source.mkdir()
        (source / "analysis.py").write_text("while True: pass", encoding="utf-8")
        job = hashlib.sha256(b"cancel").hexdigest()
        task = asyncio.create_task(sandbox.run(job, source, DEFAULTS, True, lambda: None))
        try:
            async with asyncio.timeout(30):
                while job not in sandbox.active:
                    if task.done():
                        await task
                    await asyncio.sleep(0.02)
            task.cancel()
            result = await asyncio.gather(task, return_exceptions=True)
            assert isinstance(result[0], asyncio.CancelledError), result
            assert job not in sandbox.active
        finally:
            await sandbox.cleanup(job)
        passed.append("cancel-reaps-worker")
        # Collector rejects a hard link even if a trusted test creates it.
        linked = root / "hard-link"
        import os
        os.link(secret, linked)
        try:
            regular(linked)
        except ValueError:
            passed.append("collector-rejects-hard-links")
        else:
            raise AssertionError("hard link accepted")
        if scientific:
            result = await run("scientific", """
import numpy as np,pandas as pd,matplotlib,scipy.stats,statsmodels.api as sm,seaborn
from sklearn.linear_model import LinearRegression
from PIL import Image
matplotlib.use('Agg')
import matplotlib.pyplot as plt
frame=pd.read_csv(INPUT_DIR/'sample.csv')
assert frame.x.mean()==2
assert np.isclose(scipy.stats.describe(frame.x).mean,2)
x=np.arange(5).reshape(-1,1); y=2*x.ravel()+1
assert np.allclose(LinearRegression().fit(x,y).predict(x),y)
assert np.allclose(sm.OLS(y,sm.add_constant(x)).fit().params,[1,2])
frame.to_excel(OUTPUT_DIR/'table.xlsx',index=False)
assert pd.read_excel(OUTPUT_DIR/'table.xlsx').equals(frame)
frame.to_parquet(OUTPUT_DIR/'table.parquet',index=False)
assert pd.read_parquet(OUTPUT_DIR/'table.parquet').equals(frame)
plt.plot(np.arange(3));plt.savefig(OUTPUT_DIR/'chart.png');plt.close()
with Image.open(OUTPUT_DIR/'chart.png') as image: image.verify()
""")
            assert result["status"] == "succeeded", result
            files = {item["name"]: base64.b64decode(item["data"]) for item in result["files"]}
            assert files["chart.png"].startswith(bytes.fromhex("89504e470d0a1a0a")), files.keys()
            assert {"table.xlsx", "table.parquet"} <= files.keys(), files.keys()
            passed.append("scientific-statistics-regression-excel-parquet-plot")
        return {"platform": sys.platform, "passed": passed, "configuration": {k: v for k, v in DEFAULTS.items() if k not in {"image", "pids"}},
                "case_overrides": {"timeout": {"timeout": 1}, "memory-limit": {"memory_mb": 64},
                                   "scratch-limit": {"output_mb": 1}},
                "limits": "Aggregate scratch/output bytes use monitoring, not a hard filesystem quota."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--scientific", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    result = asyncio.run(verify(args.runtime.resolve(), args.scientific))
    result["seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
