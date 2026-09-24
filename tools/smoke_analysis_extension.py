"""Verify real overlapped IO in a disposable child using loopback only."""
import argparse
import subprocess
from pathlib import Path


def exercise():
    import _overlapped
    import faulthandler
    faulthandler.dump_traceback_later(15, exit=True)
    import asyncio
    import concurrent.futures
    import msvcrt
    import socket
    import struct
    import tempfile

    def invalid():
        for method, arguments in [
            ("AcceptEx", (0, 0)), ("ConnectEx", (0, ("127.0.0.1", 1))),
            ("DisconnectEx", (0, 0)), ("TransmitFile", (0, 0, 0, 0, 1, 0, 0)),
        ]:
            operation = _overlapped.Overlapped()
            for _ in range(2):
                try:
                    getattr(operation, method)(*arguments)
                except OSError as error:
                    assert error.winerror == 10038, (method, error)
                else:
                    raise AssertionError("Invalid socket accepted")
    invalid()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: invalid(), range(32)))
    with socket.socket() as server, socket.socket() as client, socket.socket() as accepted:
        server.bind(("127.0.0.1", 0))
        server.listen()
        client.bind(("127.0.0.1", 0))
        accept = _overlapped.Overlapped()
        accept.AcceptEx(server.fileno(), accepted.fileno())
        connect = _overlapped.Overlapped()
        connect.ConnectEx(client.fileno(), server.getsockname())
        connect.getresult(True)
        accept.getresult(True)
        client.setsockopt(socket.SOL_SOCKET, _overlapped.SO_UPDATE_CONNECT_CONTEXT, 0)
        accepted.setsockopt(socket.SOL_SOCKET, _overlapped.SO_UPDATE_ACCEPT_CONTEXT,
                            struct.pack("P", server.fileno()))
        accepted.settimeout(5)
        with tempfile.TemporaryFile() as stream:
            payload = b"Epivra overlapped runtime regression"
            stream.write(payload)
            stream.flush()
            stream.seek(0)
            transmit = _overlapped.Overlapped()
            transmit.TransmitFile(client.fileno(), msvcrt.get_osfhandle(stream.fileno()),
                                  0, 0, len(payload), 0, 0)
            transmit.getresult(True)
            assert accepted.recv(1024) == payload
        disconnect = _overlapped.Overlapped()
        disconnect.DisconnectEx(client.fileno(), 0)
        disconnect.getresult(True)
        with socket.socket() as pending:
            operation = _overlapped.Overlapped()
            operation.AcceptEx(server.fileno(), pending.fileno())
            operation.cancel()
            try:
                operation.getresult(True)
            except OSError as error:
                assert error.winerror == 995, error
            else:
                raise AssertionError("Cancelled accept completed unexpectedly")
    # Exercise separate interpreter module lifecycles concurrently.
    import _xxsubinterpreters as interpreters
    def interpreter_case(_):
        identity = interpreters.create()
        try:
            interpreters.run_string(
                identity, "import asyncio, _overlapped; o=_overlapped.Overlapped(); "
                "assert not o.pending")
        finally:
            interpreters.destroy(identity)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(interpreter_case, range(8)))
    assert asyncio.iscoroutinefunction(exercise) is False
    faulthandler.cancel_dump_traceback_later()
    print("PASS: import, four socket operations, invalid-handle retry, cancellation, threads, interpreters")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if args.child:
        exercise()
    elif args.runtime:
        subprocess.run([str(args.runtime / "python.exe"), "-I", "-X", "utf8",
                        str(Path(__file__).resolve()), "--child"], check=True, timeout=45)
    else:
        parser.error("--runtime is required")


if __name__ == "__main__":
    main()
