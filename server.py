#!/usr/bin/env python3
"""
Hermes Site-Audit MCP Server — Alexa+ track, Amazon Developer Hackathon.

A self-hosted MCP server (MCP spec 2026-07-28, Streamable HTTP) that gives
an AI assistant honest, measurement-only website auditing superpowers:
audit a small-business site for fixable technical issues, find its public
contact emails, and draft outreach that quotes only measured findings.

Run:
    pip install -r requirements.txt
    python server.py                # Streamable HTTP on 127.0.0.1:8000/mcp
    python server.py --port 9000    # custom port

Connect any MCP client (Claude Desktop, MCP Inspector, Alexa+ via MCP)
to http://127.0.0.1:8000/mcp using the Streamable HTTP transport.
"""
from __future__ import annotations

import argparse
import json

from mcp.server.mcpserver import MCPServer

from siteaudit_core import (
    audit_domain,
    normalize_domain,
)
from siteaudit_core import draft_outreach as core_draft_outreach
from siteaudit_core import find_contact_emails as core_find_contact_emails

SERVER_NAME = "hermes-site-audit"
SERVER_INSTRUCTIONS = (
    "Website auditing tools. Every finding is measured live — quote the "
    "'findings' block verbatim and never invent problems a tool did not "
    "report. Never guess a contact email; if 'to' is null, say so."
)

mcp = MCPServer(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)


@mcp.tool()
def audit_website(domain: str) -> str:
    """Audit a website for fixable technical issues.

    Measures live: HTTP status, response latency, page title, meta
    description, mobile viewport tag, TLS certificate expiry, and server
    errors. Returns a JSON audit with issues, human-readable labels,
    a severity score, and the raw measurements.
    """
    try:
        audit = audit_domain(domain)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(audit.to_dict(), indent=2)


@mcp.tool()
def find_contact_emails(domain: str) -> str:
    """Find public contact emails published on a website.

    Checks the homepage then likely contact/about pages, preferring
    mailto: links. Returns a JSON object with the emails found (max 5)
    and where they were found. Empty list means none published.
    """
    try:
        result = core_find_contact_emails(domain)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(result, indent=2)


@mcp.tool()
def check_ssl(domain: str) -> str:
    """Check a domain's TLS certificate: days until expiry.

    Returns JSON with domain, days_left, and whether it expires within
    14 days. Useful as a standalone check before drafting outreach.
    """
    import socket
    import ssl as _ssl
    import datetime

    host = normalize_domain(domain)
    try:
        ctx = _ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
        exp = datetime.datetime.strptime(
            cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days = (exp - datetime.datetime.utcnow()).days
        return json.dumps({
            "domain": host,
            "days_left": days,
            "expires_soon": days < 14,
            "not_after": cert["notAfter"],
        }, indent=2)
    except Exception as e:
        return json.dumps({"domain": host, "error": str(e)[:120]})


@mcp.tool()
def draft_outreach(domain: str) -> str:
    """Draft a short outreach email based ONLY on measured audit findings.

    Runs a full audit, finds public contact emails, and drafts a pitch
    that quotes the measured issues verbatim. Returns the draft plus the
    raw findings so every claim can be verified before sending. If no
    public email exists, 'to' is null — never guess an address.
    """
    try:
        draft = core_draft_outreach(domain)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(draft, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes Site-Audit MCP Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    args = parser.parse_args()
    print(f"Starting {SERVER_NAME} — Streamable HTTP on "
          f"http://{args.host}:{args.port}{args.path}")
    mcp.run(transport="streamable-http", host=args.host,
            port=args.port, streamable_http_path=args.path)


if __name__ == "__main__":
    main()
