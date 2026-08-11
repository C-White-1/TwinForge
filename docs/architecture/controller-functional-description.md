# Controller Functional Description

The controller functional-description draft is an aggregation layer. It does
not parse source XML or independently reinterpret logic. Instead, it combines
the vendor-neutral controller model with the tested dependency, I/O,
alarm/trip, and cause/effect analyses.

## Captured structure

The document reports:

- controller identity and model inventory;
- task configuration and scheduled-program resolution;
- program, main-routine, routine-language, rung, and Structured Text counts;
- observed software call targets and tag counts; and
- generated I/O, alarm/trip, cause/effect, and dependency coverage.

Program and routine names remain source evidence. TwinForge does not transform
a suggestive name such as `R03_Trips` into a verified statement of process
purpose.

## Boundaries

The output is deliberately called a draft. Unsupported routine languages,
unknown instruction flow, unresolved operands, and absent plant documentation
may hide relevant behavior. It does not establish mechanical, electrical,
process-safety, commissioning, or alarm-philosophy requirements.

The `twinforge report` bundle writes the result to
`functional_description.md` alongside the detailed evidence reports it cites.
