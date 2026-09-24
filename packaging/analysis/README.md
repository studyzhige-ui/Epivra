# Restricted Windows analysis runtime

Based on CPython 3.12.13. Upstream source:
https://github.com/python/cpython/tree/v3.12.13

Epivra changes only Winsock extension lookup in Modules/overlapped.c.
Importing the module no longer creates a probe socket. AcceptEx, ConnectEx,
DisconnectEx and TransmitFile query their actual socket provider into a local
typed function pointer before changing operation state. OS access checks remain
in force; there is no global cache or permission fallback. The upstream license
is retained in PYTHON-LICENSE.txt.

This correction supports scientific library imports under Windows LPAC. It does
not promise arbitrary asyncio event loops in a process prohibited from creating
sockets. Runtime verification must include the complete scientific workload and
negative OS-boundary tests. Never use this extension with a different Python ABI.
