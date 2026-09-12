"""Raw stdio probe: is every byte the server writes to stdout valid JSON-RPC?

Usage:
    python scripts/stdio_probe.py uv run mcp-vultr
    python scripts/stdio_probe.py /path/to/venv/bin/mcp-vultr

Speaks initialize / initialized / tools/list / resources/list over stdin
without any MCP client library in between, then reports tool and resource
counts, whether a few landmark tool names are present, and every stdout
line that failed to parse as JSON. Under the stdio transport stdout is the
JSON-RPC channel, so one stray print() is a broken server for strict
clients. Exit code 0 only if stdout was clean and the landmarks were there.
Needs no Vultr key: tools/list and resources/list never call the API.
"""

import json
import os
import subprocess
import sys
import threading
import time

LANDMARKS = ["dns_list_domains", "instance_create", "firewall_list_groups", "reserved_ip_list_unattached"]


def main(cmd: list[str]) -> int:
    env = dict(os.environ, VULTR_API_KEY="probe-key-not-real", PYTHONUNBUFFERED="1")
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    stdout_lines: list[bytes] = []
    stderr_chunks: list[bytes] = []

    def pump(stream, sink):
        for line in iter(stream.readline, b""):
            sink.append(line)

    threading.Thread(target=pump, args=(proc.stdout, stdout_lines), daemon=True).start()
    threading.Thread(target=pump, args=(proc.stderr, stderr_chunks), daemon=True).start()

    def send(obj):
        proc.stdin.write((json.dumps(obj) + "\n").encode())
        proc.stdin.flush()

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "stdio-probe", "version": "0"}}})

    def wait_for(rid, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for raw in stdout_lines:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if isinstance(msg, dict) and msg.get("id") == rid:
                    return msg
            if proc.poll() is not None:
                break
            time.sleep(0.05)
        return None

    init = wait_for(1)
    if init is None:
        print("FAIL: no initialize response", file=sys.stderr)
        print(b"".join(stderr_chunks).decode(errors="replace")[-3000:], file=sys.stderr)
        proc.kill()
        return 2
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = wait_for(2)
    send({"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})
    resources = wait_for(3)
    time.sleep(0.5)
    proc.stdin.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    bad = []
    for raw in stdout_lines:
        try:
            json.loads(raw)
        except Exception:
            bad.append(raw.decode(errors="replace").rstrip())

    server_info = init.get("result", {}).get("serverInfo", {})
    tool_names = [t["name"] for t in (tools or {}).get("result", {}).get("tools", [])]
    res_count = len((resources or {}).get("result", {}).get("resources", []))
    missing = [n for n in LANDMARKS if n not in tool_names]

    print(f"server: {server_info.get('name')} {server_info.get('version', '')}")
    print(f"protocol: {init.get('result', {}).get('protocolVersion')}")
    print(f"tools: {len(tool_names)}  resources: {res_count}")
    print(f"landmarks missing: {missing or 'none'}")
    print(f"non-JSON stdout lines: {len(bad)}")
    for line in bad[:10]:
        print(f"  >> {line[:160]}")
    err = b"".join(stderr_chunks).decode(errors="replace")
    print(f"stderr ({len(err.splitlines())} lines), first 6:")
    for line in err.splitlines()[:6]:
        print(f"  | {line[:160]}")
    return 0 if not bad and not missing and tool_names else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
