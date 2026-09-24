"""Live end-to-end test: boots the real server over Streamable HTTP and
exercises every tool through a real MCP client session."""
import asyncio
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8931
URL = f"http://127.0.0.1:{PORT}/mcp"


def wait_for_server(proc, timeout=25):
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("server exited early")
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                time.sleep(1.5)  # let uvicorn finish startup
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("server did not start in time")


async def exercise():
    import os
    # localhost needs no proxy; the sandbox proxy vars break httpx URL parsing
    for var in list(os.environ):
        if var.lower().endswith("_proxy"):
            del os.environ[var]
    from mcp.client.streamable_http import streamable_http_client
    from mcp.client.session import ClientSession

    async with streamable_http_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("tools:", names)
            assert names == ["audit_website", "check_ssl",
                             "draft_outreach", "find_contact_emails"], names

            # audit_website against a stable real domain
            res = await session.call_tool("audit_website",
                                          {"domain": "example.com"})
            audit = json.loads(res.content[0].text)
            print("audit example.com issues:", audit["issues"],
                  "status:", audit["notes"].get("status"))
            assert audit["domain"] == "example.com"
            assert audit["notes"].get("status") == 200

            # invalid input is handled, not a crash
            res = await session.call_tool("audit_website",
                                          {"domain": "not a domain"})
            assert "error" in json.loads(res.content[0].text)

            # check_ssl (raw TLS sockets may be blocked in sandboxes;
            # the tool must then report an error, never crash)
            res = await session.call_tool("check_ssl",
                                          {"domain": "example.com"})
            ssl_info = json.loads(res.content[0].text)
            print("ssl result:", ssl_info)
            assert ("days_left" in ssl_info and ssl_info["days_left"] > 0) \
                or "error" in ssl_info

            # find_contact_emails (example.com publishes none)
            res = await session.call_tool("find_contact_emails",
                                          {"domain": "example.com"})
            emails = json.loads(res.content[0].text)
            print("emails:", emails["emails"])
            assert isinstance(emails["emails"], list)

            # draft_outreach returns draft + verifiable findings
            res = await session.call_tool("draft_outreach",
                                          {"domain": "example.com"})
            draft = json.loads(res.content[0].text)
            print("draft subject:", draft["subject"])
            assert "findings" in draft and "body" in draft
    print("ALL MCP TOOL TESTS PASSED")


def main():
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "server.py"), "--port", str(PORT)],
        cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        wait_for_server(proc)
        asyncio.run(exercise())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
