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
