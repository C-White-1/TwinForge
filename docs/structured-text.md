# Structured Text front end

TwinForge contains a lossless, recovering Structured Text front end for
analysis and future AOI conversion. It does not replace the original ST stored
on the neutral `Routine` model.

## Preservation model

The lexer emits every source character, including whitespace, comments and
unknown characters. Syntax nodes reference half-open source spans, while the
document retains the complete token stream and original source. Therefore:

```python
document.reconstructed_source == document.source
```

Unsupported syntax produces diagnostics and `UnsupportedStatement` nodes. It
is not silently removed or rewritten.

## Initial supported syntax

- assignments;
- positional and named call arguments;
- function, function-block and source-instruction calls;
- `IF`, `ELSIF`, `ELSE` and `END_IF`;
- `WHILE`, `DO` and `END_WHILE`;
- unary and binary Boolean, comparison and arithmetic expressions;
- parenthesized expressions;
- named and numeric member access such as `Ref_Msg.DN` and `OSR.0`;
- array access such as `Ref_Buffer[i]`;
- Logix dynamic bit selection such as `FOut.[i]`;
- `EXIT` from the innermost loop;
- ordinary and typed literals such as `1000`, `16#033A` and `LTIME#1MS`;
- IEC `(* ... *)`, C-style `/* ... */`, and line comments;
- omitted call arguments such as the second argument of
  `GSV(WallClockTime, , CurrentValue, TNow)`;
- CODESYS call associations using `:=` and `=>`.

This is syntax recognition, not a claim that Logix extensions already have
portable IEC semantics.

## Coverage analysis

```powershell
uv run python examples\analyze_structured_text.py `
  path\to\source.L5X `
  --output reports\structured_text_analysis.txt
```

The report gives routine and statement counts, unsupported-statement counts,
diagnostics and source-preservation status.

The current `Dev_USB_Program.L5X` reference contains eight ST routines and 72
statements under recursive counting. All eight routines parse without
diagnostics or unsupported statements, and every source body reconstructs
exactly. This is corpus-specific syntax coverage, not general IEC 61131-3 or
Logix ST coverage.

As an out-of-sample probe, the current `Dev_PF525_Program.L5X` reference
contains 24 ST routines and 1503 recursively counted statements. Those
routines also parse without diagnostics or unsupported statements after
explicitly modelling Logix dynamic bit selection and `EXIT`. This result still
measures only the syntax present in that file; it does not establish complete
Logix or IEC Structured Text grammar coverage, semantic resolution, or
convertibility.

## Architectural boundary

The front end is independent of L5X capture and target exporters:

```text
Captured Routine ST
        |
        v
Lossless tokens and syntax
        |
        +--> coverage and diagnostics
        |
        v
Future neutral semantic operations
        |
        +--> CODESYS transformation
        +--> OpenPLC transformation
```

Later phases will add semantic resolution and transformations. Target code
must be generated from explicit, tested mappings; the parser alone does not
authorize rewriting a source instruction.

## Semantic analysis

The next read-only layer resolves data names against captured controller
scopes and classifies calls using declarative rules:

```powershell
uv run python examples\analyze_structured_text_semantics.py `
  path\to\source.L5X `
  --output reports\structured_text_semantics.txt
```

Resolution is case-insensitive and follows source scope precedence:

- AOI parameters and local tags shadow controller tags;
- program tags shadow controller tags;
- controller AOI definitions and program routines are available as calls;
- a declared data object used as a callee is retained as a function-block
  instance candidate.

The semantic result retains links to the lossless syntax document. It records
resolved and unresolved references, source and neutral call names, optional
source vendor, semantic diagnostics, and nested neutral statement operations.
Unresolved symbols and calls remain explicit; they are never replaced with
invented declarations or meanings.

Current declarative call mappings cover the instructions encountered in the
reference corpora:

| Source call | Neutral classification |
| --- | --- |
| `ABS` | absolute value |
| `SIZE` | array dimension query |
| `COP` | memory copy |
| `GSV` | controller object read |
| `SSV` | controller object write |
| `MSG` | explicit message |
| `SWPB` | byte swap |
| `TONR` | retentive timer |

The Rockwell source-instruction mappings retain their vendor provenance.
Operands such as the object class and attribute in `GSV` are explicitly
modelled as instruction metadata rather than incorrectly reported as tag
references.

With the current captured declarations and call rules, the USB corpus resolves
126 data references across eight routines with no unresolved references or
unknown calls. It validates all 49 member/index accesses. The PowerFlex corpus
resolves 2853 data references across 24 routines with no unresolved references
or unknown calls and validates all 2980 member/index accesses. Neither corpus
contains an invalid access or invalid mapped source-instruction signature
under the current rules. These numbers measure only the calls, types and
declarations present in those files.

Captured user-defined data types are traversed member by member, including
nested structures. Array indexing is checked against captured tag, parameter,
and member dimensions. Numeric bit access produces `BOOL`, while literal,
unary, binary, member, index and selected call expressions receive
best-evidence result types. Exact argument counts are checked for the mapped
source instructions.

An access to a structure whose definition is unavailable is `unverified`, not
invalid. The analyzer does not claim that a target runtime implements an
equivalent operation.

## Logix type library

The Logix analysis adapter supplies evidence-backed definitions for `TIMER`,
`FBD_TIMER`, `STRING`, and a deliberately partial `MESSAGE`. Each definition
retains its vendor, source description, members, and completeness. A member
absent from the partial `MESSAGE` definition therefore remains unverified
rather than becoming invalid.

The timer structure follows Rockwell's
[TONR/FBD_TIMER documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/timer-and-counter-instructions/timer-on-delay-with-reset--tonr-.html).
The message members follow the
[MSG instruction](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/input-output-instructions/message--msg-.html)
and
[MESSAGE structure](https://www.rockwellautomation.com/en-id/docs/studio-5000-logix-designer/38-01/contents-ditamap/instruction-set/message-structure.html)
documentation. The default `STRING` layout follows Rockwell's documented
`LEN` plus `SINT` `DATA` structure and 82-character default.

Captured controller data types override library types with the same name.
TwinForge also derives a partial structural type for each AOI backing instance
from captured non-`InOut` parameters. AOI local tags remain private and are not
exposed as instance members.

## Assignment and AOI binding

Assignment and call-argument checks use an explicit source-dialect conversion
policy. The generic semantic engine assumes no implicit conversions. The Logix
adapter currently records these source behaviours:

- implicit conversion among atomic numeric types;
- `BIT` and `BOOL` logical compatibility;
- integer values assigned to `BIT` or `BOOL`;
- string literals assigned to Logix string-family types such as `STR_40`.

Each result is retained as `exact`, `implicit`, `unknown`, or `incompatible`.
Only incompatible results produce diagnostics; unknown results stay visible in
the report.

For captured Add-On Instructions, TwinForge binds the first call operand to the
AOI backing-instance tag. Remaining positional operands bind to parameters
marked `Required="true"` in declaration order, excluding the system-defined
`EnableIn` and `EnableOut` parameters. The instance type, required argument
count, parameter data types, array rank, and `Input`/`Output`/`InOut`
assignability are checked. AOI `Dimensions="1"` is treated as a generic
one-dimensional parameter contract rather than a one-element array.

This binding rule is isolated in the Logix analysis adapter. It is not a
generic IEC calling convention and will not be reused automatically by
CODESYS or OpenPLC exporters.

Across the current USB corpus, assignment compatibility is 21 exact, 13
implicit, 11 unknown and zero incompatible. All 12 bound AOI operands are
exact. Across the PowerFlex corpus, assignment compatibility is 863 exact,
207 implicit, 141 unknown and zero incompatible. All 47 bound AOI operands are
exact. Remaining unknown assignments arise where expression result typing is
still conservative rather than from unresolved member paths.
