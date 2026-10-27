# metrecept-mcp 0.7.0
Breaking changes:
- The legacy ohm-mcp / ohm-mcp-http commands and the ohm_mcp import alias are gone. Use metrecept-mcp / metrecept_mcp.
- The legacy-prefixed environment variables are no longer read. Use METRECEPT_API_KEY, METRECEPT_BASE_URL, METRECEPT_UPSTREAM_KEY, METRECEPT_SERVICE_KEY, METRECEPT_MCP_*.
- The legacy API/MCP hostnames were removed from the host allowlist. Use api.metrecept.co.uk / mcp.metrecept.co.uk.
Other: serverInfo.version is now populated.

Sunset notice:
- Date: 2027-01-25.
- The 0.6.x line still ships the ohm_mcp import shim and ohm-mcp commands, and the hosted API still sends the X-Ohm-Receipt header alias. Both are scheduled to stop on that date; 0.6.x gets no fixes after it. Move to 0.7.0 (metrecept_mcp) and the X-Metrecept-* headers before then.
