# Artifact Policy

This policy distinguishes authoritative TwinForge source from test evidence,
external references, curated outputs, and disposable local state. Location or
file extension alone does not establish authority, provenance, or permission to
redistribute an artifact.

## Principles

1. Never discard source evidence merely to simplify the repository.
2. Track only material that is necessary, lawful to redistribute, and assigned
   a clear maintenance purpose.
3. Keep generated output distinguishable from the source that produced it.
4. Preserve provenance, tool version, capture context, and known limitations
   for curated evidence.
5. Never commit credentials, private keys, authorization tokens, unsanitized
   site inventories, or sensitive live-network captures.

## Artifact classes

### Product source

Installable code under `src/twinforge/`, package configuration, CLI entry
points, and maintained schemas authored for TwinForge are authoritative product
source. They are tracked and must pass the applicable tests, Ruff, and Pyright.

Generated package metadata, wheels, distributions, and `build/` output are not
source. Authoritative package configuration remains in `pyproject.toml`, while
the resolved Python environment is recorded by `uv.lock`.

### Tests and fixtures

Automated tests under `tests/` are authoritative behavioral specifications.
Small fixtures may be tracked when they are legally shareable, deterministic,
necessary for a stated test, and stripped of secrets or site-sensitive data.

Native-editor or runtime fixtures must identify whether they are:

- independently created reference evidence;
- deterministic TwinForge-generated output; or
- a sanitized extract of another source.

Large, licensed, or sensitive inputs stay outside Git. Tests that require them
must fail gracefully, skip explicitly, or accept a user-supplied path rather
than silently substituting invented evidence.

### Executable examples

`examples/` contains thin CLI compatibility wrappers, focused API examples,
and selected native-tool projects used to demonstrate or validate behavior.
Tracked examples must have a documented purpose and must not be the sole owner
of production semantics.

An editor export or generated project may be tracked as an example when it is
small, legally redistributable, reviewed, and needed to reproduce a documented
compatibility result. Incidental build output inside an example is disposable.

### External reference material

The root `reference/` directory is ignored. It is the normal location for
standards, XSD files, manuals, EDS files, native editor exports, packet traces,
SNMP recordings, and other externally obtained evidence.

Each external item should retain, beside it where practical:

- source URL or supplier;
- title, version, and publication date;
- acquisition date;
- copyright or licence information;
- checksum when exact identity matters; and
- the TwinForge feature or test that uses it.

An external artifact may move into tracked tests or examples only after its
redistribution rights, sensitivity, size, provenance, and maintenance purpose
have been reviewed explicitly.

### Curated reports and evidence

`reports/` is reserved for reviewed engineering evidence that documents a
capability, fixture, QA issue, portability result, or target experiment. A
curated report is not automatically a product guarantee.

Tracked reports should state their input, generator or method, date or stable
version, evidence boundary, and any manual interpretation. Regenerating a
report must not erase unresolved or unknown evidence merely to reduce noise.

Ad hoc command output belongs in a user-selected output directory, ignored
workspace, or temporary directory rather than `reports/`.

### Generated output

Generated PLCopen XML, CODESYS exports, OpenPLC project directories,
AutomationML, CSV, JSON, diagrams, and engineering documents are normally build
artifacts. They may be tracked only when they serve as a reviewed example,
regression baseline, or curated evidence item.

When generated output is tracked:

- the authoritative generator or source must be identified;
- deterministic generation is preferred;
- generated and independently authored reference artifacts must be labelled;
- unnecessary tool caches and compiled intermediates must be excluded; and
- reviewers must be able to tell whether hand editing is permitted.

PlantUML source under `docs/architecture/diagrams/` is authoritative. The
adjacent SVG renderings are tracked viewing artifacts so GitHub does not depend
on an external rendering service.

### Temporary and local state

The following are disposable and must remain untracked:

- `.pytest_cache/`, `.test-artifacts/`, and legacy root `.pytest-tmp-*`
  directories;
- `__pycache__/`, bytecode, coverage data, and tool caches;
- virtual environments and dependency caches;
- `node_modules/`;
- `build/`, `dist/`, and generated package metadata;
- editor logs and machine-specific settings; and
- scratch exports without a reviewed evidence purpose.

Tests use pytest-managed `tmp_path` values rooted beneath `.test-artifacts`.
Pytest clears that directory at the beginning of the next run, so the most
recent run remains available for diagnosis without accumulating one root
directory per invocation. Evidence that must survive the next run must be
copied to a separate ignored diagnostic location and reviewed before any
deliberate promotion into Git.

## Promotion checklist

Before moving a local, external, or generated artifact into Git, confirm:

- its purpose cannot be met by a smaller authored fixture;
- redistribution is permitted;
- sensitive identity, topology, address, and credential data is removed;
- provenance and the evidence boundary are documented;
- generated versus independently authored status is explicit;
- its authoritative source or regeneration method is known;
- its path matches the ownership map in `ARCHITECTURE.md`; and
- tests or documentation identify why future maintainers must preserve it.

If any answer is unknown, keep the artifact outside Git until it can be
resolved. Ignoring a file protects the repository but does not by itself grant
permission to acquire, use, or share it.

## Removal and relocation

Do not delete or relocate tracked evidence solely because it appears generated
or historical. First determine whether tests, documentation, provenance, or a
validated compatibility result depends on it. Repository cleanup should be a
separate, reviewable change that preserves required evidence and updates every
reference.
