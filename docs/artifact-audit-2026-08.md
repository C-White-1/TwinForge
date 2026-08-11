# Tracked Artifact Audit — August 2026

This audit reviews tracked files under `examples/` and `reports/` against the
[artifact policy](artifact-policy.md). It is an inventory and classification
checkpoint, not a deletion or relocation change.

## Scope and method

The audit used the Git index as the source of truth on 12 August 2026. It
counted tracked paths, grouped file types and top-level categories, checked for
ignored files that remain tracked, searched for build/cache path segments, and
identified individual files larger than 500 KB.

No content was removed, renamed, regenerated, or reformatted during the audit.

## Inventory summary

| Category | Tracked files |
| --- | ---: |
| `examples/` | 181 |
| `reports/` | 67 |
| Total | 248 |

The most common extensions are:

| Extension | Count |
| --- | ---: |
| `.json` | 78 |
| `.py` | 46 |
| `.md` | 43 |
| `.ld` | 24 |
| `.txt` | 21 |
| `.export` | 12 |
| `.xml` | 9 |
| `.st` | 8 |

The remaining files are three PlantUML sources and one each of AutomationML,
CSV, PowerShell, and SNMP recording formats.

## Policy checks

- No tracked path under the audit scope is also matched by the current
  repository ignore rules.
- No tracked path contains a build, distribution, dependency, bytecode, or
  pytest-temporary directory segment.
- The tracked examples include executable Python demonstrations, strict JSON
  configuration examples, native-tool evidence, generated comparison output,
  and runtime-tested OpenPLC projects.
- The tracked reports contain three curated evidence collections:
  `Dev_PF525_Program`, `Dev_USB_Program`, and `Str_Capacity_AOI`.

These checks find no accidental cache or compiler-output inclusion. They do not
establish provenance, redistribution permission, or continued necessity for
every tracked file.

## Example classifications

### Python and configuration examples

The Python files are catalogued in [the example guide](examples.md) as thin CLI
wrappers or focused API demonstrations. JSON configuration examples exercise
strict user-facing target and discovery configuration. Their current location
matches the artifact policy.

`examples/build_twin.py` remains a deferred live-discovery sketch rather than
an obsolete file. Its exclusion from maintained type checking is documented;
it should not be presented as a supported discovery command.

### CODESYS native evidence

The 12 `.export` files record visualization differential evidence, EtherNet/IP
diagnostic integration, consolidated PowerFlex applications, and the two-drive
device template. Several are cited by experiment or architecture documents and
some support regression evidence.

Four CODESYS exports exceed 500 KB:

- `33_sys_module_enip_diagnostics.export` — 966,059 bytes;
- `44_powerflex525_consolidated_project.export` — 979,408 bytes;
- `45_powerflex525_two_drive_project.export` — 1,607,077 bytes; and
- `46_powerflex525_two_drive_device_template.export` — 1,511,435 bytes.

They are retained by this audit because they capture native compatibility that
cannot be reconstructed safely from filenames alone. A later provenance review
should confirm tool version, authorship, regeneration procedure, and whether a
smaller semantic fixture can preserve each requirement.

### OpenPLC projects

`examples/OpenPLC/` contains 106 tracked files. Directory names currently
distinguish generated, reference, and simulation variants, and the native
compatibility document records the editor, compiler, and runtime evidence.

These projects are legitimate regression and runtime evidence, but the tree
does not yet have one local manifest classifying every project as authored
reference, TwinForge-generated baseline, or simulation stimulus. The files are
retained pending that manifest.

### PLCopen XML and AutomationML

The tracked PLCopen XML and AutomationML documents are generated examples and
compatibility baselines. `BoosterCompressor_codesys.xml` is 763,552 bytes and
is the fifth file above 500 KB.

These files should remain distinguishable from independently authored native
exports and from ignored official schemas. Their regeneration command and
source fixture should be recorded in a local manifest before any future
cleanup decision.

### SNMPSim

The SNMPSim example tree includes a README, local loopback utilities, corpus
configuration, and a synthetic `.snmprec` fixture. It already has the clearest
local provenance and operating guidance of the reviewed example subtrees.

## Report classifications

The PowerFlex report collection is extensively cited from device-reference,
visualization, and architecture documents. Two report files are also consumed
as checked regression evidence. The USB and `Str_Capacity` collections preserve
earlier AOI parsing and portability analysis.

The report tree has no landing page that identifies, for every collection:

- the exact source fixture;
- whether the output is generated or manually curated;
- the command and version used to create it;
- which files permit manual editing; and
- which tests or documents require it.

The absence of this manifest is a documentation gap, not evidence that the
reports are disposable.

## Findings

1. No accidental tracked cache, dependency, build, or pytest output was found
   in the audited trees.
2. Existing tracked artifacts broadly fit executable-example, native-evidence,
   regression-baseline, or curated-report categories.
3. Provenance is distributed across architecture, experiment, reference, and
   test documents rather than summarized beside each artifact collection.
4. Generated and independently authored native artifacts are often
   distinguishable through naming, but this is not yet enforced by manifests.
5. Five large artifacts merit an explicit necessity and regeneration review;
   their combined presence is not currently a repository-size crisis.

## Follow-up actions

- Add a manifest or README to the CODESYS, OpenPLC, PLCopen XML, AutomationML,
  and report collections, starting with artifacts consumed by tests.
- Record source fixture, generator, native tool version, authorship,
  redistribution status, and regeneration method where applicable.
- Label generated, independently authored reference, and simulation artifacts
  consistently without relying only on filename conventions.
- Review the five files above 500 KB individually before considering Git LFS,
  replacement with smaller fixtures, or removal.
- Preserve every test and documentation reference during any later relocation.
- Do not combine provenance remediation with deletion; make each cleanup step
  independently reviewable.

The subsequent architecture change consolidated ordinary pytest output beneath
`.test-artifacts`. The ignored root `.pytest-tmp-*` directories observed during
this audit were legacy local state rather than tracked artifacts.
