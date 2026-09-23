# Control Expert exchange capture: provisional specification

Status: provisional specification with read-only capture, basic neutral mapping
and graphical object evidence, 2026-09-20. Graphical execution mapping and editor validation remain
unimplemented.
Rules below are proposed TwinForge requirements,
not a claim to reproduce Schneider's complete exchange grammar.

## Evidence and limits

Delivery status, remaining milestones and the next implementation step are
tracked in the [Control Expert roadmap](../roadmaps/control-expert-roadmap.md),
including the safety-scope note covering the M580 safety fixture used below.
This document owns technical observations and mapping decisions.

Five user-supplied ZIP archives are held in ignored
`reference/control-expert/`. The adjacent `inventory.json` records SHA-256
hashes, sizes, archive-member order, CRCs, source-page associations, and metadata
for every standalone and embedded XEF. Reproduce it with:

```powershell
python reference/control-expert/inventory_samples.py
```

The script is a local research aid, not a production capture implementation.
It reads the archives without extracting or rewriting them. Inspection checked
ZIP integrity and XML well-formedness, not XSD validity, editor acceptance,
compilation, or execution. Source URLs are the recommended pages associated
with the outer filenames; the user's actual download origins were not verified.
Redistribution permission has not been established; external files remain local
under the [artifact policy](../artifact-policy.md).

| Outer archive | Embedded ZEF | Exporter | Platform | Sections | Variable declarations |
| --- | --- | --- | --- | --- | --- |
| `cread_reg.zip` | `cwrite_reg.zef` | Unity Pro XL 8.1 | Quantum | 1 ST, 1 FBD | 11 |
| `cwrite_reg.zip` | `cread_reg.zef` | Unity Pro XL 8.0 | Quantum | 1 ST, 1 FBD | 13 |
| `function15.zip` | `mbp_mstr15.zef` | Unity Pro XL 8.1 | Quantum | 2 ST, 2 LD | 22 |
| `function2.zip` | `mbp_mstrf2.zef` | Unity Pro XL 8.1 | Quantum | 1 ST, 2 LD | 21 |
| `readvar.zip` | `readvar.zef` | Unity Pro XL 10.0 | Premium | 1 ST, 1 FBD | 7 |

Counts refer to embedded `unitpro.xef`, with variables counted only under
`dataBlock`. Library parameter declarations are not global variables.

Important discrepancies:

- `cread_reg.zip` contains a CWRITE_REG project in both its XEF and ZEF.
- `cwrite_reg.zip` contains a CREAD_REG ZEF but a CWRITE_REG standalone XEF;
  these are different projects/export versions, not interchangeable copies.
- The READ_VAR source page describes LD; the inspected project contains FBD.
- In function15, reset initialization repeatedly assigns `noecontrol16[0]`,
  overwriting its initial operation code. A Ladder comment also disagrees with
  the ST destination address. Preserve these observations; do not repair input.

### Exact outer-archive identities

| Archive | SHA-256 |
| --- | --- |
| `cread_reg.zip` | `d0f70e5c09b0220dfa33ddf12893217f68e67d4145d234c891a036d5076e5f4f` |
| `cwrite_reg.zip` | `04ccc0962a1b48fca8a82980132b1bf078655d99318545b921c7255d17fa2a15` |
| `function15.zip` | `86ad8cc456bd19c14707e6777e79c3fe321b2a5413f6ae44e0d22620b258d9a6` |
| `function2.zip` | `f61f6b43b177575ed382e0fa8734da44858e325ef2d060f20583f26e2b383e64` |
| `readvar.zip` | `8a014ff02f5755eaf11a393d67322537a2c40227826e513417b33e2937068b6a` |

## Observed container and XML structure

All five ZEFs are readable ZIP containers containing:

```text
DTM/
DTM/BinaryFile/
DTM/FDTDTMTopology.xml
Project_Definition.xpdf
unitpro.xef
```

The embedded XEFs use `ZEFExchangeFile`; standalone XEFs use `FEFExchangeFile`.
Both use UTF-8 XML. All report
`fileHeader/@DTDVersion="41"`; this value spans three exporter versions and
must not be interpreted as a unique software release or compatibility promise.
The DTM files inspected contain UTF-16LE XML with an empty device topology.
The XPDF begins with XML referencing `unity.xsd` and a `crypted` element;
its payload has not been decoded. None of these observations establishes a
mandatory filename, encoding, or member set for all ZEF versions.

| Observed selector, relative to either exchange root | Captured information | Initial interpretation boundary |
| --- | --- | --- |
| `fileHeader`, `contentHeader` | Producer, version strings, dates, DTD marker | Preserve original strings; no release mapping inferred |
| `IOConf` | Nested CPU, bus, rack, supply and module configuration | Retain hierarchy and addresses; repeated CPU entries need not be separate devices |
| `commParameters`, `comm` | Engineering connection and configured network data | Distinguish editor/simulator addresses from application communication |
| `logicConf/resource/taskDesc/sectionDesc` | Resource, task attributes and ordered section references | Observed tasks are cyclic MAST only; retain raw timing values without invented units |
| `dataBlock/variables` | Name, type expression, optional address, comments, initialization | Separate symbols, type references and memory bindings |
| `EFSource`, `EFBSource` | Library identity, versions, attributes and parameter descriptions | Signatures are not executable implementations |
| `program/identProgram` | Section name, type and task reference | Resolve against task configuration with diagnostics for conflicts |
| `program/STSource` | Source text and comments | Preserve exact member bytes as well as decoded text |
| `program/LDSource` | Contacts, blocks, pins, grid rows, links and annotations | Preserve topology and layout; execution semantics remain unresolved |
| `program/FBDSource` | Blocks, parameter bindings and graphical structure | Preserve entire subtree pending a dedicated language specification |
| `animationTable` | Watch expressions, nested entries and display attributes | Engineering metadata, not runtime values |
| `DTMConfiguration`, `Motion`, `IOScreen`, `Documentation`, `settings` | Other project data, including empty sections | Retain even when no neutral interpretation exists |

Observed variable types include BOOL, INT, DINT, WORD, TIME, STRING, array
expressions, library types such as WordArr5 and ADDR_TYPE, and block-instance
types. Array lower bounds include both zero and one. Resolve named types only
with supporting definitions; preserve unresolved references explicitly.

## Proposed capture contract

Follow the repository pipeline:

```text
Specification -> Capture -> CapturedSection -> Parser -> Model
```

1. Retain the original input bytes and hash. Record each archive member by
   ordinal and original name, with bytes and hash, including unknown members
   and directory entries. Do not key solely by filename: duplicate names must
   remain distinguishable. A distribution ZIP is provenance packaging; each
   contained XEF/ZEF remains an independent candidate project.
2. Inspect containers within explicit size, expansion and nesting limits.
   Do not extract untrusted member paths or resolve XML external entities.
   Report encrypted, corrupt or unsupported content explicitly and retain its
   original bytes; never turn capture failure into an apparently empty project.
3. Use declarative element/attribute specifications to classify XML. Preserve
   qualified names, raw attributes, text, tails and child order, including
   unknown subtrees. Raw member bytes are authoritative for comments, encoding,
   whitespace and other lexical details a parsed tree may not retain.
4. Carry archive hash, member ordinal/path and XML location into captured
   sections and parser diagnostics. Label rules as observed, documented or
   proposed, with their evidence references and tested exporter versions.
5. Missing or novel structures produce explicit coverage diagnostics. An
   observed field is not universally required merely because five files have it.
   Never discard data because a DTD marker, type or attribute is unfamiliar.
6. Parse captured sections into neutral concepts: controller, hardware, task,
   program section, variable, type reference and source-language content.
   Keep Schneider-specific configuration in associated source evidence or
   extensions instead of making the neutral model vendor-specific.

The existing L5X `ElementSpec` and `CapturedSection` illustrate this architecture,
but live under L5X-specific modules. Decide shared contracts and migration impact
before reusing or generalizing them; this document does not authorize a broad
L5X refactor or relax its preservation guarantees.

## Implementation gates and acceptance evidence

### Installed inspection command

```powershell
uv run twinforge control-expert inspect reference\control-expert\function15.zip
uv run twinforge control-expert inspect reference\control-expert\function15.zip --format json
```

The command inventories each project separately with source member ordinals and
hashes, task schedule, section languages, hardware, variable declarations and
diagnostics. JSON includes graphical objects and pins. Reports are deterministic
and omit runtime UUIDs and raw source bytes. They are inspection summaries, not
the existing L5X model-JSON contract or lossless source replacements.

Report version `1.0` uses `report_type="control_expert_inspection"`. Status is
`inspected`, `incomplete_capture`, or `no_supported_projects`; native validation
is always `not_performed`. Capture failures or absent supported projects return
exit code 1 while still emitting available inspection evidence. Mapping coverage
diagnostics alone do not cause failure. See [offline usage](../offline-usage.md).

### Initial capture API

```python
from twinforge.parsers.control_expert import capture_file

captured = capture_file("reference/control-expert/function15.zip")
for project in captured.members:
    print(project.name, project.sha256, project.diagnostics)
```

This capture API accepts standalone XEF, ZEF and distribution ZIP files.
The provisional schema lives
under `twinforge.schema.control_expert`; no L5X modules were changed.
`CapturedArtifact` retains original bytes and ordered nested members;
`CapturedSection` retains ordered XML content, raw attributes and the matching
specification, or `None` for unclassified nodes. XML locations use zero-based
child ordinals, not XPath expressions. Comments and processing instructions
inside the root are captured; original bytes also preserve document-level data.

Diagnostics must be checked recursively on members. `unclassified_content` and
`unclassified_xml` indicate retained material outside the provisional grammar,
not malformed XML. Read/parse/limit diagnostics indicate incomplete inspection.
A member that could not be read has `raw_bytes=None`, not empty bytes; its parent
archive retains the stored representation. Member-count limits leave remaining
entries in the parent bytes without individual records. Unknown DTD marker
values remain strings and are not grounds for rejection.

`CaptureLimits` bounds input, individual and aggregate expanded bytes, archive
members, archive depth, and XML element depth/count. `capture_file` raises on
an oversized input before loading the entire file. `capture_bytes` retains an
already-loaded oversized input and reports it without inspection. DTD declarations
are rejected without entity resolution. No archive paths are extracted.

Tests in `tests/test_control_expert_capture.py` use independent synthetic files
plus an explicitly optional local-reference check. The local inventory script
is separate from this production API.

### Basic neutral mapping API

```python
from twinforge.parsers.control_expert import capture_file, parse_projects

captured = capture_file("reference/control-expert/function15.zip")
projects = parse_projects(captured)
for project in projects:
    print(project.artifact.source.members)
    print(project.controller)
    for diagnostic in project.diagnostics:
        print(diagnostic.code, diagnostic.message)
```

`parse_project` requires one captured exchange XML artifact. `parse_projects`
walks archive members and returns each exchange document independently, in
archive order. Standalone and embedded exports are never automatically merged
or treated as equivalent. An empty result does not establish successful parsing;
callers must also inspect recursive capture diagnostics for unreadable inputs.

The mapping profile in `schema/control_expert/mapping.py` supplies declarative
paths, hardware layouts, source-language names and the limited observed type
vocabulary. The mapper consumes `CapturedSection`, not XML trees. The graphical
stage adds optional neutral diagram evidence to routines; L5X parsing is unchanged.

Current mapping decisions:

- Controller name comes from the content header. Producer, timestamps, versions,
  configuration and all unknown nodes remain in its complete source extension.
  The parsed result also retains the captured XML artifact and original bytes.
- Each source section becomes one neutral `Program` with one main `Routine`
  when exactly one supported body exists. This is a representation choice to
  express section execution order through `Task.scheduled_programs`, not a claim
  that Control Expert sections have Logix program semantics.
- Task references resolve case-insensitively against section names, using
  `sectionDesc` order rather than XML program order. Missing, duplicate or
  conflicting task/section identities produce diagnostics and unresolved links.
  Raw names and task attributes remain available. Timing units are not inferred.
- ST text populates numbered `StructuredTextLine` objects without trimming;
  decoded line breaks and a final newline are retained. No ST execution or
  compilation is performed. LD/FBD routines retain source and language, and
  expose graphical objects as described below. They have no executable networks;
  diagnostics identify this limitation.
- Variable names, type expressions and comments become `Tag` fields. Source
  addresses live in `metadata["source_memory_address"]`, never `alias_for`.
  Initializers remain lexical evidence, with diagnostics rather than fabricated
  runtime values. Named library/custom types remain unresolved.
- One-dimensional array bounds live in `metadata["source_array_bounds"]` and
  their element type in `metadata["source_array_element_type"]`. Full source
  type expressions remain in `data_type`; `dimensions` stays unset because the
  existing neutral field does not encode lower bounds. Array types are explicitly
  unresolved for conversion. More complex expressions remain source evidence.
- Observed Quantum/Premium racks become `Chassis` objects. Rack-module records
  supply module catalog identities and nonnegative slots. The top-level PLC
  description supplies controller identity rather than creating an extra module.
  Special positions (such as Premium supply position `-1`), conflicting slots
  and incomplete module identities produce unplaced modules with diagnostics.
  Raw vendor names and revision strings remain evidence; numeric vendor IDs and
  firmware interpretation are not invented. Unsupported hardware layouts remain
  in the controller extension with an explicit unresolved-hardware diagnostic.

Source extensions include input hash, archive member ordinals/names and XML
location. They preserve duplicate declarations even when only the first can be
represented in a name-keyed neutral collection. Downstream exporters must not
treat these partial models as validated executable conversions.

`tests/test_control_expert_project.py` verifies scheduling, source preservation,
case/identity conflicts, arrays and addresses, hardware placement and optional
sample reconciliation. All five embedded projects reconcile to the inventory's
variable/section counts; the read/write ZIP's differing projects remain distinct.

### Graphical object evidence

`Routine.graphical_diagrams` holds vendor-neutral `GraphicalDiagram` records.
The observed selectors are declared in `schema/control_expert/graphical.py`.
Within each network, extraction retains object order, including repeated names:

- Blocks expose instance/type names, dimensions, explicit positions and ordered
  pins with interface direction, formal name, inversion and bound expression.
- Contacts expose their source contact type and operand. Their implicit grid
  positions and portable execution semantics are not inferred.
- Text boxes expose annotation text, dimensions and explicit positions.

Bindings remain expressions. An input and output named GEST in READ_VAR are two
separate pins; repeated expressions are not converted into direct block-to-block
edges. Missing expressions remain absent, not false, disconnected or an inferred
connection. Interface direction alone does not establish memory access effects.

Every diagram currently has `connectivity_resolved=False`. A supported FBD
network with exactly one block and no unknown objects, parsing diagnostics or
nonempty execution override has `execution_order_resolved=True`, with that
block's object index in `execution_order` and basis `single_block_network`.
This resolves only relative block order within that network, not execution
conditions, wiring or ordering across networks. Other cases remain unresolved.
Ladder HLink/VLink/grid data and unknown nodes/attributes remain in complete
source extensions. Block `execAfter` is also exposed as the uninterpreted
`execution_after` hint. Coordinates are source coordinates, not pixels; object
order is not execution order.
Unsupported objects and malformed fields produce location-bearing diagnostics.
FBD never populates executable `ladder_rungs`. LD now populates it for the
pure-series case only (contacts in series to one trailing coil, per grid row);
branch/link/block-gated rows remain unresolved. See "Ladder grid grammar and
pure-series rung resolution" below for the grammar and its limits.

The next graphical gate needs richer connection examples and a verified grammar
before inferring wiring or execution. Tests cover pin identity/direction,
unbound pins, duplicate object names, explicit versus implicit positions,
unknown wiring, and the real READ_VAR/MBP_MSTR object lists. Existing model JSON
and Structured Text regression tests also cover the optional routine field.

### Pin expression resolution

The neutral analysis in `analysis/graphical_bindings.py` uses the reader's
limited lexical profile from `schema/control_expert/expressions.py`. Simple
identifiers resolve case-insensitively to controller tags; ambiguous source
declarations cannot bind to the first retained tag. Pin `target_tag` references
the existing object rather than a copy. Exact expression text remains intact.

`binding_kind` distinguishes `declared_symbol`, `literal`, `unbound`,
`missing_symbol`, `ambiguous_symbol`, `unresolved_expression` and
`invalid_output_literal`. Recognized input literals include basic Boolean,
decimal integer/real, radix integer and simple quoted strings. Recognition is
lexical, not type or range validation. Complex expressions, array/member accesses,
typed literals outside the profile and direct addresses remain unresolved.
Absent and empty expressions are distinct. Output literals produce diagnostics.

`shared_variables` groups repeated declared-symbol references using object/pin
indices and source input/output directions. These groups neither establish
graphical wiring nor prove memory read/write effects or same-scan freshness.
The READ_VAR sample produces groups for `sendmsg`, `ipaddress`, and `manage`;
the latter retains distinct input/output GEST pins on one block. This analysis
never changes connectivity or execution-order resolution. Re-running it clears
stale derived bindings and groups. CLI JSON includes these groups and pin binding
details; text reports provide binding counts and shared symbol names.

### Task scans, pin direction and block ordering

These are separate facts. A successfully bound section records its task name,
mode and zero-based section index in each routine's `metadata["task_schedule"]`.
For cyclic tasks, eligibility is `each_active_task_cycle`; the task records
`cycle_policy="successive_cycles_while_active"`. This does not assert that a
section or block executes unconditionally: section conditions, control flow,
task activation and block enables are not evaluated by this importer.

Input/output pin directions are explicit in the XML. EN inputs carry the neutral
role `execution_enable`; ENO outputs carry `execution_status`. Other pins retain
the `data` role, including block-specific ENABLE pins. Unbound EN is not mapped
to a guessed constant or a guessed graphical link.

Schneider's [FBD execution-order FAQ, FA340273](https://www.se.com/us/en/faqs/FA340273/)
documents positional ordering and the effect of block input dependencies.
The Schneider [Program Languages and Structure manual, 35006144, 10/2019](https://device.report/m/10ca6353ab98599713059743a248545dc962e991370a3771a7bd1386822ce4a4)
adds the necessary qualifications: graphical links take precedence over user
ordering, followed by network and output sequencing (pp. 303–310). Cyclic task
cycles repeat while active (pp. 107–109). EN controls block execution, rather
than determining whether the containing task is cyclic.

Do not sort blocks solely by XML order or connect them because they share a
variable name. The current examples and available XML grammar do not establish
the complete link/override encoding. This limits multi-block order resolution,
not recognition of task scheduling or pin direction.

| Gate | Deliverable | Required evidence |
| --- | --- | --- |
| 0: inventory and specification | This document and local inventory | Five archives identified; all nested member hashes recorded; discrepancies retained |
| 1: lossless capture | Container reader and specification-driven XML capture | Original/member bytes recoverable with matching hashes; order and unknown content retained; failures diagnosed |
| 2: basic neutral mapping | Metadata, hardware, tasks, variables, section order and ST source | Counts and identities reconcile with inventory; unresolved types/addresses reported; no invented semantics |
| 3: graphical interpretation | Separate LD and FBD specifications and parsers | Connection, ordering and pin-binding tests against richer evidence; no unsupported execution-equivalence claim |
| 4: vendor validation | Schemas and access to an editor validation environment | Versioned XSD validation and successful import/build evidence; runtime equivalence requires separate tests |

Use independently authored minimal fixtures for portable automated tests;
reference-dependent checks should explicitly skip when local samples are absent.
Fixture expectations must exercise preservation, ordering, unknown data and
conflicting project identities, rather than merely repeat parser logic.
Do not add the downloaded archives to tracked test fixtures by default.

Remaining gaps: M580 exports, other DTD markers, custom
DDT and DFB definitions, populated DTMs, SFC mapping and broader SFC evidence,
IL/LL984, multiple task kinds,
protected/encrypted projects, authoritative grammar and native editor validation.
An XSD can constrain syntax; it does not establish runtime semantics.

## Additional SFC specimen: escalator project

Inspected user-supplied files on 2026-09-20 from the public
[PLC Escalator Control System repository](https://github.com/PsyGlo/PLC-Escalator-Control-System/tree/main/Logic_Source).
Original files and detailed inventories remain under ignored `reference/control-expert/`.

| File | SHA-256 |
| --- | --- |
| `Escalier_Mecanique.XEF` | `3e29eaf2702f2b35323bbe6b44528ec7cda4c2b9c9d20b1ca40f19394c77bae4` |
| `escalier_mecanique.zef` | `85e4385c51d4b0159c637e1ebc602bc9589064708a79a39832c7498cd22a28f4` |

Both exports identify Control Expert V15.0 - 201016B and DTDVersion 41.
The standalone root is `FEFExchangeFile`; the embedded root is `ZEFExchangeFile`.
The ZEF passes ZIP CRC checks and adds `props.xml` to the member names seen in
the earlier corpus. Export timestamps and full XML bytes differ; serializing
the two `SFCProgram` subtrees with ElementTree gives identical results in both
files. This comparison does not establish whole-project equivalence.

Observed SFC grammar, now described by the declarative SFC profile:

- `SFCProgram` is a root child separate from `program`. Its `identProgram`
  identifies `G_MEMO` and `G_MOTEUR`, MAST section orders 1 and 2.
- `chartSource/networkSFC` contains five steps (two initial), six transitions,
  ten actions with qualifiers `R`, `S` and `N`, one `altBranch`, and three
  explicit `linkSFC` elements across the two charts.
- Step actions identify variables through `actionName/variableName`; empty
  timing literals and step timing attributes must remain distinct from absence.
- Transition conditions contain either `variableName` or `sectionName` with
  an `invertLogic` attribute. Four named `transitionSource` children hold ST
  expressions. These are chart-local source definitions, not ordinary MAST sections.
- Explicit links identify endpoint object types and integer `objPosition`
  coordinates; their `gridObjPosition` routing coordinates include fractions.
  Preserve those lexical values. Three explicit links do not describe every
  apparent adjacent step/transition connection; grid adjacency remains unproven.

Current CLI inspection maps all six sections and resolves both SFC task
references. `Routine.sequential_charts` contains neutral ordered element trees,
lexical properties and chart-local transition definitions. Unknown nodes and
attributes retain source extensions. Duplicate transition definitions remain
separate; chart-local transition references bind only to a unique definition
using case-insensitive identity. Each reference carries `reference_status` and
`target_definition_index` into its chart's ordered `transition_definitions` list.
Missing/duplicate targets produce source-located diagnostics and no index.
Unnamed definitions are diagnosed and retained. Binding identifies a definition,
not the validity or execution of its body. Variable/member expressions remain
unbound by this resolver. JSON inspection exposes the chart
trees and text inspection reports step/transition counts. Connectivity and
execution remain explicitly unresolved. A chart's retained section extension
also preserves metadata outside the chart body. Successful mapping of this
observed subset does not establish general SFC support.
No native import, build, runtime or XSD validation has been performed.

## Additional SFC specimen: multi-Grafcet coordination

Inspected on 2026-09-20 from the user-supplied pair associated with
[Deterministic Multi-Grafcet Implementation](https://github.com/PsyGlo/Deterministic-Multi-Grafcet-Implementation).

| File | SHA-256 |
| --- | --- |
| `MultiGrafcet_Coordination_V1_2026.XEF` | `fcdf78239b9c3aa64903d19808c8e5f1fdb79b5a4ff2eb518cf5c0efbd950c4c` |
| `tsaii_multigrafcet_final_v1.zef` | `8083e6782ababf88d3ed716d3e0ab949dfada227227b6e51317206518209770b` |

Both identify Control Expert V15.0 - 201016B, DTDVersion 41. ZEF CRC checks
pass and its member names match the escalator ZEF. The serialized SFC subtrees
match between exports; whole-project equivalence is not established.

The current importer maps all eight sections and resolves their MAST references.
Three charts (`GMaitre`, `G1`, `G2`) contain ten steps, ten transitions, eleven
action entries and three explicit links. The remaining sections are one LD and
four ST bodies. New evidence includes:

- MAST is `periodic`, not cyclic. Its timing remains source evidence and produces
  the existing unresolved-task-semantics diagnostic.
- Transition variable expressions include `Tempo1.Q` through `Tempo6.Q`.
  The `variableName` XML label therefore does not guarantee a simple identifier.
- One action qualifier is `NONE`; retain it literally without equating it to `N`
  or dropping its associated variable. Other qualifiers are `N`, `R` and `S`.
- LD contains `INITCHART`, `SETSTEP` and six `TON` instances. ST calls
  `FREEZECHART(G2, NOT Run_G2)` and reads step-state expressions such as `G1_0.X`.
  Coordination depends on supporting sections as well as the chart structure.
- `G1_Voyants` explicitly assigns variables also named by chart actions. Preserve
  both writers; do not infer final values without verified execution semantics.

The repository README describes an M580 target, but both supplied exports identify
`TSXP572634M` (Premium). Record the discrepancy; these files do not establish M580
coverage. The author's simulator demonstrations are not TwinForge native/runtime
validation. Generated inspection reports and originals remain in ignored reference/.

## Additional SFC specimen: IUT-GEII-Annecy student coursework

Inspected on 2026-09-21 from the public
[automatisme-pour-robotique](https://github.com/IUT-GEII-Annecy/automatisme-pour-robotique)
repository, `fichiers_etudiants/allier/sfc/*.sfc.xml`. This is a third, independent
origin: a different author and context (French university robotics coursework)
from the two PsyGlo repositories above.

| File | SHA-256 |
| --- | --- |
| `IUT-GEII-Annecy_02_MAIN.sfc.xml` | `d4fe8a694bc93c9fbd4c2f5a8e7d7736ceb8ac103a4c1b87cb40defa5342f8b6` |
| `IUT-GEII-Annecy_01_A6_SFC.sfc.xml` | `38e15e6683ab7b512e4991c3e35bb9d2ec6470bb867dfcf15924eabdfd6292d9` |
| `IUT-GEII-Annecy_03_A1_POST.sfc.xml` | `9b3af36be4d2eb4ac08a96b0de23ba327bc99241b8f71a2b6a7e94cdbeaad43c` |

These are single-chart exports: the root is `SFCExchangeFile`, containing
`chartSource/networkSFC` directly, with no `fileHeader`, `identProgram`, `program`
or project-level content at all. That root is not one of `parse_project`'s
recognized roots, so these files cannot go through `capture_file`/`parse_projects`
as-is; they are kept as manual evidence, not as `pytest` "optional real reference"
fixtures. `01_A6_SFC.sfc.xml` and `03_A1_POST.sfc.xml` also contain non-XML binary
content after their initial well-formed prefix (observed, not explained — possibly
embedded compiled ST/DBGTable bytes in this export shape) and do not parse as
complete documents; treat only their clean leading fragment as evidence. `02_MAIN.sfc.xml`
is fully well-formed and is the specimen used below.

New evidence from `02_MAIN.sfc.xml`:

- The same linear grammar as the escalator and multi-Grafcet specimens: steps and
  transitions alternate by exactly one grid row (`posY`), same `posX`, within one
  network, with no gaps. Document order is not grid order — elements must be
  sorted by position before adjacency is read from them. This is now corroborated
  by three independently-authored sources with no counterexample.
- A previously unobserved element, `altJoint` (`width`, `relativePos`, same shape
  as `altBranch`): a convergence marker, symmetric to `altBranch`'s divergence.
  Not present in either PsyGlo specimen. `SFC_SPEC` does not yet map it; it falls
  through as `unknown`.
- An explicit `linkSFC` whose destination is `objectType="altJoint"` at grid
  position `(5, 8)`, while the `altJoint` element's own recorded `objPosition` is
  `(4, 8)` with `width="2"`. The branch/join spans multiple columns from its
  recorded position; a link may target any column in that span, not only the
  literal recorded position. The current endpoint resolver
  (`parsers/control_expert/sfc.py`, exact `position(obj) == coordinates` equality)
  cannot resolve this shape yet; `altBranch`/`altJoint` are also not in
  `endpoint_types` at all, so today this would be diagnosed `unsupported_type`,
  not `unresolved_sfc_link_endpoint` for a resolvable-but-unmatched position.
- One selective (OR) divergence/convergence structure is fully worked: from a
  single step, an `altBranch` (width 2) offers two transitions in parallel
  columns; each branch continues independently (one directly, one through a
  further step) and both paths reach the matching `altJoint` before rejoining a
  common step. This is the first concrete evidence of a complete divergence
  *and* convergence pair in one chart.

Non-primary, non-fixture lead: `apexsotjo-blip/control-expert-mcp`'s own
reference notes (`src/control_expert_mcp/lang_reference.py`,
`tools/lang_refs/SFC_0_Packaging_Robot.xml`) independently describe the same
alternation rule, and additionally describe `parBranch`/`parJoint` (simultaneous/AND
branching) and `jumpSFC` (a named jump to a step by `stepName`, bypassing grid
position entirely). That project's citations of specific Control Expert import
error codes (`E1228`, `E1189`) suggest hands-on verification against the real
GUI, but it remains one third party's own reverse-engineering, not vendor
documentation or a captured export, and no fixture in this corpus exercises
either construct. Recorded as a lead only; see the roadmap backlog item.

## Sources and next reference request

Source pages recommended for these samples:

- [CREAD_REG, FA250932](https://www.se.com/us/en/faqs/FA250932/)
- [CWRITE_REG, FA250277](https://www.se.com/nl/en/faqs/FA250277/)
- [MBP_MSTR function 15, FA246092](https://www.se.com/ie/en/faqs/FA246092/)
- [MBP_MSTR function 2, FA245323](https://www.se.com/in/en/faqs/FA245323/)
- [READ_VAR, FA271865](https://www.se.com/ae/en/faqs/FA271865/)

[Code generation for programmable logic controllers, Appendix B](https://www.diva-portal.org/smash/get/diva2%3A1449858/FULLTEXT01.pdf)
documents generating classes from installation-supplied `SrcXmlSchema` XSDs.
No authoritative DTD-version mapping or official standalone schema download was
located during the 2026-09-20 research. That is a search limitation, not proof
that neither exists.

Request from Schneider support: the XML exchange schema set, including
`FEFExchangeFile.xsd` and all dependencies, the associated software release,
and documentation of `fileHeader/@DTDVersion` and compatibility. Keep any
received schemas in `reference/control-expert/schemas/<software-version>/`
with provenance and hashes. No support request has been sent.

## Explicit SFC endpoint binding

The observed endpoint type profile admits `step` and `transition`. Each explicit
link must have exactly one source and destination. A unique object with the same
kind and exact lexical x/y position in the same network binds through
`target_element_path = [chart_element_index, network_child_index]`. Source and
destination `reference_status` values expose resolved, missing, ambiguous,
invalid-position or unsupported-type results; malformed role counts are diagnosed.
Paths index the preserved element lists, including unknown objects. Position
strings are not numerically normalized; equivalent-looking alternative spellings
remain unresolved until a coordinate grammar is established. Routing points are
preserved independently and are never used to identify endpoint objects.

All six explicit endpoints resolve in each local escalator and multi-Grafcet
export. This proves only recorded endpoint identity: adjacent grid objects,
branches and runtime flow are not inferred. `connectivity_resolved` and
`execution_resolved` remain false. Synthetic fixtures distinguish duplicate
positions, overlapping object types, missing targets, cross-network targets,
unsupported types, missing coordinates and malformed endpoint multiplicity.

## SFC simple variable binding

The vendor-neutral sequential binding analysis classifies variable references
under action targets and transition conditions using the declared lexical
identifier profile. Unique controller tags bind case-insensitively; duplicate
source declarations remain ambiguous even when the name-keyed model retains
only one tag. `binding_kind` distinguishes declared, missing and ambiguous
symbols from unresolved expressions. `target_symbol_name` records the canonical
name only on success. Original whitespace and expressions remain unchanged.
Source-located diagnostics describe unresolved bindings. Re-running analysis
clears stale bindings first.

Each escalator export binds twelve occurrences. Each multi-Grafcet export binds
fifteen and retains six timer-member expressions as unresolved. Qualifier `NONE`
is preserved while its named variable can still be identified; identification
does not imply that the action writes it. The analysis does not establish types,
read/write effects, action semantics or runtime behavior. ST bodies are not parsed
by this pass. Chart-local transition definition and explicit endpoint bindings
remain separate from variable binding.

## Library interface evidence and one-level member binding

The mapping profile now declares EF/EFB identity selectors and external parameter
paths. `ParsedProject.library_interfaces` retains ordered parameter names, types
and directions, with complete definition source extensions. Definitions remain a
list so duplicate identities cannot silently overwrite one another. CLI JSON
exposes these signatures; they are evidence, not executable implementations.

SFC binding accepts a single member selector when the base tag is unique, its
EFB interface is unique, and exactly one parameter matches the member name.
Names compare case-insensitively. `declared_member` records canonical base/member
names and the lexical member datatype. Ambiguous or absent interfaces/members
remain `unresolved_member`; arrays, deeper paths and step-state structures remain
outside this subset. No type compatibility, access-direction or execution claim
follows from member identity. Analysis resets derived member fields on reruns.

The multi-Grafcet exports declare six Tempo instances of TON; their embedded
interface declares Q as BOOL. All six `.Q` references now bind in each export.
This supersedes their earlier unresolved status in the inspection checkpoints.
Tests cover a unique signature and duplicate interface rejection alongside the
existing ambiguous tag, missing member evidence and lexical preservation cases.

## Graphical call signature matching

Graphical blocks now carry an interface status and an index into the parsed
project's ordered library interface list. A unique case-insensitive type identity
is required. Pin matching additionally requires name and source direction; matching
pins carry parameter indices. Duplicate definitions or parameters never choose
the first candidate. Derived fields reset on repeat analysis. CLI JSON exposes
these results alongside symbol bindings.

Unmatched data pins report `unresolved_convention`, not invalid calls: generic
and in-out representations require further evidence. Profile-classified EN/ENO
pins absent from the signature are marked `implicit_execution_pin`.
No missing-required-pin, datatype compatibility or executable validity claim is
made. Non-block graphical objects are excluded. Source-located diagnostics retain
unmatched calls and pins. Independent tests cover wrong direction, duplicates,
implicit pins, unsupported pins and stale result clearing.

Schneider's exported EF sources mark a repeatable parameter template with a
literal `(Extensible)` comment suffix, observed on `ADD`'s `IN1` alongside a
hidden `nin` count parameter (`function15`/`function2`). Numbered pins whose
name reduces to that template's base after stripping trailing digits (`IN2`,
`IN3`, ...) resolve to `matched_extensible` against the template's parameter
index, so their declared generic type still applies. This reuses only the
vendor's own extensibility marker, never a name-pattern guess applied to
parameters without that evidence; a base shared by more than one marked
template is reported `ambiguous` rather than guessed.

## Multi-block FBD execution order remains unresolved

Corrected 2026-09-21: shared `effectiveParameter` names establish symbol
references, not graphical wires, memory effects or a same-scan ordering rule.
The earlier `shared_variable_dataflow` inference has been withdrawn, including
for the ADDR/READ_VAR pair in `readvar.zip`. Even a unique topological ordering
of inferred dependencies would not verify the vendor's execution order.

Multi-block diagrams retain their shared-variable groups with empty
`execution_order`, false `execution_order_resolved` and no order basis until
independent link/layout/override evidence supports a rule. The analysis clears
legacy `shared_variable_dataflow` results on reruns, including excluded diagrams.
It retains the existing ambiguity diagnostic for a symbol occurring on output
pins of multiple blocks without asserting those pins' memory effects.
The independently supported single-block FBD case is preserved. A centralized
parser pass emits `unresolved_block_order` once per unresolved diagram.

Regression tests cover disconnected and partially constrained blocks, a shared
chain, stale result clearing, preservation of single-block evidence and JSON
inspection retaining shared symbols while reporting unresolved order.

## Ladder contact operand binding, including cross-section step state

LD contact operands (`GraphicalObject.operand`) previously carried no binding
classification at all, unlike FBD pins. Real corpus contacts prove two
distinct, evidenced shapes: plain declared-symbol references (`BPA`,
`Start_Timer`, ...; `Escalier_Mecanique`) and Control Expert's IEC 61131
step-active-state convention, `<step>.X`/`<step>.x` (`MultiGrafcet`'s `Init`
LD section reads `G1_0.X` .. `G2_2.X` and `E1.x`, each declared in a
*different* SFC chart section — `G1`, `G2`, `GMaitre` — not the LD section
itself). A raw system-bit reference such as `%S1` is not a declared project
symbol and is correctly left `unresolved_expression`, never guessed.

`resolve_graphical_bindings` now also classifies each contact's operand:
`declared_symbol`/`missing_symbol`/`ambiguous_symbol` reuse the same declared-
tag namespace as pins; `declared_step_state`/`missing_step_state`/
`ambiguous_step_state` match the `<name>.X` pattern against a project-wide
step-name registry built from every `SequentialElement` of kind `step` across
every chart in every routine — global, not chart-local, because the evidence
shows cross-section references and the local corpus has no duplicate step
name to contradict that scoping (a genuine duplicate is still reported
ambiguous, never resolved to either). `GraphicalObject` gained
`operand_binding_kind`, `target_tag` and `target_step_name`, exposed in CLI
JSON. No claim is made about the step's actual active/inactive value, memory
representation, or evaluation order — only that the reference names a unique
declared step. Independent unit tests cover both binding shapes, ambiguity
and rerun/reset; an integration test proves the cross-section (LD contact →
SFC chart in a different program) lookup end to end.

## Split graphical representation of in-out parameters

Observed in readvar.zip: READ_VAR declares GEST under
`ExternalToolsOnly/inOutParameters`, while its graphical call contains both
`inputVariable` and `outputVariable` named GEST, each bound to manage. The Control
Expert mapping profile explicitly allows an inout parameter to match either
source pin direction. The neutral matcher has no such alias by default.
Successful alias matches are reported as `matched_direction_alias` with the same
parameter index; the two pins, their directions and expressions remain separate.
Direct and aliased candidates are considered together, so conflicting declarations
remain ambiguous rather than preferring one. No storage alias, read/write effect,
missing-pin rule or generic datatype compatibility is inferred.

All four GEST pin occurrences across readvar.zip's two exports now match. No
`unresolved_convention` pins remain in the current local corpus. This is corpus
coverage, not general library validation. Tests cover profile opt-in, independent
expressions, conflicting declarations and resetting stale matches.

## Ladder grid grammar and pure-series rung resolution

Observed across `Escalier_Mecanique.XEF`/`.zef`, `function15.zip` and both
multi-Grafcet exports (all `LDSource nbColumns="11"`, one or more `networkLD`
children): a `networkLD` is a flat ordered sequence of `typeLine` elements
(one grid row each) and occasional top-level `textBox` annotations. Each
`typeLine`'s children are grid cells left to right:

- `emptyCell nbCells="N"` / `HLink nbCells="N"` -- blank span / wire span,
  consuming N columns, producing no object.
- `contact typeContact="openContact|closedContact|PContact" contactVariableName="..."`
  and `coil typeCoil="coil|resetCoil" coilVariableName="..."` -- exactly one
  column wide each; neither carries an `objPosition`, unlike `FFBBlock`/`textBox`.
- `shortCircuit` (wrapping a `VLink` plus a sibling `HLink` or `contact`) and
  bare `VLink` -- vertical wiring to the same column position in an adjacent
  row.
- `emptyLine nbRows="N"` -- only ever observed as a `typeLine`'s sole child;
  skips N rows without occupying one itself.

Row derivation: a `typeLine` whose sole child is `emptyLine` advances the row
counter by its `nbRows` and is not itself a row; every other `typeLine`
occupies exactly the current row, which then increments by one. This holds
regardless of a block's own `height` attribute -- `FFBBlock` height is a
rendering span, not a row-consumption count in this sequence. Verified against
every `FFBBlock`'s own `objPosition posY` in the corpus (e.g. `Escalier_
Mecanique.XEF`'s two `INITCHART` calls at rows 1 and 6, matching five
intervening `typeLine`s and an `emptyLine nbRows="2"`). Column derivation is
the cumulative cell width consumed left to right within one row, contacts and
coils counting as exactly one column each.

A row resolves as a pure series-AND rung -- built into `LadderRung`/
`LadderSeries`/`LadderInstruction` (`model/routine.py`, `model/ladder.py`;
already used by the L5X/CCW/PLCopen converters, never populated from Control
Expert until now) -- only when every child is `emptyCell`/`HLink`/`contact`/
`coil` and exactly one coil is present, as the last cell-bearing element.
`typeContact`/`typeCoil` values map to `LadderOperation` only for the
lexically-witnessed subset (`openContact`, `closedContact`, `coil`,
`resetCoil`); any other value (e.g. `PContact`, a positive-edge contact seen
gating `INITCHART`/`SETSTEP`) still resolves the instruction's position and
operand but carries `LadderOperation.UNSUPPORTED` plus a source-located
diagnostic, preserving evidence without asserting unwitnessed boolean
semantics. A row with contacts but no coil, or with a coil anywhere but the
final position (including more than one), is diagnosed and produces no rung.

Any row touching `shortCircuit`, `VLink`, `FFBBlock` or `textBox` is
diagnosed (`unresolved_ladder_row`) and never guessed at. Real evidence
contradicts the simplest hypothesis (a `shortCircuit`/`VLink` pair merging
two adjacent rows): `function15.zip` shows a single contact's `shortCircuit`
followed by four consecutive rows of a lone `VLink`, before reaching an
`FFBBlock` several rows below -- a vertical wire routed to a distant
destination, not a same-row branch merge. Attempting to resolve block EN/IN
pin wiring or general branch/join topology within Ladder from two examples
was deliberately not attempted; see the roadmap's Milestone 4 backlog item.

`coil` is now a mapped `GraphicalObject` kind (`schema/control_expert/
graphical.py`), alongside `contact`/`block`/`annotation`; every real coil in
the corpus previously fell through as `unclassified_graphical_object`.

## Coil operand binding, without the step-state convention

`resolve_graphical_bindings` now classifies coil operands the same way as
contact operands (`declared_symbol`/`missing_symbol`/`ambiguous_symbol`/
`unresolved_expression`, with their own `*_coil_*` diagnostic codes rather
than reusing the `*_contact_*` ones), with one deliberate exception: a coil
operand is never tested against the `<step>.X`/`.x` step-active-state
pattern, even when it lexically matches. A coil cannot legitimately write a
step's active-state bit -- that convention is read-only and owned by the SFC
engine -- so a coincidental lexical match falls through to plain symbol
resolution (or `unresolved_expression` if no declared tag matches) rather
than being misclassified as a step reference. All six real coils in the
escalator corpus resolve `declared_symbol` cleanly.

Validated against the local corpus: `Rising_Edge_Detection` (escalator)
resolves all four of its rows as pure series; `Init_Logic` resolves two
(an unconditional reset coil wired straight from the rail, and a plain
contact-to-coil rung) and diagnoses the rest (`INITCHART`-gating rows);
`TIMERS` resolves none. The multi-Grafcet LD section -- entirely
`INITCHART`/`SETSTEP`/`TON`-gated -- resolves zero rungs, as expected.

## Explicit FBD link evidence and resolution

New corpus: `estradege_m580-safety.xef` and `estradege_m340.xef` (MIT-licensed
test fixtures from [estradege/controlexpert](https://github.com/estradege/controlexpert),
a third-party C#/.NET Control Expert interop library; kept in
`reference/control-expert/`, SHA-256 `e807c0d1...399d62` and
`79502e04...38bc4f92`). The safety fixture is a real Control Expert V14.0
project (`fileHeader product="Control Expert V14.0 - 190112"`) with 32
`FBDSource` networks and 430 `linkFB` elements -- the first local evidence of
an explicit FBD wire at all; none of the previously-available fixtures
(`function15.zip`, `function2.zip`, `readvar.zip`, `cread_reg.zip`,
`cwrite_reg.zip`) contain one. That absence was checked deliberately before
attempting this work, since the natural alternative -- deriving order from a
shared parameter name between blocks -- was already withdrawn once as
unproven (see "Multi-block FBD execution order remains unresolved" above).

Observed grammar: a `linkFB` (a direct child of `networkFBD`, alongside
`FFBBlock`/`textBox`) has one `linkSource` and one `linkDestination`, each
carrying `parentObjectName` and `pinName` attributes plus its own `objPosition`
(a rendering waypoint only, confirmed by example: a link's endpoint position
routinely does not equal either connected block's own position) and an
optional `gridObjPosition` route point. Unlike SFC's `linkSFC`, resolution
here is **by name, not position**: `parentObjectName` matches a unique
`FFBBlock.instanceName` in the same network, and `pinName` matches that
block's unique pin with the endpoint's implied direction (`output` for a
`linkSource`, `input` for a `linkDestination`) -- a pin sharing the name but
the wrong direction is correctly left unmatched, not guessed. This removes
the coordinate-adjacency ambiguity that made SFC and Ladder resolution
harder; it is a direct identity lookup, the same shape as existing
library-call pin matching elsewhere in this parser.

`GraphicalDiagram.links: list[GraphicalLink]` now holds one `GraphicalLink`
per `linkFB`, each with an independently-resolved `source`/`destination`
`GraphicalLinkEndpoint` (`resolved`/`missing_object`/`ambiguous_object`/
`missing_pin`/`ambiguous_pin`, plus a `missing_pin` in cases of a real name
match on the wrong direction). Malformed endpoint counts (`!= 1` `linkSource`
or `linkDestination`) are diagnosed (`invalid_graphical_link_endpoint_count`)
and left at their default unresolved state, the same discipline as SFC's
explicit-link endpoint binding. All 371 `linkFB` occurrences in the safety
fixture resolve cleanly on both ends; `unclassified_graphical_object`, which
every one of them produced before this change (371 of the fixture's total),
no longer appears at all for that project.

**This is connectivity, not an execution-order claim.** Resolving a link
proves the vendor declared a wire between two specific pins; it does not by
itself establish that the source block executes before the destination in
the same scan, or that any value is fresh when read. `execution_order`,
`execution_order_resolved` and `execution_order_basis` are untouched by this
work and remain exactly as before (only the single-block case is resolved).
Deriving execution order from `linkFB` -- which does look like considerably
stronger evidence than the withdrawn shared-parameter-name inference -- is a
deliberately separate next step, not attempted here; it needs its own
sign-off on what "the vendor declared a wire from A to B" is allowed to imply
about scan timing, matching how SFC connectivity and SFC execution were also
kept as two separate, independently-gated claims.

## Power supplies are not slot-addressed hardware

The M580 safety fixture's rack (see above) carries a `powerSupply` element
(`BMXCPS4002S`) alongside its `moduleATS` children -- a vendor tag the mapping
profile already distinguished lexically (`HardwareLayout.modules` previously
listed both `"moduleATS"` and `"powerSupply"` together) but processed
identically to a numbered-slot module. Its `equipInfo` carries
`position="-1"` and a `topoAddress` ending `.(P) (P)`; `str.isdecimal()`
rejects the leading `-`, so it fell to `unplaced_hardware`. The same shape
was already present, unnoticed, in the original `readvar.zip` fixture.

Domain input (not derivable from the XML alone): a power supply mounts in
its own dedicated position, physically separate from a rack's numbered
slot scheme -- it is not "a module at an unusual slot," it is a different
kind of thing. Widening the position parser to accept negative integers
would have mechanically "fixed" this by giving it slot `-1`, but that
misrepresents the hardware and would have silently changed two existing
fixtures' resolved slot layout. `Chassis.power_supplies: list[Module]`
(populated via `add_power_supply()`, no slot involved) now holds it instead,
fully resolved and reported as neither a numbered module nor unplaced
hardware; `HardwareLayout.power_supply_modules` carries the tag(s), evidenced
per layout -- `("powerSupply",)` for the Schneider ATS layout only. The
Quantum layout has no observed power-supply tag and keeps its default `()`.

This does not generalize across manufacturers or even across Schneider rack
families: some mount power supplies in-chassis, some do not, and nothing
here asserts a rule beyond the one vendor tag shape actually evidenced. A
power supply with no resolvable identity still reports `unplaced_hardware`,
unchanged from before.

## DDT (derived type) grammar and capture

`DDTSource` is a root-level sibling of `program`/`dataBlock` (not nested
under either), one per derived type: `<DDTSource DDTName="..." version="..."
dateTime="...">`, with a `<comment>`, zero or more `<attribute name="..."
value="...">` (vendor metadata -- `TypeSignatureCheckSumString`,
`IsTypeLocked`, `IsTypeHiddenButExported`, ... -- retained in source
evidence, not interpreted or mapped to any model field) and one `<structure>`
containing its members, each a `<variables name="..." typeName="...">` --
the identical element already used for top-level `dataBlock` variables and
library parameters, reused here for DDT members, each with its own
`<comment>` and `<attribute>` children (per-member ones observed:
`RequestAccessRight`, `InstancesProgramAccessRight` -- access-right codes
with no confirmed semantics, likewise retained unmapped).

13 real DDTs, from the M580 safety fixture (see above), map cleanly to the
pre-existing, previously entirely-unpopulated `Datatype`/`DatatypeMember`
model. Two are Schneider's own standard module-health types
(`T_BMENOC0321`, `T_BMEP58_ECPU_EXT`), not user-authored, so they are
representative, safe reference material rather than one customer's private
design. 18 real members use the inline array form already evidenced for
top-level tags, `ARRAY[lower..upper] OF <type>` (e.g. `ARRAY[257..384] OF
BOOL`) -- the same regex already relied on for tag arrays matches every one
unchanged. One member (`T_BMENOC0321.DID_HEALTH`) has a `typeName` that is
itself another DDT's name (`T_NOCDIO_HEALTH`) -- the corpus's only observed
composite/nested-type reference, and it is declared *before* the DDT it
references, proving the resolver must not assume declaration order.

Two-pass resolution: every `Datatype` is created first (so every name is
known), then every `DatatypeMember` in a second pass, so a member's
`typeName` can forward- or backward-reference any DDT regardless of source
order. A member resolves when its `typeName` is either a known scalar
(`spec.scalar_types`) or a known DDT name (case-insensitively, matching the
declared-symbol lookup convention used everywhere else in this parser);
`DatatypeMember.data_type` is set only in the DDT case, so a consumer can
tell "the base type is a captured composite type" from "the base type is a
scalar" without inspecting the raw string. Neither case is set for an array
member's own element type slot beyond what the array-bounds regex already
extracts -- array-of-DDT has no corpus evidence and is not attempted.

Array bounds land in `DatatypeMember.dimension` as the unmodified lexical
`"lower..upper"` text (e.g. `"257..384"`, not `"0..127"` or a bare count) --
the milestone's "without zero-base loss" is met by simply not normalizing at
all, the same discipline `_variables`'s existing tag-array handling already
uses for its own `source_array_bounds` metadata, extended here to a field
built for exactly this purpose. `unresolved_array_type` still fires whenever
an array pattern matches (the array *type itself* -- as opposed to its
element type identity -- remains uninterpreted, unchanged from the tag case);
`invalid_array_bounds` fires when the upper bound precedes the lower.

A second, smaller finding from the same corpus: of its members, `BYTE`,
`UINT`, `REAL` and `UDINT` accounted for the bulk of `unresolved_type`
diagnostics before this pass -- genuine, unambiguous IEC elementary types
simply absent from `spec.scalar_types` (which previously covered only
`BOOL`, `INT`, `DINT`, `WORD`, `TIME`, `STRING`). Added those four plus
`DWORD` and `EBOOL` (Schneider's own extended-BOOL elementary type, adding
rising/falling-edge and forcing semantics, still a scalar value type).
Deliberately not added: IEC generic placeholder types observed in the same
corpus (`ANY`, `ANY_NUM`, `ANY_BIT`, `ANY_ELEMENTARY`, ...) and the dozens of
FB/EFB instance type names also present as `typeName` values elsewhere in
the same project (`TON`, `SFC_TRAN`, `S_SR`, `R_TRIG`, ...) -- neither
represents a concrete scalar value type, and conflating either with DDT
member typing would be a real, not merely cosmetic, category error.

Top-level tags benefit from the same registry: `_variables` now treats a
`typeName` matching a known DDT name as resolved, not only the scalar set,
so a tag legitimately typed with a captured DDT is not left permanently
`unresolved_type` once that DDT exists. The M580 safety fixture's
`dataBlock` happens to be empty (no top-level tags at all in that project),
so this specific extension has no real-corpus example yet; it is a direct,
low-risk consequence of the DDT registry now existing; not a speculative
addition.

Out of scope, not attempted: device DDTs are a structurally distinct
mechanism from `DDTSource` and are not captured by this work despite sharing
the "DDT" name in the milestone wording (custom DFB/`FBSource` definitions
*are* now captured -- see below); composite/array *initialization* values
(as opposed to the bounds captured here) remain unresolved lexical evidence,
matching how scalar initial values are already handled for plain tags.

## DFB (user-defined Function Block) grammar and capture

`FBSource` is a root-level sibling of `program`/`DDTSource` (not nested
under either), one per user-defined Function Block: `<FBSource
nameOfFBType="..." version="..." dateTime="...">`, with `<comment>`,
`<attribute>` metadata (`TypeCodeCheckSumString`, `TypeSignatureCheckSumString`,
retained unmapped, same discipline as `DDTSource`'s own attributes), an
interface and a body.

Interface shape: `inputParameters`/`outputParameters`/`inOutParameters` and
`publicLocalVariables`/`privateLocalVariables`, each containing `variables`
elements -- the identical element reused for `DDTSource` members and
`dataBlock` tags. Location varies by body state, observed as mutually
exclusive across all 83 real definitions: a **direct** child of `FBSource`
for the 76 with a real body, or nested under `ExternalToolsOnly` for the 7
with a `crypted` one -- the same wrapper `EFBSource`/`EFSource` already use
for their own (always-nested, never-direct in the observed evidence)
interface declarations, apparently Control Expert's way of exposing an
interface to external tools even when the implementation is inaccessible.
Reused the existing `library_parameters` path list unchanged rather than
adding a parallel lookup: it already tries the `ExternalToolsOnly`-nested
paths, so three more entries for the direct paths cover both locations with
one mechanism.

Body shape: `FBProgram` wraps exactly one of the four recognized language
sources (observed: `STSource` 65 times, `FBDSource` 10; no `LDSource` or
`chartSource` body in this corpus, though nothing in the grammar rules them
out) -- parsed with the identical machinery a top-level program's body
already uses (`parse_diagrams`, ST line-splitting), producing an ordinary
`Routine` attached to the DFB's own `AddOnInstruction.routines`. A `crypted`
element (hex-encoded, `Encoding` attribute, no children -- genuinely opaque,
not attempted) replaces `FBProgram` entirely for those 7; one definition
(`IO_AI_EX`) has *two* `FBProgram` elements, diagnosed
(`ambiguous_function_block_body`) rather than arbitrarily picking one.

Model choice: `FBSource` maps to the existing `AddOnInstruction`/
`AddOnInstructionParameter` model (`Controller.add_on_instructions`,
previously populated only by the L5X/Rockwell AOI parser, unpopulated for
Control Expert until now) rather than a new Control-Expert-specific type. A
DFB and a Rockwell AOI are the same concept -- a reusable instruction with a
parameter interface, local tags and an implementation body -- and the
existing model already separates external parameters from local tags
exactly the way this evidence needs. `AddOnInstructionParameter`'s
pre-existing `data_type_definition: Datatype | None` field (mirroring
`DatatypeMember.data_type`) resolves against the same DDT registry the
`DDTSource` pass already builds; the same registry closed a small
completion gap in that earlier pass -- `Tag.data_type_definition` was never
actually being set for top-level tags, only the diagnostic was suppressed.

Each `FBSource` is also registered as a `user_function_block` entry in
`library_interfaces` (alongside the pre-existing `EFBSource`=`function_block`
and `EFSource`=`function` entries), using its own already-collected
parameter list. This costs nothing new structurally -- `match_library_calls`
has no kind-specific logic, `kind` is purely descriptive -- but it closes a
real, previously invisible gap: 260 real `FFBBlock` instances in this
project's own top-level programs call a project-defined FB, and previously
had no interface to validate against at all.

Deliberately not attempted: binding pins/symbols *inside* a DFB body. An
FB body's parameters and locals are their own namespace -- an `IN` pin
inside a DFB body means "this DFB's own IN parameter," not a project-global
tag named IN -- but `resolve_graphical_bindings` and
`resolve_sequential_bindings` both assume one flat, project-wide symbol
table. Wiring DFB routines into those passes unchanged would produce
plausible-looking but *wrong* bindings for any DFB whose parameter or local
name happens to collide with an unrelated global tag, not merely incomplete
ones -- a materially worse failure mode than leaving them unresolved. Left
as a separate, explicitly scoped next step, not a small extension of the
existing passes.

## FB-local pin binding: an isolated namespace per DFB

The deferred step above is now implemented, not with a new pass bolted onto
the existing one, but by giving `resolve_graphical_bindings` a shared core.
Its per-diagram resolution logic (contact/coil operand classification, pin
classification, shared-variable grouping) moved into a private
`_resolve_diagrams` helper parameterized on the symbol table and scope name;
`resolve_graphical_bindings` itself is behaviorally unchanged (still builds
one project-global table from `controller.tags`), and a new
`resolve_function_block_bindings` calls the same helper once per
`AddOnInstruction`, each time with a table built from *only* that FB's own
`parameters` and `local_tags` -- never the project's tags, never another
FB's declarations.

This is IEC 61131-3 encapsulation, confirmed directly rather than assumed: a
pin inside a DFB body referencing a name that exists as a *project-global*
tag, but not as that DFB's own parameter or local, resolves `missing_symbol`
-- the global tag is not used as a fallback. Two DFBs each declaring a
parameter named `IN` resolve two separate pins to two separate parameter
objects; no cross-FB leakage. A parameter and a local tag sharing a name
*within one* DFB (structurally possible -- `_function_blocks` checks
parameter-name and local-name uniqueness with separate `used` sets, so nothing
already prevented this at capture time) is correctly diagnosed
`ambiguous_pin_symbol`, not resolved to either.

Scope is smaller than "every DFB body": only FBD bodies carry parsed pins at
all (`STSource` bodies are retained as plain text, never parsed into
expression structure), so this binds pins in 10 of the 83 real M580 safety
DFBs. Real results there: `M_DWORD_TO_BIT`'s inner `WORD_TO_BIT.BIT16` pin
resolves to the *outer* DFB's own `BIT16` output parameter -- exactly the
kind of same-named-across-nesting-levels case that would have silently
mis-resolved against a shared global table. Complex expressions genuinely
present in this corpus (`GEST[1].0`, `Communication = 16#00`,
`UDINT_TO_TIME(1000 * HoldupTime)`) stay `unresolved_expression`, the same
conservative classification already used for top-level program pins with
equally complex expressions -- this work changes *which symbol table* a
simple identifier resolves against, not what counts as "simple."

Model change: `GraphicalPin` gained `target_parameter:
AddOnInstructionParameter | None`, set instead of (never alongside)
`target_tag` for an FB-scoped resolution. A resolved `AddOnInstructionParameter`
is not a `Tag` -- `GraphicalPin.target_tag` is typed `Tag | None`, so
assigning a parameter there would have been a real type error, not a
convenient reuse. `GraphicalBindingIssue` gained `scope: str = "program"`
(`"function_block"` for the new path) so the diagnostic-wiring code in
`parse_project` can select `controller.add_on_instructions` instead of
`controller.programs` when resolving an issue's source location, without
guessing from the name alone. CLI JSON exposure was likewise unified: the
per-diagram object/pin serialization (previously inline, only reachable from
`programs[].routines[].diagrams`) became a shared `_diagram_summary`
function, so `function_blocks[].body[].diagrams` now carries the same full
detail -- including `target_parameter` -- instead of the summary-only shape
it briefly had.

## Multi-block FBD execution order: a documented vendor rule, generalized

`schema/control_expert/graphical.py`'s `execution_rule_source` has cited
[Schneider FAQ FA340273](https://www.se.com/us/en/faqs/FA340273/) since the
single-block case was implemented, but nothing consumed it until now. Its
own words: FFBs with no other FFB as input execute first, top to bottom by
grid position; FFBs that do have one execute after, also top to bottom --
dependency overrides position when the two conflict, demonstrated by the
FAQ's own example, "FFB 13 will be executed before the 11 that is above."
That example is exactly two levels deep.

Real corpus evidence: 28 real diagrams (across both top-level programs and
DFB bodies) have at least one `linkFB`-evidenced dependency; the deepest
chain runs 7 levels (`Sim_W505`, 80 blocks), and none are cyclic. At that
depth the FAQ's literal two-bucket wording is insufficient -- every block
past the first level shares the same "has input" bucket, ordered only by
position, which would misorder a block that depends on another block also
in that bucket if position happened to place them the wrong way round. A
full topological sort -- Kahn's algorithm, releasing each wave of
position-sorted blocks whose dependencies are now satisfied -- is the
mathematically necessary generalization, and it collapses to exactly the
documented rule for a 2-level graph. Implemented as
`execution_order_basis = "documented_dependency_order"`, distinct from
`"single_block_network"`, and explicit in its own module docstring that the
N-level case is a generalization, not a separately vendor-confirmed rule --
the same honesty this project already applied once to the FBD block-order
question, when the shared-variable-name inference was withdrawn for
resting on less than it claimed.

The dependency graph is built only from resolved `linkFB` connections.
Deliberately excluded from evidence: `shared_variables` groups, which this
project already proved are not reliably wires. A group's output pin and
input pin on two different blocks, *not* also covered by a resolved link,
disqualifies the whole diagram -- checked directly against the corpus, not
theoretically: `IO_READVAR`, `PC_T_GEN` and `P_MUX3` (all DFB bodies) have
exactly this shape. An unresolved link, a dependency cycle (new diagnostic
`cyclic_block_dependency`; none observed), or any block lacking a grid
position also disqualifies resolution, never guessed past.

One further finding changed the implementation mid-pass: the pre-existing
gate that skipped a whole diagram whenever any pin anywhere had an
unresolved symbol binding made the new sort resolve zero of the 22 real FBD
diagrams -- every one has at least one such pin somewhere in a large enough
network. That gate predates real order resolution and has no bearing on
whether an explicit `linkFB` wire is trustworthy; loosened for order
resolution specifically (kept in front of the separate `ambiguous_block_order`
shared-variable-write check, where a clean-pins diagram is still the
relevant precondition). All 22 real FBD diagrams now resolve; every
resolved order was checked programmatically to respect every real link
dependency.

## Execution order for DFB bodies, and a diagnostic-noise fix

The follow-up flagged above is done: `resolve_fbd_execution_order` now
covers `controller.add_on_instructions` too, via the same
`_resolve_routine_diagrams` helper used for `controller.programs` -- order
resolution is purely diagram-local (blocks, links, grid positions), so
extending coverage was a scope change only, never a semantics one, unlike
FB-local pin binding.

This gave the unlinked-shared-variable disqualification guard its first
real exercise (previously only synthetically tested): of 10 real
FBD-bodied DFBs, exactly the 3 already identified as having unlinked
shared-variable dataflow (`IO_READVAR`, `PC_T_GEN`, `P_MUX3`) stay
unresolved; the other 7, including one single-block DFB, resolve.

Extending the final catch-all diagnostic loop to cover DFB routines
required checking `diagram.language` there for the first time, which
surfaced that it had been reporting `unresolved_block_order` for every LD
diagram unconditionally -- `execution_order_resolved` never becomes `True`
for LD by any mechanism, so this was noise, not evidence, present since the
diagnostic was first introduced. Filtered out for LD; no existing test
relied on the old count, and a new one locks in the fix.

## `shortCircuit`/`VLink` vertical wires: not vendor SCE, but evidenced anyway

Schneider's own Machine Expert documentation ("Parallel Branch",
product-help.se.com, part number EIO0000002854.00) names the double
vertical line in a Ladder rung "Short Circuit Evaluation" (SCE): a
conditional bypass for a function block with a boolean input/output --
when a parallel branch made only of contacts evaluates true, the gated
block is skipped and its input value passes straight through to its
output; when false, the block runs normally. That is a real, documented
mechanism, but it is not what the `shortCircuit` element represents in
every project in this corpus. No fixture here shows the doc's specific
shape (one parallel branch with a block, another with only contacts,
merging to a shared point). Every real `shortCircuit` instead feeds one
target pin directly, confirmed by recomputing grid columns/rows by hand
and matching them exactly against the target `FFBBlock`'s own
`objPosition`. `resolve_ladder_pin_conditions` (`ladder.py`) resolves this
narrower, actually-evidenced case, and deliberately stops short of
synthesizing the vendor's bypass-and-passthrough execution semantics,
which nothing in the corpus proves applies here.

Column/row arithmetic, worked out against `Escalier_Mecanique.XEF` and
`function15.zip`/`function2.zip` (the same `mbp_mstr15`/`mbp_mstrf2`
projects behind the FBD execution-order evidence) and cross-checked
against every real `objPosition`:

- `emptyCell`/`HLink` consume their `nbCells`; a bare `contact`, `coil` or
  `VLink` consumes exactly one column, matching the existing pure-series
  convention.
- `shortCircuit` wraps exactly one `VLink` plus one sibling (`contact` or
  `HLink`). Its own column-width equals that sibling's width, and its
  vertical "tie" column is the *last* column of that span, not the first
  -- confirmed because every subsequent bare `VLink` continuing the same
  wire lands on that end column, never the start column.
- A wire's condition is whichever `contact`s appear in its origin row
  before reaching the `shortCircuit` (as ordinary series siblings, or
  nested inside the `shortCircuit` itself, or both) -- zero, for a
  `shortCircuit` wrapping a plain `HLink`, means the wire is unconditional.
- The wire continues through following rows wherever a bare `VLink` sits
  in the *same* column. It does not survive a blank/skipped span
  (`emptyLine`): nothing is drawn there to carry it, and no fixture shows
  otherwise.
- It lands, unambiguously, on `EN` -- never any other pin -- when it
  reaches a row that is exactly an `FFBBlock`'s own `objPosition posY`,
  that block has `enEnO="true"` with `EN` listed first in its
  `descriptionFFB` (always true for such a block), and nothing but empty
  cells lies between the wire's column and the block's `posX`. `EN` is
  the only pin ever evidenced as a target; no fixture shows a second input
  row being fed this way.
- A landing is confirmed only if the same column carries *no* marker one
  row past the landing row. Real evidence needed this refinement twice:
  `resetnoe`'s `.3`/RESET looks like a clean landing at row 20, but the
  same wire genuinely continues (through two more real, undrawn-nothing
  rows) to `.4`/SET at row 23 -- confirming the landing at row 20 would
  have been wrong. Conversely, `MBP_MSTR_7` (a 7-row `MBP_MSTR` block with
  three wireable inputs, `EN`/`ENABLE`/`ABORT`) shows a wire landing
  cleanly on its anchor row, then keeping a `VLink` alive at the same
  column for exactly one further row before dangling. Whether that means
  the wire also feeds `ENABLE`, or is merely the block's own border
  rendered with the same element, is not decidable from the grid alone --
  left unresolved rather than guessed.

Confirmed across the full corpus: 4 resolved `EN` conditions each in
`function15.zip`/`function2.zip` (`.2`/SET ← `abortnoe`,
`.4`/ADD ← `timedoutnoe`, `.5`/ADD ← `resetnoe`,
`.4`/SET ← unconditional), zero elsewhere -- both of
`Escalier_Mecanique.XEF`'s two `shortCircuit` occurrences dangle (no
`FFBBlock` reached at all), and no other fixture in the corpus contains a
`shortCircuit` element.
