# Plantwide Integration L5X and MCP Tool Analysis

## Source

This note records useful architectural ideas from Plantwide Integration's
video
[Using AI to Read Rockwell PLC Code: An L5X Tool with an MCP Server](https://www.youtube.com/watch?v=c6ZLfLGPnZc).
The source was reviewed through a user-supplied NotebookLM summary on
2026-08-15 rather than a timestamped verbatim transcript. Consequently, this
document paraphrases demonstrated concepts and does not attribute exact
quotations or independently verify every implementation claim.

The tool is described as an internal project capability rather than a product
offering. It reportedly accepts L5X directly, converts ACD projects to L5X,
provides an API and MCP server, supports offline and read-only live use, and
can operate with or without an AI client.

## Ideas worth adopting

### Bounded engineering retrieval

The strongest architectural idea is to let an agent inspect a controller as
an engineer would: one routine, tag cross-reference, AOI, diagnostic, or
relationship at a time. This avoids placing an entire large controller project
into one model context and reduces irrelevant or conflicting evidence.

TwinForge already has suitable foundations:

- versioned neutral-model JSON and JSON Schema;
- RFC 6901 read-only queries;
- typed record discovery with stable pointers;
- structural model comparison;
- deterministic reports and diagnostics; and
- CLI and Python services that remain usable without AI.

A future MCP adapter should compose these application services rather than
parse L5X, open protocol sockets, or mutate the domain model directly.

Candidate bounded tools include:

- list controllers, programs, routines, tasks, tags, and AOIs;
- return one routine with retained source evidence;
- find scoped tag definitions and references;
- find AOI definitions, instances, and parameter bindings;
- list unresolved references and conversion diagnostics;
- inspect communication relationships;
- compare two validated neutral-model artifacts; and
- generate an existing deterministic engineering report.

### Explainable brownfield assessment

The source describes ranking the difficulty of modifying an existing project.
This is useful for quoting, but TwinForge should expose an evidence-backed
assessment rather than an unexplained score.

Potential measures include:

- controller, program, routine, rung, tag, and AOI counts;
- supported and unsupported instruction coverage;
- source-protected or otherwise unavailable content;
- unresolved routine, tag, datatype, and AOI references;
- repeated structures versus reusable definitions;
- controller-scoped and program-scoped coupling;
- produced and consumed tags, messages, and external dependencies;
- safety, motion, redundancy, or vendor-specific features;
- conversion diagnostics and target-specific portability; and
- evidence relevant to online versus offline implementation planning.

Every measure should link to its source records. Any aggregate rating must
publish its rubric, weighting, unavailable inputs, uncertainty, and limits.
It must remain an estimating aid rather than a guaranteed labour forecast.

### Deterministic review with AI explanation

The source describes finding dead code, missing routine targets, incomplete
state behavior, repeated implementation, and difficult AOI replacements.
TwinForge should divide these into distinct confidence classes:

1. syntactic or referential defects established from captured evidence;
2. structural findings established by deterministic graph analysis;
3. pattern deviations based on an explicit engineering rule; and
4. speculative design recommendations requiring human review.

Deterministic services should produce findings, evidence pointers, severity,
and confidence. AI may explain, summarize, or prioritize those findings but
must not silently become the source of record.

### Multi-document engineering context

Retrieving PLC evidence alongside drawings, manuals, error-code references,
and related controller projects could materially improve troubleshooting and
change planning. Such sources must retain separate provenance, licensing,
revision, checksum, and confidence. A retrieved drawing or manual page must
not be represented as controller-observed state.

### Deployment and data governance

The source emphasizes customer-controlled Windows or Linux infrastructure and
private models where cloud disclosure is unacceptable. A future TwinForge MCP
deployment should therefore support:

- offline and non-AI operation as the baseline;
- local or customer-controlled deployment;
- explicit artifact and prompt-data classifications;
- least-privilege access to selected projects and evidence;
- auditable MCP calls and result provenance; and
- deliberate policies for model providers, retention, and telemetry.

## Capabilities requiring separate evidence

### ACD conversion

ACD is a proprietary Rockwell project format. The source does not establish
whether conversion uses Studio 5000 automation, another installed Rockwell
component, or an independent decoder. TwinForge must not claim portable ACD
support without documenting the mechanism, platform dependency, licence, and
loss characteristics.

### Live controller values

Read-only live values could help identify conditions blocking a sequence, but
this is a different authority and risk boundary from offline model inspection.
It requires an explicitly authorized target, exact variable allowlists,
request budgets, bounded polling, timestamps, quality and communication-state
evidence, and an auditable stop condition.

The duration of a complete explicit-message read cycle should be called a
polling or acquisition interval. It should not be called an RPI unless it is
actually the Requested Packet Interval of an I/O or produced/consumed
connection.

### Safety and fault diagnosis

Navigation to an E-stop, guard, or safety-monitor condition may assist a
qualified engineer, but the system must not recommend bypassing safeguards or
claim that a logic condition proves the physical system is safe. Safety
findings are evidence-navigation aids and require independent validation under
the applicable safety lifecycle.

### Historical and continuous troubleshooting

A historian or looped diagnostic agent introduces retention, time alignment,
sampling, alarm, cybersecurity, and operational-governance requirements. It
should remain separate from the first read-only MCP milestone and must not be
enabled merely because an MCP client requests it.

## TwinForge direction

The source validates a practical use for TwinForge's neutral query services:
an agent should retrieve small, source-linked engineering records instead of
receiving an unbounded controller dump. The recommended progression is:

1. offline read-only MCP inspection over validated neutral artifacts;
2. deterministic reference, graph, and review services;
3. explainable brownfield-change assessment;
4. governed multi-document retrieval; and
5. separately authorized live evidence only after laboratory validation.

This progression extends TwinForge without making AI mandatory, weakening the
vendor-neutral core, or conflating interpretation with captured evidence.
