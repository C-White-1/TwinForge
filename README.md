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

- 94 automated tests pass;
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
- Programs, routines, RLL rungs, tasks and scheduled-program references
- Module engineering units and configured analogue ranges
- Nominal, configured, assigned, unavailable and spare I/O evidence
- Project-specific RLL conversion coverage analysis
- PLCopen XML 2.01 and CODESYS-targeted output
- AutomationML 2.1 / CAEX 3.0 hierarchy, semantic libraries and links
- Vendor-neutral and Rockwell catalog SystemUnitClasses

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
- [PLCopen capability matrix](docs/plcopen-capabilities.md)
- [AutomationML capability and validation](docs/automationml-proof-of-concept.md)
- [PLCopen reference handling](docs/standards/plcopen.md)
- [AutomationML reference handling](docs/standards/automationml.md)
