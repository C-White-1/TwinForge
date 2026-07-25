# AutomationML capability and validation

TwinForge exports the Booster Compressor model as AutomationML 2.1 using CAEX
3.0 structures observed in a native AutomationML Editor 6.4.3.5 file.

This is a validated project baseline, not a claim that every L5X or hardware
catalog can be represented completely.

## Generated content

The document contains:

- a system, controller, chassis and installed-module instance hierarchy;
- module slot, catalog, manufacturer and asset-type attributes;
- analogue and digital module-channel interfaces;
- analogue and digital process signals derived from L5X aliases;
- engineering units and configured lower/upper analogue ranges;
- links between assigned signals and physical module interfaces;
- a relative `PLCopenXMLInterface` reference to the generated control program;
- stable UUIDs derived from stable source identities; and
- source/provenance attributes for capacity and assignment evidence.

## Semantic libraries

TwinForge emits:

- role classes derived from the standard `Resource` role;
- analogue and digital interface classes derived from `SignalInterface`;
- typed attributes for identity, addressing, ranges and signals;
- vendor-neutral SystemUnitClasses for controllers, chassis, I/O modules,
  signal collections and process signals; and
- Rockwell catalog SystemUnitClasses derived from the vendor-neutral classes.

Every generated equipment and signal instance has a
`RefBaseSystemUnitPath`. The generated file also references the official
AutomationML 2.1 base-library document.

## I/O evidence

Capacity and usage are reported as different properties:

| Module | Nominal | Configured | Unavailable | Assigned | Spare |
| --- | ---: | ---: | ---: | ---: | ---: |
| `DI_Slot1` | 16 | 16 | 0 | 10 | 6 |
| `DI_Slot2` | 16 | 16 | 0 | 14 | 2 |
| `DO_Slot3` | 16 | 16 | 0 | 15 | 1 |
| `AI_Slot4` | 8 | 4 | 4 | 4 | 0 |
| `AO_Slot5` | 8 | 8 | 0 | 2 | 6 |
| `AI_Slot6` | 8 | 4 | 4 | 4 | 0 |

Nominal capacity comes from recognized Rockwell catalog evidence. Configured
analogue channel counts come from L5X configuration. Assignment includes both
aliases and direct `Local:` operands used by RLL, preventing directly addressed
outputs from being reported as spare.

These values describe the Booster Compressor fixture only.

## Generate and validate

```powershell
uv run python examples\export_automationml.py `
  tests\data\basic\BoosterCompressor_20260128.L5X `
  examples\AutomationML\BoosterCompressor.aml `
  --plcopen ..\PLCOpenXML\BoosterCompressor_codesys.xml `
  --base-library ..\..\reference\AutomationML\AutomationML2.10BaseLibraries.aml `
  --xsd reference\AutomationML\CAEX_ClassModel_V.3.0.xsd
```

Validation has two layers:

1. `lxml` validates CAEX structure and ordering against the CAEX 3.0 XSD.
2. TwinForge resolves local/external class paths, unique IDs, internal-link
   endpoints and PLCopen document references.

These layers are implemented independently. CAEX XSD validation does not
perform filesystem or class-reference resolution, while semantic validation
does not substitute for schema validation. Hierarchy construction,
class-library generation, signal/I/O generation and deterministic identity are
also separate exporter components behind the stable `AutomationMLExporter`
façade.

The generated file has also loaded successfully in AutomationML Editor.

## Editor review checklist

1. The system root contains the controller and local chassis.
2. Chassis slots contain the expected controller and I/O module types.
3. Signal collections contain analogue and digital I/O aliases.
4. Analogue signals carry units and configured ranges where evidence exists.
5. Digital modules contain their nominal points, including true spare points.
6. Internal links connect assigned signals to module interfaces.
7. CAEX validation and semantic reference checks report no errors.

## Current boundaries

- Physical channel and CIP assembly objects are not yet independently
  discovered.
- Catalog capacity decoding covers recognized evidence, not arbitrary modules.
- Four-wire or other configuration constraints must be represented as
  unavailable points when known; they cannot be derived safely from capacity
  alone.
- No confirmed Modbus register map exists in the Booster Compressor L5X.
- Successful AML validation does not establish executable control equivalence;
  that remains the role of the PLCopen/CODESYS validation path.
