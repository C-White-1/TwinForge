# Standalone L5X documents

Rockwell component exports contain a context controller but identify one
primary object through the root `TargetType` and the nested
`Use="Target"` element. TwinForge supports these target types:

| `TargetType` | Primary model | Software wrapper |
| --- | --- | --- |
| `Controller` | `Controller` | none |
| `Module` | `Module` | none |
| `Program` | `Program` | `SoftwareComponent(PROGRAM)` |
| `AddOnInstructionDefinition` | `AddOnInstruction` | `SoftwareComponent(FUNCTION_BLOCK)` |

Use the document API when the input may be any supported export:

```python
from twinforge.parsers.l5x import L5XParser

document = L5XParser().parse_document("component.L5X")
print(document.target_type)
print(document.target)
print(document.software_component)
```

`parse_document()` selects exactly one element marked `Use="Target"`. It
rejects ambiguous documents instead of choosing by position or name.
Context dependencies are retained in the document-level source extension, so
no unmodelled L5X content is discarded.

The existing `parse()` method remains a controller-project convenience API
and returns a `Plant`. Existing users do not need to change until they want to
consume standalone component exports.

## Evidence resolution

Parsing does not infer a physical device from a generic controller module.
After independent conversion, an evidence-resolution stage may combine:

```text
Module export
Program export
AOI export
reference evidence
        ↓
Device + SoftwareComponent + evidence-bearing bindings
```

For the PowerFlex example:

- `Dev_PF525_Module.L5X` produces a generic EtherNet/IP `Module`;
- `Dev_PF525_Program.L5X` produces a `Program` software component;
- `Dvc_PF525_AOI.L5X` produces a function-block software component; and
- their combined evidence identifies and binds a PowerFlex 525 `Device`.

## Multi-file and multi-controller corpora

Use `L5XCorpusParser` when an import boundary contains several component or
controller exports:

```python
from twinforge.parsers.l5x import L5XCorpusParser

corpus = L5XCorpusParser().parse_directory("site_exports")

for workspace in corpus.workspaces:
    print(workspace.controller_name, workspace.confirmed)

print(corpus.shared_software)
print(corpus.software_index)
print(corpus.software_bindings)
print(corpus.unassigned_documents)
print(corpus.diagnostics)
```

The directory is an explicit corpus boundary, not an assertion that every
file belongs to one PLC. Processing is deterministic and independent of input
order.

Generate a reviewable Markdown report from the same corpus boundary with:

```powershell
uv run python examples/export_corpus_report.py site_exports `
  reports/site/corpus_evidence.md --title "Site L5X evidence"
```

Ownership resolution is intentionally conservative:

- Every full controller export establishes its own confirmed workspace.
- A Program or Module with one context controller name attaches to a unique
  full controller of that name.
- If no full controller exists, matching component documents form a
  provisional, context-name-only workspace.
- If multiple full controllers use the same name, matching component exports
  remain unassigned and receive ambiguity diagnostics.
- AOI definition exports enter the shared software catalogue. Their context
  controller name is not treated as exclusive ownership.
- Documents with missing or multiple controller contexts remain unassigned.

Folder names are provenance only. They are not controller-ownership evidence.
Context-name-only workspaces are also not proof that documents belong to the
same physical PLC; a future manifest or stronger hardware/project identity
resolver can confirm or split them without reparsing the source files.

## Shared AOI instance resolution

The corpus indexes shared AOI definitions by case-insensitive name. Within
each controller workspace, a Program tag whose `DataType` uniquely matches an
AOI name receives an evidence-bearing `instance_tag` software binding.

This resolution follows the Rockwell AOI instance convention but remains
conservative:

- one matching definition creates a binding;
- multiple matching definitions create duplicate-definition and
  ambiguous-instance diagnostics;
- no matching definition creates no binding and no missing-AOI diagnostic,
  because an unmatched datatype may legitimately be a UDT; and
- every binding records the controller workspace, program, tag, source path,
  and datatype evidence.

The same shared definition can therefore bind instance tags in several PLC
workspaces without making the definition the exclusive property of any PLC.
