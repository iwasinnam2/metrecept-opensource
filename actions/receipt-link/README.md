# Metrecept receipt link — GitHub Action

Status: **Founder opens. Agent does not send.** (Marketplace listing is a
founder step; packet in `docs/distribution/RECEIPT-LINK-PACKETS.md`.)

Comments the signed session receipt link on a pull request:

```
### Metrecept session receipt
Receipt: https://metrecept.co.uk/verify#<jws>
12 events · $0.0123 pipe · 3 cache hits · 9 misses · session `pr-842`
This link proves the Metrecept key signed this record of the run; anyone can
check it in their browser against the public key directory, no account. It
does not grade the work, and it did not stop anything.
```

## Use

```yaml
- uses: iwasinnam2/withohm-open/actions/receipt-link@main
  with:
    session-id: pr-${{ github.event.pull_request.number }}
    api-key: ${{ secrets.METRECEPT_API_KEY }}
```

Tag the agent's calls with the same id (`X-Metrecept-Session: pr-842`, or
`session_id` on the MCP tools). The action reads `GET /v1/sessions/{id}`;
reading does not bill. A session with no tagged events gets a comment that
says so, and no link.

## What it needs

`python3` and `gh` (both on GitHub-hosted runners), `pull-requests: write`
permission for the job, and a Metrecept API key in a secret.
