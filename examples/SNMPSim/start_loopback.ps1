$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$dataDirectory = (Resolve-Path (Join-Path $PSScriptRoot "data")).Path
$cacheDirectory = Join-Path $env:TEMP "TwinForge-SNMPSim-Cache"
$authenticationKey = if ($env:TWINFORGE_SNMP_AUTH_KEY) {
    $env:TWINFORGE_SNMP_AUTH_KEY
}
else {
    "TwinForgeAuth2026"
}
$privacyKey = if ($env:TWINFORGE_SNMP_PRIVACY_KEY) {
    $env:TWINFORGE_SNMP_PRIVACY_KEY
}
else {
    "TwinForgePrivacy2026"
}

New-Item -ItemType Directory -Force -Path $cacheDirectory | Out-Null

Push-Location $repositoryRoot
try {
    uv run --group snmp-sim snmpsim-command-responder `
        "--data-dir=$dataDirectory" `
        "--cache-dir=$cacheDirectory" `
        "--agent-udpv4-endpoint=127.0.0.1:1161" `
        "--v3-user=twinforge-local" `
        "--v3-auth-key=$authenticationKey" `
        "--v3-auth-proto=SHA256" `
        "--v3-priv-key=$privacyKey" `
        "--v3-priv-proto=AES"
}
finally {
    Pop-Location
}
