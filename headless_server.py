#!/usr/bin/env python3
"""Run the Binary Ninja MCP HTTP server headless (no GUI).

The MCP *bridge* (`uvx binja-mcp`) is just an HTTP client to localhost:9009.
Normally the *plugin* that serves 9009 runs inside the Binary Ninja GUI and
requires an active BinaryView. This launcher starts that same MCPServer using
the headless Binary Ninja API instead, so the bridge (and all mcp__binja-mcp__*
tools) work with no GUI open.

Usage:
    python headless_server.py [binary ...] [--host H] [--port P] [--no-update-analysis]

Each positional binary is opened, analyzed, and registered so list_binaries /
select_binary see it immediately. With no binaries given, the server still
starts; load one later via the add_binary_to_project / load_binary MCP path.
"""
import argparse
import os
import signal
import sys
import time

# Make the vendored `plugin` package importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import binaryninja as bn  # noqa: E402  (BN API installed via install_api.py)

from plugin.core.config import Config  # noqa: E402
from plugin.server.http_server import MCPServer  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless Binary Ninja MCP server")
    ap.add_argument("binaries", nargs="*", help="binaries to preload and analyze")
    ap.add_argument("--host", default=None, help="bind host (default localhost)")
    ap.add_argument("--port", type=int, default=None, help="bind port (default 9009)")
    ap.add_argument(
        "--no-update-analysis",
        action="store_true",
        help="skip waiting for full analysis on preloaded binaries",
    )
    args = ap.parse_args()

    cfg = Config()
    if args.host:
        cfg.server.host = args.host
    if args.port:
        cfg.server.port = args.port

    server = MCPServer(cfg)

    for path in args.binaries:
        if not os.path.exists(path):
            print(f"[!] skip (not found): {path}", file=sys.stderr)
            continue
        print(f"[*] loading {path} ...", flush=True)
        bv = server.binary_ops.load_binary(path)
        if bv is None:
            print(f"[!] failed to open: {path}", file=sys.stderr)
            continue
        if not args.no_update_analysis:
            bv.update_analysis_and_wait()
        print(f"    {path}: {len(list(bv.functions))} functions", flush=True)

    server.start()
    print(
        f"[+] Binary Ninja MCP server (headless) on "
        f"http://{cfg.server.host}:{cfg.server.port}  (BN {bn.core_version()})",
        flush=True,
    )

    stop = {"v": False}

    def _handle(_sig, _frm):
        stop["v"] = True

    signal.signal(signal.SIGINT, _handle)
    try:
        signal.signal(signal.SIGTERM, _handle)
    except (ValueError, AttributeError):
        pass

    try:
        while not stop["v"]:
            time.sleep(0.5)
    finally:
        print("[*] stopping server ...", flush=True)
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
