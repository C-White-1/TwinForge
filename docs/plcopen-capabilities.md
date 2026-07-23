# L5X to PLCopen XML capability matrix

This document describes TwinForge's current, tested conversion boundary. It is
not a claim that arbitrary Logix projects can be converted without review.

Status terms:

- **Parsed**: represented in TwinForge's vendor-neutral model.
- **Preserved**: retained in source extensions or PLCopen `addData`, but not
  necessarily executable in the target.
- **Converted**: emitted as PLCopen XML.
- **CODESYS-tested**: imported and precompiled successfully in the CODESYS
  environment used for the TwinForge fixtures.

## Validation baseline

The current end-to-end reference is
`tests/data/basic/BoosterCompressor_20260128.L5X`.

Its generated CODESYS document:

- imports successfully;
- precompiles with zero errors;
- contains zero unsupported RLL rungs;
- preserves five intentional `NOP()` rungs as no-operations.

The automated suite currently contains 74 passing tests. The standard profile
is also validated against the PLCopen XML 2.01 XSD. CODESYS-specific output
uses the `tc6_0200` namespace and structures learned from native CODESYS
exports.

This is strong evidence for the tested feature set, but it is still one
representative Logix application rather than a broad compatibility corpus.

## L5X parsing and model conversion

| L5X content | Current status | Notes |
| --- | --- | --- |
| Controller identity and revision | Parsed and preserved | Includes known attributes and source extensions. |
| Modules and electronic keys | Parsed and preserved | Vendor identity, catalog number, slot/parent information and keying data are modelled. |
| Data types | Parsed and preserved | Definitions and members are modelled; this does not imply PLCopen UDT export. |
| Controller tags | Parsed and preserved | All source data representations remain available in source extensions. |
| Program tags | Parsed and preserved | Parent and scope relationships are retained. |
| Programs and routines | Parsed and preserved | RLL rung number, comment and source text are retained. |
| Tasks | Parsed and preserved | Type, priority, rate and scheduled-program references are resolved where possible. |
| Unknown attributes and elements | Preserved | TwinForge does not intentionally discard unrecognised L5X content. |

Parsing or preservation does not automatically mean that an item has an
executable PLCopen representation.

## PLCopen project structure

| Feature | Standard 2.01 | CODESYS profile |
| --- | --- | --- |
| Controller/global variables | Converted | Converted as `ControllerTags` |
| Program-local variables | Converted | Converted |
| Programs | Converted as POUs | Converted as CODESYS POUs |
| Non-main routines | Converted as actions | Converted as CODESYS actions |
| `JSR(routine,0)` | Action call | Native CODESYS action call |
| Tasks | Converted | Converted with CODESYS task settings |
| Scheduled programs | Converted | Converted |
| Standard library dependency | Not applicable | Emitted when timers or edge triggers require it |
| Deterministic object identifiers | Not applicable | Emitted for CODESYS project objects |

Only the exact `JSR(routine,0)` form is currently recognised. Unresolved calls
are preserved and diagnosed.

## Tag and variable conversion

Scalar variables using these IEC-compatible types are exported:

`BOOL`, `BYTE`, `WORD`, `DWORD`, `LWORD`, `SINT`, `INT`, `DINT`, `LINT`,
`USINT`, `UINT`, `UDINT`, `ULINT`, `REAL`, `LREAL`, `STRING`, `WSTRING`,
`TIME`, `DATE`, `TIME_OF_DAY`, and `DATE_AND_TIME`.

Additional behaviour:

- Rockwell `TIMER` tags used by supported logic are emitted as
  `Standard.TON` instances in the CODESYS profile.
- Alias tags become portable surrogate variables. Their original `AliasFor`
  targets are preserved in `addData`, but physical I/O bindings are not
  recreated.
- Raw Logix addresses such as `Local:1:I.Data.0` become deterministic,
  IEC-safe surrogate variables. The original operands are preserved.
- Descriptions are exported as documentation.

Current variable limitations:

- arrays are not exported;
- user-defined and other structured types are not exported as PLCopen data
  types;
- general tag initial values are not yet exported;
- produced/consumed tag behaviour is not recreated;
- physical module-channel bindings are not recreated.

## Executable RLL conversion

### Contacts, coils and branches

| Rockwell instruction/structure | PLCopen/CODESYS conversion |
| --- | --- |
| `XIC` | Normally-open contact |
| `XIO` | Negated contact |
| `OTE` | Coil |
| `OTL` | Set/storage coil |
| `OTU` | Reset/storage coil |
| Multiple output coils | Parallel outputs from the same condition |
| Top-level parallel paths | Parallel contact paths merged before the serial tail |

Branch support is deliberately limited. The current parser supports one
top-level parallel branch group whose paths contain `XIC` and `XIO`.
Nested branches and arbitrary instructions inside branch paths are not yet
supported.

### Comparisons

| Rockwell | CODESYS operator |
| --- | --- |
| `EQU` | `EQ` |
| `NEQ` | `NE` |
| `GRT` | `GT` |
| `GEQ` | `GE` |
| `LES` | `LT` |
| `LEQ` | `LE` |

Comparison results are written to generated Boolean variables and then used as
ladder contacts. Rockwell timer `.ACC` operands map to IEC timer `ET`; DINT
millisecond operands are converted with `DINT_TO_TIME(...)`.

### Data movement and arithmetic

| Rockwell | CODESYS operator |
| --- | --- |
| `MOV` | `MOVE` |
| `ADD` | `ADD` |
| `SUB` | `SUB` |
| `MUL` | `MUL` |
| `DIV` | `DIV` |

Operators on the same Rockwell rung are linked through `ENO` to preserve
left-to-right execution order. Destinations are emitted as direct output
expressions.

### Timers

| Rockwell feature | Conversion |
| --- | --- |
| `TIMER` tag used by `TON` | `Standard.TON` instance |
| `TON(timer,?,?)` | Native CODESYS TON function-block call |
| `PRE` | Decorated L5X millisecond value converted to IEC `TIME` |
| `.ACC` | Generated `TIME` variable connected to `ET` |
| `RES(timer)` | Conditional TON call with `IN := FALSE` |

The currently implemented timer family is `TON`. `TOF`, `RTO` and other
timer variants have not been implemented. Rockwell `.EN`, `.TT`, `.DN` and
arbitrary direct member usage have not been generally mapped; the tested
application uses `.ACC`.

### One-shots and no-operations

| Rockwell | Conversion |
| --- | --- |
| `ONS(storage)` | Persistent `Standard.R_TRIG` instance |
| `NOP()` | Preserved intentional no-operation |

The incoming rung condition is captured, `R_TRIG` is executed every scan, and
subsequent instructions continue from its one-scan `Q` pulse. The original
Rockwell ONS storage operand is preserved in TwinForge extension metadata.

## Preservation and diagnostics

If a rung cannot be converted, TwinForge emits it as a non-executable comment
and preserves the original RLL text in PLCopen `addData`. It also returns a
conversion diagnostic. Unsupported variables, unresolved JSR targets, raw
operand rewrites, alias surrogates and missing timer presets are similarly
diagnosed.

The rule is: unsupported content may become non-executable, but it must not
silently disappear.

## Known unimplemented areas

The following are examples, not an exhaustive list:

- nested or complex branch structures;
- `TOF`, `RTO`, counters and sequencers;
- `CPT`, `COP`, `CPS`, `FLL`, `LIM`, `MEQ` and many bit/word instructions;
- PID/PIDE, MSG, motion, safety and redundancy-specific execution semantics;
- Add-On Instruction definitions and calls;
- structured-text, function-block and SFC routine bodies;
- arrays, indirect addressing and full UDT/AOI data conversion;
- physical I/O and produced/consumed tag bindings;
- exact cross-vendor equivalence for every Logix scan or fault behaviour.

Some unlisted instructions may already be safely captured and preserved by the
L5X pipeline even though they are not executable in PLCopen output.

## Compatibility expectations for another L5X file

Before treating a conversion as successful:

1. Review all exporter diagnostics.
2. Confirm the count and text of preserved non-executable rungs.
3. Validate standard output against the PLCopen 2.01 XSD when applicable.
4. Import the CODESYS profile into a clean test project.
5. Precompile and inspect variable declarations and ladder networks.
6. Compare timer, one-shot, latch and arithmetic behaviour against the Logix
   source.
7. Perform an application-level simulation or controlled commissioning test.

Do not infer runtime equivalence merely from a successful XML import or zero
precompile errors.

## Command-line example

```powershell
.\.venv\Scripts\python.exe examples\export_plcopen.py `
  path\to\project.L5X `
  path\to\project_codesys.xml `
  --profile codesys
```

For standard PLCopen XML:

```powershell
.\.venv\Scripts\python.exe examples\export_plcopen.py `
  path\to\project.L5X `
  path\to\project_plcopen.xml `
  --profile standard_201 `
  --xsd reference\PLCopenXML\tc6_xml_v201.xsd
```
