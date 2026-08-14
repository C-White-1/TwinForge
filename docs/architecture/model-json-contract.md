# Neutral model JSON contract

TwinForge model JSON is a deterministic, versioned evidence format for tools
that need the converted neutral model without importing Python classes. It is
not a replacement for the source L5X document. Retained source extensions
remain part of the output so unknown attributes, elements, text, and metadata
are not discarded.

## Envelope

Version 1.0 contains exactly three top-level fields:

```json
{
  "schema_version": "1.0",
  "source_format": "l5x",
  "document": {}
}
```

`document` is a typed `L5XDocument` record. Paths and references use RFC 6901
JSON Pointer syntax rooted at `#/document`.

## Evidence nodes

Ordinary JSON primitives, arrays, and string-keyed objects retain their usual
meaning. Four reserved keys identify serialization controls:

- `$type` identifies a serialized dataclass record. Remaining fields contain
  its evidence.
- `$ref` identifies a shared or cyclic object by its first-occurrence JSON
  pointer.
- `$bytes_hex` preserves an exact byte sequence as hexadecimal text.
- `$map` preserves ordered key/value entries when keys are not strings or
  collide with reserved control keys.

A control object cannot mix control forms. For example, a `$ref` object
contains only `$ref`. Source dictionaries containing reserved names are
automatically represented as `$map` entries, preventing ambiguity or loss.

## Runtime-only fields

`Asset.id` currently contains a generated runtime UUID rather than source
evidence. It is deliberately omitted so repeated conversion of the same input
is byte-stable. `parent` fields are construction back-references and are also
omitted; ownership is already represented by containment, while other shared
objects use `$ref`.

## Validation

Python consumers can validate the envelope and recursive evidence encoding:

```python
from twinforge.exporters import validate_model_json

document = validate_model_json(json_text)
```

The installed CLI exposes the same validation boundary:

```powershell
uv run twinforge model validate build\project-model.json
```

Validated evidence can be inventoried without reconstructing mutable Python
objects:

```powershell
uv run twinforge model inspect build\project-model.json
uv run twinforge model inspect build\project-model.json --format json
```

The inventory reports typed records, references, source extensions, exact byte
sequences, and typed maps. It is suitable for inspection and automation, but
does not claim that the JSON document is a replacement source format.

## JSON Schema

TwinForge packages a maintained JSON Schema Draft 2020-12 definition of the
version 1.0 structural grammar. Export it for editors, CI, or tools that do not
import the Python package:

```powershell
uv run twinforge model schema --output build\model-json-1.0.schema.json
```

The schema validates the envelope and recursive control-node shapes. Use
`twinforge model validate` when semantic validation is required: JSON Schema
cannot prove that an RFC 6901 `$ref` resolves to an already established node.

## Read-only queries

Select a precise evidence node without reconstructing the object graph:

```powershell
uv run twinforge model query build\project-model.json `
  "#/document/target/modules/Local%3A1"
```

Pointers use RFC 6901 fragment form. `--resolve-reference` follows the selected
node when it is exactly a `$ref`; it does not recursively expand the graph, so
cycles and shared identity remain explicit. `--compact` produces a compact
JSON response suitable for scripts and future read-only adapters.

Discover typed records before querying a particular node:

```powershell
uv run twinforge model records build\project-model.json --type Module
uv run twinforge model records build\project-model.json `
  --type twinforge.model.tag.Tag --format json
```

Type matching is exact. A short class name matches the final component of
`$type`; a fully qualified name matches the complete value. Results contain
stable pointers to first-occurrence records and never follow `$ref` objects,
avoiding duplicates and recursive traversal.

## Structural comparison

Compare two validated model artifacts without reparsing their L5X sources:

```powershell
uv run twinforge model compare build\before.json build\after.json
uv run twinforge model compare build\before.json build\after.json `
  --format json
```

Comparison reports deterministic `add`, `remove`, and `replace` operations at
RFC 6901 pointers. JSON output retains the exact before and after evidence.
Lists are compared by position and dictionaries by key; TwinForge does not
guess that reordered or renamed records are equivalent.

Validation rejects unsupported versions, malformed references, invalid byte
encoding, malformed typed maps, mixed reserved-key forms, and non-finite
numbers. References must resolve to an already established complex evidence
node. This rejects dangling and forward references and preserves the
first-occurrence ordering used by deterministic serialization. Model fields
remain forward-compatible: new non-reserved fields can be added to typed
records without changing the evidence-node grammar.
