# Controlled SNMP Recording Conversion

TwinForge accepts common `.snmpwalk` text directly. Files with unusual
extensions or packaging are not guessed from their contents. An operator can
instead declare that a specific checksummed file contains Net-SNMP walk text
and convert it through a reviewable offline workflow.

The installed command is dry-run by default:

```powershell
twinforge snmp convert-walk vendor.dump `
  --output converted.snmprec `
  --expected-sha256 <64-hex-checksum> `
  --source-url https://example.invalid/source `
  --license BSD-2-Clause `
  --device-category switch `
  --sanitized `
  --approved-by lab.operator `
  --approved-at 2026-08-10T09:00:00+10:00 `
  --rationale "Declared vendor dump as Net-SNMP walk text"
```

The dry run prints the plan and performs no conversion. After review, repeat
the same command with `--execute`.

## Controls

The plan requires:

- an exact input SHA-256 checksum;
- source URL, licence, device category, and sanitization status;
- approving operator, timezone-aware approval time, and rationale;
- a positive input byte limit; and
- a distinct `.snmprec` destination.

Network access is always disabled. Existing output, sidecar, or receipt files
are never overwritten. Use `--reject-unparsed-lines` when conversion must fail
unless every non-empty input line is canonicalized.

## Outputs and evidence retention

Successful execution writes:

- a canonical, numerically ordered `.snmprec` recording;
- `.snmprec.unparsed.json`, containing every undecoded source line with its
  original line number, text, and reason; and
- `.snmprec.receipt.json`, linking input and output checksums to provenance and
  approval metadata.

The original input remains untouched. Outputs are prepared in temporary files
and moved into place only after decoding and policy validation. The receipt is
written last and therefore acts as the completion marker for downstream corpus
assembly. The resulting `.snmprec` can be added to an ordinary corpus manifest
and measured through the existing offline lowering workflow.
