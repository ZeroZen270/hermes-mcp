# Hermes Site-Audit MCP Server

A self-hosted **MCP server** (Model Context Protocol, spec 2025-11-25+, Streamable HTTP)
that gives an AI assistant honest, measurement-only website auditing superpowers —
built for the **Alexa+ track** of the Amazon Developer Hackathon
(*Build, Ship, Shape*, 2026).

MCP is the open standard that powers Alexa+ integrations. This server exposes
four tools any MCP client (Claude Desktop, MCP Inspector, Alexa+ via MCP) can call:

| Tool | What it does |
|---|---|
| `audit_website` | Audits a domain for fixable technical issues — measured live: HTTP status, latency, `<title>`, meta description, mobile viewport, TLS expiry, 5xx errors. Returns issues + human-readable labels + severity score + raw measurements. |
| `find_contact_emails` | Finds public contact emails published on the site (homepage, then contact/about pages; `mailto:` links first, max 5). |
| `check_ssl` | TLS certificate days-until-expiry for a domain. |
| `draft_outreach` | Drafts a short outreach email quoting **only** measured findings, with the raw audit attached so every claim is verifiable. `to` is `null` when no public email exists — it never guesses an address. |

## Why this exists

Freelancers and small agencies waste hours manually checking prospect websites.
An assistant connected to this server can answer "audit example.com and draft
me an honest outreach note" in one turn — with every claim backed by a live
measurement, never invented.

## Quickstart

```bash
pip install -r requirements.txt
python server.py                      # Streamable HTTP on http://127.0.0.1:8000/mcp
python server.py --port 9000          # custom port
```

Connect your MCP client to `http://127.0.0.1:8000/mcp` using the
**Streamable HTTP** transport, then ask it to audit a website.

Example (via MCP Inspector or any client):

```
> Use audit_website on example.com
< {"domain": "example.com", "issues": ["no_meta_description"],
    "issue_labels": ["homepage has no meta description (hurts click-through)"],
    "score": 2, "notes": {"status": 200, "latency_s": 0.33, ...}}
```

## Tests

```bash
pip install -r requirements.txt
python test_mcp_live.py
```

Spins up the real server on a local port and exercises all four tools through
a real MCP client session (needs internet access for the live audit targets).

## Project layout

- `server.py` — MCP server (4 tools, Streamable HTTP)
- `siteaudit_core.py` — measurement-only audit engine (no MCP dependency)
- `test_mcp_live.py` — end-to-end test over real Streamable HTTP

## Built with

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp>=2.2`, Streamable HTTP transport, spec 2025-11-25+)
- `requests` for the audit probes

## License

MIT — see [LICENSE](LICENSE).
