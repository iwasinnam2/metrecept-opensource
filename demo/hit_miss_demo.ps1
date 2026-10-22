<#
.SYNOPSIS
  Proves the core claim live: an identical request MISSes once, then HITs for
  free -- and every call, HIT or MISS, carries a signed receipt you can verify yourself.

.EXAMPLE
  $env:OHM_API_KEY = "sk-at-..."
  powershell -NoProfile -ExecutionPolicy Bypass -File demo\hit_miss_demo.ps1

  Get a free key (no card) at https://metrecept.co.uk/billing/intermediate
#>
param(
    [string]$BaseUrl = $(if ($env:OHM_BASE_URL) { $env:OHM_BASE_URL } else { "https://api.metrecept.co.uk" })
)

$ErrorActionPreference = "Stop"

if (-not $env:OHM_API_KEY) {
    Write-Error "Set `$env:OHM_API_KEY first -- get a free `$0 key at https://metrecept.co.uk/billing/intermediate"
    exit 1
}

$body = @{
    model    = "mock"
    messages = @(@{ role = "user"; content = "withohm-open demo $(Get-Date -UFormat %s)" })
} | ConvertTo-Json -Compress

$headers = @{
    Authorization  = "Bearer $env:OHM_API_KEY"
    "Content-Type" = "application/json"
}

Write-Output "== Request 1 (expect MISS) =="
$resp1 = Invoke-WebRequest -Uri "$BaseUrl/v1/chat/completions" -Method Post -Headers $headers -Body $body
Write-Output "X-AT-Cache: $($resp1.Headers['X-AT-Cache'])"

Write-Output ""
Write-Output "== Request 2, identical body (expect HIT) =="
$resp2 = Invoke-WebRequest -Uri "$BaseUrl/v1/chat/completions" -Method Post -Headers $headers -Body $body
Write-Output "X-AT-Cache: $($resp2.Headers['X-AT-Cache'])"
if ($resp2.Headers['X-AT-Billed-USD']) {
    Write-Output "X-AT-Billed-USD: $($resp2.Headers['X-AT-Billed-USD'])"
}

$receipt = $resp2.Headers['X-Ohm-Receipt']
if ($receipt) {
    Write-Output ""
    Write-Output "== Verifying the signed receipt (zero withOhm code) =="
    python "$PSScriptRoot\verify_receipt.py" "$receipt" --base $BaseUrl
} else {
    Write-Output "(no X-Ohm-Receipt header on this response -- receipts may be disabled for this tenant)"
}
