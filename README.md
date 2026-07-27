# TwinForge

TwinForge is a specification-driven, vendor-neutral industrial automation
toolkit. It currently imports Rockwell L5X projects into a lossless domain
model and exports tested PLCopen XML and AutomationML representations.

## Current validated baseline

The primary fixture is:

```text
tests/data/basic/BoosterCompressor_20260128.L5X
```

Current results:

- 192 automated tests pass;
- all 134 RLL rungs and 474 instruction occurrences in the fixture convert;
- generated CODESYS PLCopen XML imports and precompiles with zero errors;
- standard PLCopen XML validates against the PLCopen 2.01 XSD;
- generated AutomationML loads in AutomationML Editor;
- AutomationML validates against the CAEX 3.0 XSD; and
- local and external AutomationML class, link and document references resolve;
  and
- Pyright reports zero errors and warnings for the maintained package, tests
  and examples.

These results establish the tested boundary for this fixture. They are not a
claim of universal L5X or IEC 61131-3 compatibility.

## Processing architecture

```text
Specification
    ↓
Capture
    ↓
CapturedSection
    ↓
L5X converters
    ↓
Vendor-neutral model
    ├── analysis and enrichment
    ├── PLCopen XML exporter
    └── AutomationML exporter
```

Unknown L5X attributes and elements are preserved as source extensions.
Exporters consume the model and never parse L5X directly.

## Implemented areas

- Controller, module and electronic-key identity
- Chassis, slots, module connections and parent relationships
- Datatypes, controller/program tags and scalar exported values
- Add-On Instructions, parameters, typed defaults and Structured Text source
- Programs, routines, RLL rungs, tasks and scheduled-program references
- Module engineering units and configured analogue ranges
- Nominal, configured, assigned, unavailable and spare I/O evidence
- Project-specific RLL conversion coverage analysis
- PLCopen XML 2.01 and CODESYS-targeted output
- AutomationML 2.1 / CAEX 3.0 hierarchy, semantic libraries and links
- Vendor-neutral and Rockwell catalog SystemUnitClasses
- Model-driven controller, tag, datatype, module, task and program reports
- Vendor-neutral device parameter and setpoint reports in Markdown and CSV

## Quick start

Install development dependencies:

```powershell
uv sync --extra validation
```

Parse the reference L5X:

```powershell
uv run python examples\parse_l5x.py `
  tests\data\basic\BoosterCompressor_20260128.L5X
```

Run tests:

```powershell
uv run pytest
```

Run static type checking:

```powershell
uv run pyright
```

Pyright uses `standard` mode for `src/twinforge`, `tests`, and maintained
examples. The legacy `examples/build_twin.py` live-discovery sketch is excluded
until its underlying API is implemented.

Generate PLCopen XML:

```powershell
uv run python examples\export_plcopen.py `
  tests\data\basic\BoosterCompressor_20260128.L5X `
  examples\PLCOpenXML\BoosterCompressor_codesys.xml `
  --profile codesys
```

Generate human-readable engineering reports:

```powershell
uv run python examples\export_reports.py `
  tests\data\basic\BoosterCompressor_20260128.L5X `
  reports\BoosterCompressor
```

The report exporter consumes the vendor-neutral model rather than parsing L5X
directly. Reports therefore include promoted scalar values, engineering units,
ranges, resolved task/program relationships and preserved RLL source text.
AOI reports include parameters, typed defaults and numbered Structured Text
source lines.

Assess captured AOIs before selecting an IEC 61131-3 conversion strategy:

```powershell
uv run python examples\analyze_aoi_portability.py `
  tests\data\aoi\Str_Capacity_AOI.L5X `
  --output reports\Str_Capacity_AOI\aoi_portability.txt `
  --puml reports\Str_Capacity_AOI\aoi_portability.puml
```

The analyzer recommends a function or function block and classifies each AOI
as a portable candidate, adapter required, or manual review. Its conclusions
are conservative and evidence-based: they identify retained state, lifecycle
hooks, dependencies, referenced data types, Structured Text calls and known
Rockwell services. A portable-candidate result is not proof of semantic
equivalence on another runtime.

Measure lossless Structured Text syntax coverage:

```powershell
uv run python examples\analyze_structured_text.py `
  tests\data\aoi\Str_Capacity_AOI.L5X `
  --output reports\Str_Capacity_AOI\structured_text_analysis.txt
```

Export a supported Structured Text AOI through executable IR to a CODESYS
PLCopen XML function block:

```powershell
uv run python examples\export_aoi_codesys.py `
  tests\data\aoi\Str_Capacity_AOI.L5X `
  examples\PLCOpenXML\Str_Capacity_codesys.xml
```

This path applies the explicit `promote_written_inputs` normalization policy
and reports both its audit diagnostics and any unresolved target requirement.
The current evidence-backed target mappings cover CODESYS variable-length
`VAR_IN_OUT` arrays and Rockwell `SIZE` array-dimension semantics. The example
also emits an explicit ten-element test binding, `PLC_PRG`, its function-block
call, and a 20 ms cyclic `MainTask`.

Generate and validate AutomationML:

```powershell
uv run python examples\export_automationml.py `
  tests\data\basic\BoosterCompressor_20260128.L5X `
  examples\AutomationML\BoosterCompressor.aml `
  --plcopen ..\PLCOpenXML\BoosterCompressor_codesys.xml `
  --base-library ..\..\reference\AutomationML\AutomationML2.10BaseLibraries.aml `
  --xsd reference\AutomationML\CAEX_ClassModel_V.3.0.xsd
```

The `reference/` directory is intentionally ignored. Standards documents and
schemas must be obtained from their official publishers and supplied locally.

## Detailed documentation

- [Architecture](ARCHITECTURE.md)
- [Domain model](MODEL.md)
- [Roadmap](ROADMAP.md)
- [Parameter and setpoint reports](docs/parameter-reports.md)
- [PLCopen capability matrix](docs/plcopen-capabilities.md)
- [AOI portability and runtime contracts](docs/aoi-portability.md)
- [Structured Text front end](docs/structured-text.md)
- [Executable intermediate representation](docs/executable-ir.md)
- [AutomationML capability and validation](docs/automationml-proof-of-concept.md)
- [PLCopen reference handling](docs/standards/plcopen.md)
- [AutomationML reference handling](docs/standards/automationml.md)
