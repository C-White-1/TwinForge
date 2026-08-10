# Tag Dependency Graph

TwinForge builds a source-neutral cross-reference graph from the losslessly
captured software-call model. Ladder instructions and Structured Text calls
therefore share the same dependency representation.

## Resolution

Each call operand is scanned for identifier-like references. Resolution is
case-insensitive, matching Logix symbol behavior, and follows Logix scope:

1. a program tag in the calling program; then
2. a controller tag.

Member and array suffixes are retained separately from the owning tag. For
example, `Timer.ACC` resolves to the `Timer` tag with member path `.ACC`.
Program and controller tags with the same name remain distinct graph keys.

Identifiers that do not resolve are preserved in
`unresolved_references`. This includes direct module operands such as
`Local:1:I.Data.0`, unknown AOI expressions, and references whose definitions
were absent from the captured export. TwinForge does not create placeholder
tags or discard those operands.

## Access semantics

Instruction rules classify supported occurrences as `read`, `write`, or
`read_write`. Current rules cover contacts, coils, comparisons, timers,
counters, resets, one-shots, moves, and arithmetic operations. Structured
Text named call arguments use `:=` as input/read and `=>` as output/write.

Direct Structured Text assignments classify the target as a write and the
value as a read. References in `IF`, `ELSIF`, and `WHILE` conditions are reads.
Nested statement bodies, member selections, and array-index expressions are
walked from the lossless syntax tree. Calls embedded in those expressions are
left to the call-operand extractor so that their references appear once with
the most specific available direction evidence.

Unknown instructions and positional AOI parameters remain `unknown` until a
definition or instruction specification establishes their flow. Unknown is a
retained epistemic state, not an error or an assumed read.

## Current boundary

The deterministic JSON graph records program, routine, rung or line,
instruction, argument position, exact operand, resolved scope, member path,
and access semantics. This is sufficient for instruction-level
cross-reference reports and is a foundation for alarm, cause-and-effect, and
functional-description generation.

The broader roadmap item remains open. Alias-definition edges and dependencies
expressed in other routine-body languages still require explicit extraction.
Until those are implemented, this graph must not be described as a complete
controller cross-reference database.
