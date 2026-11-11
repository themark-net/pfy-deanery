#!/usr/bin/env python3
"""Forward one unix socket to one fixed TCP endpoint (default 127.0.0.1:11434, Ollama).

The trial runs in its own network namespace with no route out; this socket is
its only way to the local model. Usage: sock_proxy.py SOCKET_PATH [HOST:PORT]
"""
import os
import socket
import sys
import threading

path = sys.argv[1]
host, port = (sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1:11434").rsplit(":", 1)
if os.path.exists(path):
    os.unlink(path)
srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
srv.bind(path)
srv.listen(8)


def pipe(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


while True:
    client, _ = srv.accept()
    upstream = socket.create_connection((host, int(port)))
    threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
    threading.Thread(target=pipe, args=(upstream, client), daemon=True).start()
