# CCW project interchange boundary

TwinForge consumes Connected Components Workbench evidence through a versioned
JSON contract. It does not decode `.ccwarc` archives and does not import Python
code from the separate `rockwell-file-research` repository.

## Contract provenance

The packaged `ccw-project-v1.schema.json` is an exact snapshot of the Draft
2020-12 schema generated and maintained by `rockwell-file-research` for its
`ccw-project-v1` export. Its stable identifier is
`urn:rockwell-file-research:ccw-project:v1`.

The initial vendored snapshot has SHA-256
`a339b755aea53f119de6bd621979dfee91d7b6355dddd3aa0f4472319454c37a`.
This hash is the same in both repositories at the time of integration.

Update the snapshot only when the producing repository intentionally publishes
a compatible or newly versioned contract. TwinForge must add explicit support
for a new `schema_version`; it must not silently interpret one version as
another.

## Responsibility boundary

```text
.ccwarc archive
    -> rockwell-file-research capture and parsing
    -> ccw-project-v1.json
    -> TwinForge validation and lossless interchange capture
    -> future vendor-neutral semantic lowering
```

The first TwinForge milestone validates and inventories the artifact only. The
adapter retains the complete validated document, including source provenance,
SHA-256 evidence, parser diagnostics, unresolved operands, sensitive-entry
names, and unknown-entry names. It does not yet claim that CCW ladder logic can
be converted to PLCopen XML or CODESYS.

The schema deliberately rejects undeclared JSON members. Evidence that the
producer cannot interpret remains represented through its documented
diagnostic and unknown-entry fields rather than being discarded or guessed by
TwinForge.

## Command line

Validate or inspect an artifact without lowering it:

```powershell
uv run twinforge ccw-project validate .\project.json
uv run twinforge ccw-project inspect .\project.json
uv run twinforge ccw-project inspect .\project.json --format json
```

Export the exact schema snapshot used by the installed TwinForge version:

```powershell
uv run twinforge ccw-project schema --output .\ccw-project-v1.schema.json
```
