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
        expected = sorted([
            "metrecept_create_chat_completion", "metrecept_fetch_web_pages",
            "metrecept_call_api", "metrecept_register_api_service",
            "metrecept_list_api_services", "metrecept_unregister_api_service",
            "metrecept_get_session_receipt", "metrecept_get_usage",
            "metrecept_get_usage_history", "metrecept_get_savings",
            "metrecept_publish_savings_receipt", "metrecept_list_models",
            "metrecept_list_providers", "metrecept_get_fetch_policy",
            "metrecept_list_cache_trees", "metrecept_list_cache_entries",
            "metrecept_evict_cache_entry", "metrecept_delete_cache_tree",
            "metrecept_manage_cache_tree",
        ])
        assert len(names) == 19, names
        assert names == expected, names
        assert all(n.startswith("metrecept_") for n in names), names
        return 0
    finally:
        proc.stdin.close()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()

if __name__ == "__main__":
    sys.exit(main())
