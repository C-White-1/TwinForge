# Offline installation and operation

TwinForge's parsing, reporting, validation, and export paths are deterministic
local operations. They do not require an AI service, cloud API, controller
connection, or network discovery. Unsupported source semantics are reported;
they are not silently discarded or guessed.

## Requirements

- Python 3.10 or newer
- `uv` for the documented installation workflow
- A local Rockwell L5X export
- Optional local standards files for schema validation

The official PLCopen XML schemas and AutomationML libraries are third-party
reference assets. TwinForge does not redistribute them. The repository's
`reference/` directory is ignored by Git so each user can maintain legally
obtained copies locally.

## Install from a repository checkout

Clone or copy TwinForge, open PowerShell in the repository root, and create the
managed environment:

```powershell
uv sync --extra validation
uv run twinforge --help
```

The `validation` extra installs `lxml` for PLCopen and CAEX XSD validation.
Install the optional SNMP dependencies only when that offline evidence workflow
is needed:

```powershell
uv sync --extra validation --extra snmp
```

Use `uv run twinforge` in commands below. Alternatively, activate `.venv` and
invoke `twinforge` directly:

```powershell
.\.venv\Scripts\Activate.ps1
twinforge --help
```

## Install XML validation

An XSD is a data file that describes valid XML structure. It is not installed
or run as an executable. TwinForge uses `lxml` as the validation engine and
loads the XSD supplied through `--xsd`.

Install the validation engine through the project extra:

```powershell
uv sync --extra validation
```

Confirm that the active TwinForge environment can import it:

```powershell
uv run python -c "from lxml import etree; print(etree.LXML_VERSION)"
```

Create this recommended local layout:

```text
reference/
├── AutomationML/
│   ├── AutomationML2.10BaseLibraries.aml
│   └── CAEX_ClassModel_V.3.0.xsd
└── PLCopenXML/
    └── standard/
        └── tc6_xml_v201.xsd
```

The entire `reference/` directory is ignored by Git. These files therefore
remain on the workstation and are not included accidentally in a commit.

### Obtain the PLCopen schema

1. Open the official [PLCopen downloads page](https://www.plcopen.org/downloads/).
2. Find **PLCopen XML version 2.01 xsd file**, which is the ZIP archive rather
   than the PDF describing the schema.
3. Review the accompanying terms and download the archive.
4. Extract `tc6_xml_v201.xsd` into
   `reference/PLCopenXML/standard/`.

TwinForge currently emits the PLCopen 2.01 namespace. Do not substitute an XSD
for another PLCopen or IEC 61131-10 format merely because its filename is
newer; those formats are not necessarily compatible.

Confirm that the schema is available:

```powershell
Test-Path reference\PLCopenXML\standard\tc6_xml_v201.xsd
```

Validate a planned target-neutral PLCopen export without writing it:

```powershell
uv run twinforge export project.L5X `
  --target plcopen `
  --output build\project.xml `
  --xsd reference\PLCopenXML\standard\tc6_xml_v201.xsd `
  --dry-run
```

Remove `--dry-run` to validate and then write the XML. The standard PLCopen
2.01 XSD does not apply to the CODESYS-adapted target.

### Obtain the CAEX schema and AutomationML base library

1. Open the official AutomationML
   [CAEX and AutomationML guide](https://www.automationml.org/about-automationml/publications/amlbook/a-practical-guide/chapter-2-the-caex-and-automationml-guide/).
2. Download and extract **CAEX_ClassModel_V.3.0.xsd**.
3. Obtain the AutomationML 2.1 base libraries from the official
   [AutomationML specifications](https://www.automationml.org/about-automationml/specifications/)
   and retain the file as `AutomationML2.10BaseLibraries.aml`.
4. Place both files in `reference/AutomationML/`.

The files serve different purposes:

- `CAEX_ClassModel_V.3.0.xsd` validates XML structure and ordering.
- `AutomationML2.10BaseLibraries.aml` supplies the standard semantic classes
  referenced by the generated document.

The base library is required for AutomationML export even when XSD validation
is not requested. Validate structure, external references, and semantic paths
without writing the AML file:

```powershell
uv run twinforge export project.L5X `
  --target automationml `
  --output build\plant.aml `
  --base-library reference\AutomationML\AutomationML2.10BaseLibraries.aml `
  --xsd reference\AutomationML\CAEX_ClassModel_V.3.0.xsd `
  --dry-run
```

TwinForge checks each supplied source, schema, base-library, and referenced
document path before conversion. A missing path produces a concise error that
names the corresponding option, returns exit code `2`, and writes no output.
If `lxml` is absent or validation fails, TwinForge also returns a non-zero exit
code without writing the requested output.

## Prepare a disconnected workstation

Dependency resolution and downloading require connectivity on the first
machine. To prepare for a disconnected installation:

1. Copy the complete TwinForge checkout, including `uv.lock`.
2. Populate the uv cache on a connected machine with the required extras.
3. Transfer both the checkout and that cache through the approved site process.
4. On the disconnected machine, point uv at the transferred cache and use
   `--offline`.

For example:

```powershell
$env:UV_CACHE_DIR = 'D:\TwinForge-dependencies\uv-cache'
uv sync --offline --extra validation
```

An environment directory should not be copied between unlike operating systems
or Python platforms. Transfer the dependency cache and let uv construct the
environment for the destination machine.

## Inspect before converting

Inspection is read-only and accepts controller, module, program, and Add-On
Instruction L5X exports:

```powershell
uv run twinforge inspect project.L5X
uv run twinforge inspect project.L5X --format json
```

Generate the supported controller engineering report bundle with:

```powershell
uv run twinforge report project.L5X --output reports\project
```

Apply a separately reviewed alarm/trip overlay when engineering authority is
available:

```powershell
uv run twinforge report project.L5X `
  --output reports\project-reviewed `
  --alarm-review alarm-review.json
```

Start from `examples/reporting/alarm-review.example.json`, then replace its
controller name, exact candidate keys, review assertions, and provenance with
the approved project information. TwinForge rejects unknown candidates and
does not alter the source L5X.

After first generating the cause-and-effect matrix and obtaining its exact
relationship keys, a separately attributable relationship review may be
applied as well:

```powershell
uv run twinforge report project.L5X `
  --output reports\project-reviewed `
  --alarm-review alarm-review.json `
  --cause-effect-review cause-effect-review.json
```

Use `examples/reporting/cause-effect-review.example.json` as the starting
contract. Unknown keys fail closed, and unresolved operands cannot be marked
as verified.

Validate a completed review overlay independently before report generation:

```powershell
uv run twinforge review validate alarm alarm-review.json
uv run twinforge review validate cause-effect cause-effect-review.json
```

This checks the selected versioned input contract, attribution fields,
timestamps, unique keys, and asserted values. Candidate-key reconciliation
occurs when the overlay is applied to its source L5X report. It can also be
requested independently, without creating a report bundle:

```powershell
uv run twinforge review validate alarm alarm-review.json `
  --source project.L5X
```

With `--source`, TwinForge rebuilds the evidence-derived candidates and rejects
controller-name mismatches, unknown alarm keys, unknown relationship keys, and
attempts to verify unresolved cause-and-effect relationships.

For CI or MCP consumption, request a versioned JSON validation receipt:

```powershell
uv run twinforge review validate alarm alarm-review.json `
  --source project.L5X `
  --format json `
  --output evidence\alarm-review-validation.json
```

The receipt includes SHA-256 hashes of the exact review and L5X bytes. Export
its installed JSON Schema with:

```powershell
uv run twinforge review schema validation-result `
  --output schemas\review-validation-result.v1.schema.json
```

Invalid input returns exit code `4` (`VALIDATION_FAILED`). With `--format
json`, stderr contains TwinForge's versioned diagnostic envelope with operation
`review.validate`; stdout remains empty. This lets CI and MCP callers handle
success and failure without scraping prose.

`--output` writes the same JSON receipt using atomic file replacement. A failed
review never creates or partially overwrites the requested receipt.

Verify a retained receipt later against the exact input bytes, repeating L5X
candidate reconciliation when a source was originally supplied:

```powershell
uv run twinforge review verify-receipt alarm `
  evidence\alarm-review-validation.json `
  --review alarm-review.json `
  --source project.L5X
```

Any changed review or source bytes, altered metadata, missing field, additional
field, controller mismatch, or now-invalid candidate key fails verification.

When `twinforge report` applies an alarm or cause-and-effect review, the report
bundle automatically contains `alarm_review_validation.json` or
`cause_effect_review_validation.json`. These use input basenames for portable,
reproducible content, and `report_manifest.json` authenticates each receipt as
part of the complete generated file set.

Bundle verification also checks receipt semantics. Each receipt must name and
hash the exact manifested review overlay and L5X input, identify the expected
review kind, and record successful source reconciliation. A correctly rehashed
but contradictory receipt is therefore rejected.

Each generated bundle includes `report_manifest.json`. It records SHA-256
digests and byte sizes for the source L5X, any applied review overlays, and
every other generated report. The manifest intentionally omits timestamps and
does not hash itself, avoiding circular content while keeping identical inputs
reproducible.

Verify the complete bundle against the original evidence files:

```powershell
uv run twinforge reports verify reports\project-reviewed `
  --source project.L5X `
  --alarm-review alarm-review.json `
  --cause-effect-review cause-effect-review.json
```

Omit a review option only when that review kind is absent from the manifest.
Verification fails for missing, unexpected, added, removed, renamed, or changed
files.

Export the exact manifest schema installed with TwinForge for independent CI or
MCP validation:

```powershell
uv run twinforge reports schema `
  --output schemas\engineering-report-manifest.v1.schema.json
```

Export the exact schemas installed with the active TwinForge version when
configuring an editor, CI job, or MCP client:

```powershell
uv run twinforge review schema alarm `
  --output schemas\alarm-review.v1.schema.json
uv run twinforge review schema cause-effect `
  --output schemas\cause-effect-review.v1.schema.json
```

The bundle includes review-oriented Markdown, complete CSV, and deterministic
JSON reports for tag dependencies and explicitly labelled alarm/trip candidates.
It also includes a channel-level I/O list covering explicit assignments, spare
candidates, configuration-unavailable channels, ranges, and units. Unresolved
operands remain visible. A cause-and-effect candidate matrix joins reads to
alarm/trip writes at the same source location but does not claim verified
causality. Unestablished facts should be reviewed rather than inferred.
The `functional_description.md` draft summarizes controller identity,
task/program execution, routine coverage, and the generated engineering
evidence while retaining explicit verification boundaries.
The module schedule provides Markdown, CSV, and JSON summaries of capacity,
assignments, spare candidates, configuration-unavailable channels, and modules
whose I/O capability remains unknown.

## Check export readiness

Use `--dry-run` before writing an output. It performs parsing, target planning,
configuration validation, and any requested schema or semantic validation:

```powershell
uv run twinforge export project.L5X `
  --target plcopen `
  --output build\project.xml `
  --dry-run
```

Use JSON diagnostics for scripts and CI:

```powershell
uv run twinforge export project.L5X `
  --target plcopen `
  --output build\project.xml `
  --dry-run `
  --diagnostics-format json
```

Successful JSON is written to standard output. Failed JSON is written to
standard error. Export commands use these stable exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Success or successful readiness check |
| 2 | Invalid input, option, or configuration |
| 3 | Recognized but unsupported conversion |
| 4 | Schema or semantic validation failure |
| 5 | Operational failure |

## Export targets

- `plcopen` writes a PLCopen XML 2.01 file and accepts an optional PLCopen 2.01
  XSD.
- `codesys` writes a CODESYS-adapted PLCopen XML file and requires no
  additional local input.
- `openplc` writes a native OpenPLC project directory and accepts an optional
  versioned JSON configuration.
- `automationml` writes an AutomationML 2.1 / CAEX 3.0 file. It requires the
  AutomationML base library and accepts optional CAEX XSD and PLCopen inputs.
- `json` writes a deterministic, cycle-safe representation of the converted
  neutral model and retained source evidence.

Target-neutral PLCopen XML with optional validation:

```powershell
uv run twinforge export project.L5X `
  --target plcopen `
  --output build\project.xml `
  --xsd reference\PLCopenXML\standard\tc6_xml_v201.xsd
```

CODESYS-adapted PLCopen XML:

```powershell
uv run twinforge export project.L5X `
  --target codesys `
  --output build\codesys.xml
```

Neutral model JSON for downstream tools and inspection:

```powershell
uv run twinforge export project.L5X `
  --target json `
  --output build\project-model.json
```

Generated runtime UUIDs and parent back-references are not serialized. Shared
model objects are represented by stable `$ref` JSON pointers, while retained
source extensions and unknown L5X evidence remain in the document.

Validate a saved model document without reparsing its source L5X:

```powershell
uv run twinforge model validate build\project-model.json
```

The separate native CODESYS deployment workflow packages a validated
PowerFlex 525 application, native device-tree evidence, manifest, and import
instructions:

```powershell
uv run twinforge codesys bundle `
  examples\deployment\powerflex525_two_drive.json `
  --output build\powerflex525-codesys
```

Paths inside the deployment manifest, including `native_template`, resolve
relative to the manifest file. This command does not replace the ordinary
L5X-to-CODESYS PLCopen XML export above; it packages the separately proven
native EtherNet/IP deployment workflow.

Native OpenPLC project output:

```powershell
uv run twinforge export project.L5X `
  --target openplc `
  --output build\openplc `
  --config examples\OpenPLC\openplc-export.example.json
```

PLCopen and AutomationML configuration examples are available at:

```text
examples/PLCOpenXML/plcopen-export.example.json
examples/AutomationML/automationml-export.example.json
```

Paths inside these JSON documents resolve relative to the configuration file.
An explicit `--xsd`, `--base-library`, or `--plcopen-reference` argument
overrides the corresponding configured path.

AutomationML with the required base library:

```powershell
uv run twinforge export project.L5X `
  --target automationml `
  --output build\plant.aml `
  --base-library reference\AutomationML\AutomationML2.10BaseLibraries.aml
```

Add a CAEX XSD through `--xsd` or an existing PLCopen document through
`--plcopen-reference` when those checks and links are required.

## Offline and safety boundaries

- `inspect`, `report`, and `export` do not contact controllers or scan a
  network.
- `state` commands operate only on explicitly named local discovery-state
  files.
- No installed command currently starts live CIP or SNMP discovery implicitly.
- Source L5X extensions and unknown evidence remain preserved in the model.
- Successful conversion proves support for the admitted source shape; it does
  not prove runtime equivalence on every IEC 61131-3 platform.
- Generated control logic must receive the same engineering review and target
  runtime testing as manually translated PLC logic.

Run `uv run twinforge <command> --help` for the authoritative installed options.
