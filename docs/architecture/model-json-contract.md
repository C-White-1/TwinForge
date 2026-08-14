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

Validation rejects unsupported versions, malformed references, invalid byte
encoding, malformed typed maps, mixed reserved-key forms, and non-finite
numbers. Model fields remain forward-compatible: new non-reserved fields can
be added to typed records without changing the evidence-node grammar.
