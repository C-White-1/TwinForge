# OpenPLC native project compatibility experiment

This experiment originally intended to test TwinForge's target-neutral PLCopen
XML through an OpenPLC import. The observed OpenPLC editor can export PLCopen
XML or CODESYS XML but exposes no corresponding import operation. Native
compatibility must therefore be tested through its project-directory format.

Passing TwinForge's unit tests or the PLCopen XSD is not evidence that OpenPLC
loads or executes a generated native project. Record editor, build, and runtime
results separately.

## Native empty-project evidence

The ignored reference
`reference/OpenPLC/native-projects/plc_empty_file.xml` was created by OpenPLC
on 31 July 2026. It is a PLCopen XML representation, but it is not the complete
native working-project format.

The captured directory listing in
`reference/OpenPLC/native-projects/files.txt` establishes that the OpenPLC
working project is folder based:

```text
test/
├── project.json
├── devices/
│   ├── configuration.json
│   └── pin-mapping.json
└── pous/
    ├── function-blocks/
    ├── functions/
    └── programs/
        └── main.ld
```

The JSON files and separate IEC source files therefore form part of the native
project. The PLCopen XML file remains useful exchange evidence, but replacing
it alone must not be described as replacing an OpenPLC working project.

The language selected when creating the project determines the program source
extension. Ladder Diagram was selected for this fixture, producing
`pous/programs/main.ld`.

The native `main.ld` file is not ordinary IEC text and is not PLCopen XML. It
is a hybrid OpenPLC representation:

```text
PROGRAM main
VAR
END_VAR

{
  "name": "main",
  "rungs": []
}
END_PROGRAM
```

The IEC declaration envelope carries the program name and variables. The JSON
object carries OpenPLC's editable ladder model. A native OpenPLC packager must
serialize both parts faithfully.

`project.json` contains project metadata plus task, program-instance, and
global-variable configuration. The program entry is referenced by name
(`main`) but is not duplicated in its empty `pous` list; the source file under
`pous/programs` supplies the POU. Device concerns are separate:

- `devices/configuration.json` selects `OpenPLC Runtime v3` and contains
  communication settings;
- `devices/pin-mapping.json` contains the physical I/O mapping and is empty in
  this fixture.

This establishes three distinct OpenPLC target responsibilities:

1. application and scheduling metadata in `project.json`;
2. language-specific POU source serialization; and
3. optional runtime-device configuration and physical pin mapping.

These responsibilities must remain outside the generic PLCopen XML exporter.

The native file and TwinForge's smoke fixture both pass the official PLCopen
2.01 XSD. The native empty project establishes these OpenPLC defaults:

- PLCopen XML namespace `http://www.plcopen.org/xml/tc6_0201`;
- graphical scaling of `16` by `16`;
- program `main` with an empty `LD` body;
- configuration `Config0` and resource `Res0`;
- task `task0`, priority `1`, and interval `T#20ms`; and
- POU instance `instance0` referencing `main`.

TwinForge currently emits standards-valid equivalent concepts with descriptive
names and the ISO duration `PT0.02S`. These differences must not be treated as
OpenPLC requirements until native loading proves that OpenPLC rejects the
standard forms.

## Native basic-ladder evidence

The ignored `basic-ladder` project and `plc_basic_ladder.xml` export establish
the first populated Ladder representation:

- local declarations are ordinary IEC lines inside the `.ld` `VAR` block;
- each rung has a stable identity, comment, bounds, nodes, and directed edges;
- the serial rung contains left rail, contact, coil, and right rail nodes;
- nodes repeat measured geometry and connector metadata used by the editor;
- variables carry class, base type, location, initial value, documentation,
  and debug fields;
- edges identify source and target nodes plus their connector handles; and
- the PLCopen export translates the same native graph into standard LD
  elements and connection points.

The native IDs observed in the editor are generated values. TwinForge uses
deterministic UUIDs and numeric IDs derived from logical paths so repeated
exports remain byte stable. Native editor acceptance is still required to
confirm that OpenPLC treats these values as opaque identities.

`OpenPLCNativeProjectExporter` implements only this evidenced subset:

- one task scheduling one program;
- one Ladder routine;
- local `BOOL` variables and IEC `TON` instances;
- serial `XIC` conditions driving one `OTE`;
- two-path parallel `XIC` branches, with an optional trailing `XIC` or `XIO`;
- canonical Rockwell `TON`/`.DN` and `TOF`/`.DN` rung pairs lowered to their
  corresponding IEC timer networks;
  and
- optional timer elapsed-time telemetry at an explicit `%MD` location.

It rejects unsupported programs before creating the destination, rather than
silently dropping behavior or guessing unevidenced node schemas.

The OpenPLC compiler requires its primary program to be named exactly `main`
in lowercase. A different name can open in the editor but compilation fails
with the misleading message `Error generating XML from JSON: XML data is not
a string`. TwinForge therefore maps the selected source program name to native
`main` and reports both names in the export result. The source model and its
original program identity remain unchanged. This behavior is also confirmed
by the OpenPLC maintainer in the
[OpenPLC forum](https://openplc.discussion.community/post/openplc-error-generating-xml-from-jsonerrorxml-data-is-not-a-string-13763951).

## PLCopen XML comparison fixture

Generate the minimal fixture:

```powershell
uv run python examples/export_openplc_smoke.py `
  examples/OpenPLC/01_basic_ladder.xml `
  --native-destination examples/OpenPLC/native-smoke `
  --xsd reference/PLCopenXML/standard/tc6_xml_v201.xsd
```

The paired fixtures contain:

- controller `OpenPLCSmoke`;
- program `PLC_PRG`;
- periodic task `MainTask`;
- Boolean variables `Enable` and `Output`; and
- one ladder rung equivalent to `XIC(Enable)OTE(Output)`.

The native directory is generated by
`OpenPLCNativeProjectExporter`; the XML is generated independently by the
standards-based `OpenPLCExporter`.

The generated XML remains useful for schema validation and for comparison with
an XML export of the equivalent native OpenPLC project. It is not currently a
known project-loading mechanism.

## Stage 1: native project smoke fixture

Create or generate a native OpenPLC project directory containing the same
two-variable, one-rung program. Open the directory in OpenPLC and record the
OpenPLC product and version, operating system, load diagnostics, and whether
the program, task, variables, and ladder body appear.

Build the project before attempting runtime validation. If it builds, run it
with no physical I/O mapping:

1. Confirm `Output` is false while `Enable` is false.
2. Set or force `Enable` true and confirm `Output` becomes true.
3. Return `Enable` to false and confirm `Output` becomes false.
4. Record any manual edits required by OpenPLC.

Do not mark native compatibility complete if the project opens but does not
build or the rung does not execute.

Record the result here after the native test:

| Check | Result | Evidence or required edit |
| --- | --- | --- |
| PLCopen 2.01 XSD validation | Passed | Official local XSD, 30 July 2026 |
| Native project opened | Passed | OpenPLC Editor, Windows, 31 July 2026 |
| Source `PLC_PRG` mapped to native `main` | Passed | Required compiler mapping |
| `MainTask` present and scheduled | Passed | Generated ST uses `T#20ms` |
| `Enable` and `Output` present | Passed | Both emitted as debug BOOLs |
| Ladder rung compiled | Passed | Generated ST is `Output := Enable;` |
| Project built | Passed | IEC2C Stage 1 and C generation succeeded |
| Located variables monitored | Passed | `%QX0.0` and `%QX0.1` |
| False/true/false runtime behavior passed | Passed | Runtime v3 Monitoring |

The editor generated `plc.xml`, `program.st`, IEC C sources, debug metadata,
and glue variables successfully. A second build with `compileOnly` explicitly
enabled completed the same stages and intentionally skipped runtime upload.
That final message is a selected deployment mode, not a compilation failure.
The generated smoke fixture now records `compileOnly: true` reproducibly.

The runtime Monitoring page polls Modbus data rather than displaying arbitrary
unlocated program locals. The first generated program therefore ran correctly
but produced an empty Monitoring table. The native located-variable fixture
establishes the required declaration form:

```text
Enable : bool AT %QX0.0;
Output : bool AT %QX0.1;
```

OpenPLC leaves each Ladder node's JSON `variable.location` field empty; the
location exists only in the IEC declaration envelope. TwinForge consequently
accepts locations as explicit OpenPLC deployment configuration rather than
adding them to the neutral `Tag` model. The proven exporter subset accepts
`%IX<byte>.<bit>` and `%QX<byte>.<bit>` Boolean locations. OpenPLC Runtime
Monitoring correctly treats `%IX` points as read-only, so the serial-AND
compatibility experiment keeps two separate fixtures:

- `native-serial-and` uses hardware-faithful `%IX` contacts; and
- `native-serial-and-simulation` deliberately maps its contact variables to
  writable `%QX` points for a repeatable runtime truth-table test.

The simulation mapping is deployment-test configuration, not a claim that the
two contact operands are physical outputs.

### Timer elapsed-time telemetry

OpenPLC does not permit a located `TIME` variable. A native compatibility
experiment therefore connected the IEC `TON.ET` output to a local `TIME`, then
used OpenPLC's `TIME_TO_DINT` block to expose whole elapsed seconds through a
located `DINT`:

```text
DelayTimer_ET : TIME;
DelayTimer_ElapsedSeconds : DINT AT %MD0;
```

The runtime experiment compiled and the monitored value advanced as expected.
In the tested OpenPLC implementation, `TIME_TO_DINT` returns whole seconds;
this is not a millisecond representation. `%MD0` is a 32-bit internal-memory
double word and occupies two consecutive 16-bit Modbus holding registers.

TwinForge keeps this mapping target-specific. Callers opt in with
`timer_elapsed_locations={"DelayTimer": "%MD0"}`; no located telemetry tag is
invented in the neutral controller model. Unknown timer names and locations
outside the evidenced `%MD<number>` form are rejected before files are written.
The current elapsed-time option is restricted to `TON`; it will not be claimed
for `TOF` until the generated ET path is independently runtime-tested.

### Off-delay timer evidence

An OpenPLC Editor project using `DelayTimer : TOF` compiled on 3 August 2026.
Runtime tests confirmed all three defining behaviors:

- `Q` becomes true immediately when `IN` becomes true;
- `Q` remains true for the five-second preset after `IN` becomes false; and
- returning `IN` true during that interval cancels the pending off-delay.

The captured native graph uses the same `IN`, `PT`, `Q`, and `ET` connector
shape as `TON`, while preserving `TOF` in both the IEC declaration and block
metadata. TwinForge therefore shares graph construction but carries the timer
instruction kind explicitly; it does not rewrite `TOF` as `TON`.

The independently generated `native-tof-generated` fixture subsequently
opened and compiled successfully in OpenPLC. Its runtime behavior also passed
the immediate-on, five-second delayed-off, and cancellation checks without
manual changes, validating the complete TwinForge generation path.

The native project's PLCopen XML export should also be retained as comparison
evidence. It can reveal semantic differences between TwinForge's generic XML
and OpenPLC's serialization, even though it cannot currently be loaded through
the editor.

## Stage 2: representative L5X conversion

After Stage 1 succeeds, generate a real L5X conversion:

```powershell
uv run python examples/export_openplc.py `
  tests/data/basic/BoosterCompressor_20260128.L5X `
  examples/OpenPLC/02_booster_compressor.xml `
  --creation-time 2026-07-30T00:00:00Z
```

For a future native OpenPLC package generated from this larger document,
distinguish:

- native project load failures;
- unsupported IEC or ladder constructs;
- unresolved Rockwell operands or instructions;
- task/program scheduling differences; and
- runtime behavior differences.

The Stage 2 result is a capability-discovery artifact. It is not expected to
have the same initial success criteria as the deliberately small Stage 1
fixture.
