# Decisions

## 2026-06-29

### Domain model is the central API

All discovery modules populate the model classes.

Exporters never communicate directly with discovery code.

Reason:

Keeps online discovery, ACD parsing, and L5X parsing interchangeable.

## 2026-07-02

### Modules contain Identity objects

Identity information is not duplicated across model classes.

Reason:

Common representation for controllers, modules, drives and network devices.

## 2026-07-24

### Captured source extensions preserve unsupported L5X

Known content is promoted into typed model fields. Unknown attributes,
elements and source representations remain attached as extensions.

Reason:

Parser progress must not make TwinForge lossy, and future converters need
access to information the current model does not yet understand.

### PLCopen XML and AutomationML have separate responsibilities

PLCopen XML represents executable IEC 61131-3 project content. AutomationML
represents equipment, signals, engineering context and document relationships.
AutomationML references the generated PLCopen document rather than embedding a
second executable model.

Reason:

This follows the strengths of each standard and avoids conflicting sources of
truth.

### Evidence carries provenance and confidence

Explicit source values, derived relationships and naming/description
inferences are distinguished. Conflicts are diagnosed rather than silently
resolved.

Reason:

Engineering units, ranges and capacity can be correct for different reasons.
Users and exporters must be able to assess the strength of each claim.

### Standards references remain local

Downloaded standards documents, base libraries and XSDs live in the ignored
`reference/` directory. Documentation records their official source.

Reason:

TwinForge can validate against authoritative material without assuming the
right to redistribute it.

## 2026-07-25

### XML validation has structural and semantic layers

PLCopen and CAEX output is checked against available XSDs. AutomationML also
receives TwinForge checks for IDs, class paths, internal links and referenced
documents.

Reason:

An XSD proves document structure, but does not prove that every cross-document
or library reference resolves.

### I/O capacity and use are separate facts

The model distinguishes nominal capacity, configured count,
unavailable-by-configuration count, assigned points and usable spare points.

Reason:

A catalog may advertise more channels than the active wiring/configuration
permits. An unreferenced but unavailable channel is not a spare.

### Catalog decoding is a vendor-specific evidence source

Recognized Rockwell catalog conventions may provide nominal capacity, but the
result records its decoder and provenance and is not embedded as a universal
model rule.

Reason:

Names such as `1756-IB16` are useful engineering evidence, while suffix-only
guessing is not reliable across manufacturers, module families or wiring
configurations.

### Generated identifiers are deterministic

Stable source identities produce stable generated object identifiers. Runtime
metadata may use the actual export time; tests inject fixed values when
repeatability is required.

Reason:

Stable documents produce meaningful diffs without misrepresenting every
production export as having occurred on a fixed date.

## 2026-08-12

### TwinForge remains a monorepo

TwinForge retains one repository and one distributable Python package. The
parsers, vendor-neutral model, analysis, executable IR, reports, discovery,
and target exporters share contracts and fixtures, and changes commonly need
to cross those boundaries atomically. Target-specific optional dependencies
are already isolated through dependency groups rather than incompatible
packages.

The August 2026 reassessment found 894 tracked files containing approximately
12.7 MiB. There is no evidence of independent release cycles, incompatible
dependency sets, or materially separate contributor groups. Splitting the
repository would therefore add version coordination without establishing a
genuine ownership or deployment boundary.

Reassess this decision if one or more of these conditions emerges:

- a component needs an independently versioned release cycle or compatibility
  policy;
- platform or dependency requirements cannot coexist in one package and CI
  workflow;
- a stable ownership, governance, or access-control boundary develops between
  contributor groups;
- clone size, CI duration, or generated-artifact volume materially impairs
  normal development; or
- a separately deployable service establishes a narrow, versioned interface
  to the rest of TwinForge.

Module count, target-specific directories, conceptual breadth, and ignored
local reference material are not by themselves reasons to split. Navigation
and artifact-policy problems should first be addressed through documented
boundaries inside the repository.

Reason:

The vendor-neutral model and preservation pipeline are TwinForge's shared
foundation. Keeping them and their consumers in one repository supports
atomic change, cross-target testing, and consistent evidence handling.
