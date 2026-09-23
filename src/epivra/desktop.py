"""Desktop lifecycle: one workspace, one control window, an authenticated Web UI."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from importlib.metadata import version
from pathlib import Path

from . import host
from .cli_settings import write
from .components import Components
from .local_security import exclusive_lock, private_directory
from .platform_paths import desktop_root
from .webui import App, Server


def endpoint(root):
    record = json.loads((root / ".epivra/desktop.json").read_text(encoding="utf-8"))
    port = record["port"]
    if type(port) is not int or not 0 < port < 65536:
        raise ValueError("invalid desktop endpoint")
    origin = f"http://127.0.0.1:{port}"
    return record, origin


def contact(root, stop=False):
    record, origin = endpoint(root)
    request = urllib.request.Request(
        origin + ("/api/desktop/quit" if stop else "/api/settings"),
        data=b"{}" if stop else None,
        headers={"X-Research-Token": record["token"],
                 "Content-Type": "application/json", "Origin": origin},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=2) as response:
        result = json.load(response)
    if not stop and result["root"] != str(root.resolve()):
        raise ValueError("desktop workspace mismatch")
    return record, origin


class Desktop:
    def __init__(self, root, no_browser=False):
        self.root = root.resolve()
        self.no_browser = no_browser
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.done = threading.Event()
        self.error = None
        self.url = None
        self.components = Components(self.root)

    def request_shutdown(self):
        self.components.close()
        self.stop.set()
        return {"stopping": True}

    def run(self):
        server = None
        serving = None
        pointer = self.root / ".epivra/desktop.json"
        host_started = False
        try:
            app = App(self.root)
            app.components = self.components
            app.desktop = self
            server = Server(app)
            asyncio.run(host.start(self.root, wait=None, cancel=self.stop))
            host_started = True
            self.url = server.url
            serving = threading.Thread(target=server.serve_forever, daemon=True)
            serving.start()
            write(pointer, json.dumps({"port": server.server_port, "token": server.token,
                                       "version": version("epivra")}))
            self.ready.set()
            if not self.no_browser and not self.stop.is_set():
                webbrowser.open(self.url)
            self.stop.wait()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.error = str(exc)
            traceback.print_exc()
        finally:
            if host_started:
                try:
                    asyncio.run(host.send(self.root, {"action": "shutdown"}))
                    deadline = time.monotonic() + 30
                    while (self.root / ".epivra/host.json").exists():
                        if time.monotonic() > deadline:
                            raise TimeoutError("Research host has not stopped; check host.log before upgrading.")
                        time.sleep(0.1)
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    self.error = str(exc)
                    traceback.print_exc()
            if serving:
                server.shutdown()
                serving.join()
            if server:
                server.server_close()
            pointer.unlink(missing_ok=True)
            self.done.set()


def window(desktop):
    import tkinter as tk
    from tkinter import messagebox, ttk

    chinese = (os.environ.get("EPIVRA_LANG") or __import__("locale").getlocale()[0] or "en").startswith("zh")
    def text(zh, en):
        return zh if chinese else en

    view = tk.Tk()
    view.title("Epivra")
    view.geometry("540x270")
    view.minsize(480, 250)
    frame = ttk.Frame(view, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Epivra", font=("", 22, "bold")).pack(anchor="w")
    status = tk.StringVar(value=text("正在启动…", "Starting…"))
    ttk.Label(frame, textvariable=status, wraplength=475).pack(anchor="w", pady=12)
    ttk.Label(frame, text=text("关闭浏览器后研究继续。退出应用会停止后台研究。",
                              "Closing the browser keeps research running. Quit stops the research host."),
              wraplength=475).pack(anchor="w")
    buttons = ttk.Frame(frame)
    buttons.pack(anchor="w", pady=20)
    open_button = ttk.Button(buttons, text=text("打开工作台", "Open workbench"),
                             command=lambda: webbrowser.open(desktop.url), state="disabled")
    open_button.pack(side="left", padx=(0, 8))

    def open_folder():
        if sys.platform == "win32":
            os.startfile(desktop.root)
        else:
            subprocess.Popen(["open", str(desktop.root)])

    ttk.Button(buttons, text=text("数据文件夹", "Data folder"), command=open_folder).pack(side="left", padx=(0, 8))

    def quit_app():
        if desktop.done.is_set():
            view.destroy()
            return
        if not messagebox.askokcancel("Epivra", text(
                "退出将停止后台研究，成果会保留，下次打开可恢复。", 
                "Quit stops background research. Saved work will be available when you reopen."), parent=view):
            return
        try:
            desktop.request_shutdown()
            status.set(text("正在安全退出…", "Stopping safely…"))
            open_button.configure(state="disabled")
        except ValueError as exc:
            messagebox.showinfo("Epivra", str(exc), parent=view)

    ttk.Button(buttons, text=text("退出", "Quit"), command=quit_app).pack(side="left")
    view.protocol("WM_DELETE_WINDOW", quit_app)
    worker = threading.Thread(target=desktop.run, daemon=True)
    worker.start()
    notified = False

    def poll():
        nonlocal notified
        if desktop.done.is_set():
            if desktop.error and not notified:
                notified = True
                messagebox.showerror("Epivra", desktop.error + "\n\n" + str(desktop.root / ".epivra/desktop.log"), parent=view)
            view.destroy()
            return
        if desktop.ready.is_set() and not desktop.stop.is_set():
            status.set(text("正在运行。可以打开浏览器工作台。", "Running. Open the workbench in your browser."))
            open_button.configure(state="normal")
        view.after(200, poll)

    view.after(200, poll)
    view.mainloop()
    if not desktop.done.is_set():
        desktop.stop.set()
        worker.join(35)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Epivra desktop")
    parser.add_argument("--root", type=Path, default=desktop_root())
    parser.add_argument("--headless", action="store_true", help="Run without the control window (diagnostics)")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--shutdown", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.shutdown:
        contact(root, stop=True)
        return
    root.mkdir(parents=True, exist_ok=True)
    state = root / ".epivra"
    private_directory(state)
    try:
        lock = exclusive_lock(state / "desktop.lock")
    except OSError:
        for _ in range(100):
            try:
                record, origin = contact(root)
                if record.get("version") != version("epivra"):
                    raise RuntimeError("Quit the running Epivra before opening the new version.")
                if not args.no_browser:
                    webbrowser.open(origin + "/#token=" + record["token"])
                return
            except (OSError, ValueError, KeyError):
                time.sleep(0.1)
        raise RuntimeError("Epivra is already starting or stopping. Try again shortly.") from None
    log_path = state / "desktop.log"
    if log_path.exists() and log_path.stat().st_size > 2 * 1024 * 1024:
        log_path.replace(state / "desktop.previous.log")
    try:
        with log_path.open("a", encoding="utf-8", buffering=1) as log:
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = log
            desktop = Desktop(root, args.no_browser)
            try:
                if args.headless:
                    desktop.run()
                else:
                    window(desktop)
                if desktop.error:
                    raise RuntimeError(desktop.error)
            except BaseException:
                traceback.print_exc()
                raise
            finally:
                sys.stdout, sys.stderr = old_out, old_err
    finally:
        lock.close()


if __name__ == "__main__":
    main()
