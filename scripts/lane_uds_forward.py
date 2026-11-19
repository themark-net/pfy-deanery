#!/usr/bin/env python3
"""In-cage forwarder: 127.0.0.1:PORT -> the driver's egress proxy unix socket.

The lane container runs with --network=none, so loopback is its only
interface. HTTPS_PROXY points at this forwarder; the driver-side proxy
(scripts/lane_cage.py) decides which hosts are reachable. Unsetting the proxy
does not help an agent: there is no other route out.
"""
from __future__ import annotations

import socket
import sys
import threading


def pipe(a: socket.socket, b: socket.socket) -> None:
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


def serve(port: int, sock_path: str) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(64)
    while True:
        conn, _ = srv.accept()
        up = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            up.connect(sock_path)
        except OSError:
            conn.close()
            continue
        threading.Thread(target=pipe, args=(conn, up), daemon=True).start()
        threading.Thread(target=pipe, args=(up, conn), daemon=True).start()


if __name__ == "__main__":
    serve(int(sys.argv[1]), sys.argv[2])
