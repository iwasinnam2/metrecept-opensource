---
name: ohm-providers
description: >
  withOhm upstream provider and failover status via MCP ohm_providers. Use when
  a model call fails, routing looks off, or you want pipe health — withOhm,
  ohm, providers, failover, status.
---

# Ohm providers

Call the Ohm MCP tool `ohm_providers` for upstream provider and failover status.

## Call

```text
ohm_providers()
```

Returns provider health and failover state from `GET /v1/providers`. Check
this first when `ohm_chat` errors on a real (non-mock) model.

Requires Ohm MCP attached (`OHM_BASE_URL`, `OHM_API_KEY`). See `docs/CURSOR.md`.
