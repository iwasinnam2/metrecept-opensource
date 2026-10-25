"""Smoke test: start metrecept-mcp over stdio, initialize, and list tools."""
import json, queue, subprocess, sys, threading, time

TIMEOUT = 30

def main() -> int:
    proc = subprocess.Popen(["metrecept-mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=sys.stderr, text=True, bufsize=1)
    q: "queue.Queue[str]" = queue.Queue()
    threading.Thread(target=lambda: [q.put(l) for l in proc.stdout], daemon=True).start()

    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n"); proc.stdin.flush()

    def wait_for(id_):
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            try:
                line = q.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == id_:
                return msg
        raise TimeoutError(f"no response for id {id_}")

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "ci-smoke", "version": "0"}}})
        r = wait_for(1); assert "result" in r, r
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        r = wait_for(2)
        tools = r.get("result", {}).get("tools", [])
        print(f"tools/list returned {len(tools)} tools")
        names = sorted(t["name"] for t in tools)
        assert len(names) == 14, names
        assert all(n.startswith("metrecept_") for n in names), names
        return 0
    finally:
        proc.stdin.close()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

if __name__ == "__main__":
    sys.exit(main())
