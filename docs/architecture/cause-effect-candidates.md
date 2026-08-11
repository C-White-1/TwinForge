# Cause-and-Effect Candidates

TwinForge derives a conservative review matrix from the tag dependency graph
and the explicitly labelled alarm/trip candidate set. It does not claim that
software co-location alone defines a validated process cause and effect.

## Evidence rule

For each observed write to an alarm/trip candidate, TwinForge collects resolved
reads and unresolved operands at exactly the same program, routine, and rung or
Structured Text line. Each emitted relationship records:

- the cause and effect symbols;
- resolved or unresolved cause status;
- alarm/trip classification;
- program, routine, and source location;
- read and write instructions; and
- the `same_logic_location` evidence basis.

Every relationship initially has `causal_relationship_verified = false`.
Co-location may include enabling conditions, mode gates, resets, housekeeping,
or other operands that are not process causes.

## Engineering boundary

Engineering review is still required to establish polarity, delay, voting,
latching, suppression, operating-state applicability, and shutdown action.
Unsupported routine languages and unresolved operands prevent the output from
being described as a complete controller cause-and-effect matrix.

## Report formats

The `twinforge report` bundle writes `cause_effect_candidates.md`,
`cause_effect_candidates.csv`, and `cause_effect_candidates.json`. The formats
retain unverified and unresolved evidence rather than silently omitting it.
