# IEC 61499 and Eclipse 4diac roadmap

This roadmap evaluates IEC 61499 as a distinct TwinForge target using Eclipse
4diac IDE and the 4diac FORTE runtime. It does not imply that Allen-Bradley
ControlLogix or CompactLogix controllers can execute IEC 61499 applications.

The initial architecture keeps Rockwell controllers and EtherNet/IP adapters
as external devices. FORTE runs on Windows, Linux, an edge computer, or another
supported target.

## Objective

Establish whether TwinForge can generate evidence-preserving IEC 61499 system,
application, function-block, device, resource, and mapping artifacts from its
vendor-neutral model.

The work must preserve the distinction between:

- translating data and interfaces;
- translating control behavior;
- mapping function blocks to distributed resources; and
- communicating with an existing Allen-Bradley controller or adapter.

## Phase 0: native localhost evidence

- [ ] Install or unpack Eclipse 4diac IDE
- [ ] Build or obtain a compatible Windows FORTE runtime
- [ ] Run FORTE locally without elevated privileges
- [ ] Create a minimal IEC 61499 system and application in 4diac IDE
- [ ] Add one `FORTE_PC` device with one embedded resource
- [ ] Map a small Boolean function-block network to the resource
- [ ] Deploy it to localhost and observe it online
- [ ] Export or copy the complete native 4diac project into the ignored
  reference area
- [ ] Record IDE, FORTE, project-format, deployment-profile, and port versions
- [ ] Add a legally shareable minimal derived fixture when redistribution and
  provenance are clear

Completion criterion: a native project created by 4diac IDE deploys to a local
FORTE runtime and its observable Boolean behavior is recorded.

## Phase 1: native format and semantic capture

- [ ] Parse the native 4diac system and type files losslessly
- [ ] Preserve unknown XML attributes and elements as source evidence
- [ ] Identify application, subapplication, device, resource, segment, and
  mapping identifiers
- [ ] Capture event inputs, event outputs, data inputs, data outputs, and
  event-data associations separately
- [ ] Capture Basic FB execution-control charts, algorithms, and transitions
- [ ] Capture Composite FB networks and Service Interface FB declarations
- [ ] Determine stable versus editor-generated identifiers
- [ ] Document native validation and package/library metadata

Completion criterion: TwinForge can inspect a native fixture without losing
unrecognized source content.

## Phase 2: vendor-neutral IEC 61499 target model

- [ ] Define target contracts for systems, applications, devices, resources,
  mappings, FB types, instances, events, data ports, and connections
- [ ] Keep target contracts outside the vendor-neutral controller core
- [ ] Define deterministic identities and serialization order
- [ ] Represent event scheduling explicitly rather than treating it as a
  graphical restatement of ladder execution
- [ ] Preserve unsupported Logix behavior with diagnostics
- [ ] Add a target capability and conversion-readiness report

Completion criterion: the target model can represent the native smoke fixture
and reject incomplete event/data semantics.

## Phase 3: first TwinForge-generated application

- [ ] Generate the minimal native project from the target model
- [ ] Load it in 4diac IDE without manual XML repair
- [ ] Deploy it to localhost FORTE
- [ ] Compare observed behavior with the native fixture
- [ ] Add deterministic serialization and round-trip regression tests
- [ ] Keep project loading, deployment, and runtime execution as separate
  validation results

Completion criterion: a TwinForge-generated Boolean application executes in
FORTE with the same observations as the native baseline.

## Phase 4: Rockwell integration boundary

- [ ] Represent an Allen-Bradley controller as an external IEC 61499 system
  device rather than a FORTE execution target
- [ ] Derive interface candidates from L5X produced/consumed tags, MESSAGE
  configuration, module addresses, and external-reference evidence
- [ ] Derive EtherNet/IP Assembly candidates from EDS path evidence
- [ ] Define an EtherNet/IP Service Interface FB contract
- [ ] Select or implement an authorized, read-only EtherNet/IP transport for
  the FORTE target
- [ ] Separate structural discovery, cyclic I/O, explicit messaging, and
  runtime tag-value access
- [ ] Validate communication first with a simulator or personally controlled
  device

Completion criterion: an IEC 61499 application exchanges a small, explicitly
defined data set with an authorized external EtherNet/IP endpoint without
claiming native Logix execution.

## Phase 5: selective control-logic conversion

- [ ] Define the relationship between Logix scan semantics and IEC 61499 event
  scheduling
- [ ] Start with a small stateless Boolean routine
- [ ] Add stateful timers, counters, one-shots, and AOIs only after their event
  behavior is defined and tested
- [ ] Map eligible AOIs to Basic or Composite FB types without name-specific
  conversion rules
- [ ] Preserve lifecycle, task period, priority, and execution-order evidence
- [ ] Report unsupported motion, safety, redundancy, and vendor services

Completion criterion: every converted behavior has executable equivalence tests
and an explicit scheduling model. Graphical similarity alone is insufficient.

## Deliberate exclusions

- Running FORTE inside an Allen-Bradley Logix controller
- Treating PLCopen XML as IEC 61499 exchange data
- Assuming IEC 61131 function blocks have IEC 61499 event semantics
- Generating EtherNet/IP writes or cyclic control connections without an
  explicit authorized device profile
- Claiming universal Logix conversion from one successful fixture
- Automatically resolving or downloading untrusted external type references

## Suggested first reference location

Keep native editor and runtime evidence under the ignored directory:

```text
reference/IEC61499/4diac/native-localhost/
```

Record a directory listing, application/system files, exported FB types,
screenshots when useful, and a short text file containing the 4diac IDE and
FORTE versions. Do not commit third-party binaries or documentation unless their
redistribution terms explicitly allow it.
