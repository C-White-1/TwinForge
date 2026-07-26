# AOI portability analysis

TwinForge assesses Rockwell Add-On Instructions from the vendor-neutral model
before attempting target-specific code generation. The analysis is deliberately
conservative: it identifies evidence and required runtime services, but does
not claim that imported code is semantically equivalent.

## Dispositions

| Disposition | Meaning |
| --- | --- |
| `portable_candidate` | No known target-runtime requirement or unresolved implementation evidence was detected. |
| `adapter_required` | The AOI needs one or more declared runtime capabilities. |
| `manual_review` | An implementation body, dependency, or routine language could not be analyzed. |

An AOI with retained local state or lifecycle behavior is recommended as an
IEC function block. A stateless AOI is recommended as an IEC function.

## PLCopen Common Behaviour detection

TwinForge separately assesses whether an AOI already exposes a complete
PLCopen-style behaviour interface:

| Model | Control input | Completion/status outputs |
| --- | --- | --- |
| Edge triggered | `Execute` or `xExecute` | `Done`, `Busy`, `Error`, `ErrorID` |
| Level controlled | `Enable` or `xEnable` | `Valid`, `Busy`, `Error`, `ErrorID` |

The Execute/Done and Enable/Valid pairings follow PLCopen's *Creating PLCopen
Compliant Function Block Libraries* guidance. Optional Abort, Aborted, TimeOut,
and TimeLimit members are recorded as extensions.

A wrapper is recommended only for a complete interface with compatible input
and output directions. Partial interfaces are reported but are not changed
automatically. Rockwell's system-defined `EnableIn` and `EnableOut` parameters
do not constitute the PLCopen level-controlled model and are deliberately
excluded from detection.

The assessment describes a possible wrapper; it does not alter the captured
AOI or claim that its internal state transitions conform to the PLCopen state
machine.

## Runtime capability contracts

The neutral analysis layer defines capabilities rather than CODESYS or OpenPLC
APIs. A target profile implements `RuntimeCapabilityProvider` and declares the
capabilities its adapter supplies.

| Capability | Current Rockwell evidence |
| --- | --- |
| `explicit_messaging` | `MSG` call or `MESSAGE` datatype |
| `wall_clock_read` | `GSV` call targeting `WallClockTime` |
| `controller_object_read` | `GSV` call |
| `controller_object_write` | `SSV` call |
| `module_reference` | `MODULE` datatype |
| `prescan_hook` | AOI prescan execution |
| `postscan_hook` | AOI postscan execution |
| `disabled_scan_hook` | AOI enable-in-false execution |

Evidence is retained alongside each requirement. This allows a future target
adapter to report exactly why a capability is needed and prevents vendor terms
from becoming the public runtime contract.

`evaluate_runtime_compatibility` compares an AOI's requirements with a target
provider. Target bindings belong outside this neutral analysis module. A future
CODESYS provider and OpenPLC provider can therefore satisfy different subsets
without changing L5X capture, conversion, or the controller model.

## Command

```powershell
uv run python examples\analyze_aoi_portability.py `
  path\to\source.L5X `
  --output reports\aoi_portability.txt `
  --puml reports\aoi_portability.puml
```

The report includes source calls and datatypes, dependency resolution, inferred
state, lifecycle hooks, runtime capabilities, and the evidence for each
capability.

The optional PlantUML output visualizes AOI-to-AOI dependencies, referenced
datatypes, and calls across the target-runtime adapter boundary. TwinForge
generates PlantUML source and does not require PlantUML merely to run the
analysis; rendering that source to SVG or PNG remains a separate step.
