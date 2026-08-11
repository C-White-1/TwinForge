# Example catalogue

The installed `twinforge` command is the supported user interface. Python files
under `examples/` either preserve a former command as a thin CLI wrapper or
demonstrate a focused library API that is intentionally more specialized than
the installed command line.

## CLI compatibility wrappers

These scripts retain their original positional arguments but delegate all
parsing, validation, diagnostics, exit codes, and output behavior to
`twinforge.cli`:

- `export_plcopen.py`
- `export_automationml.py`
- `export_reports.py`

New automation should invoke `twinforge` directly. The wrappers exist for old
commands, documentation, and simple migration.

## L5X and model API demonstrations

- `basic_model.py` constructs and traverses the vendor-neutral model.
- `parse_l5x.py` demonstrates detailed capture reports and model traversal.
- `export_json.py` serializes model evidence as JSON.
- `export_graph.py` emits graph-oriented model evidence.
- `export_module_csv.py` emits the module inventory CSV.
- `export_parameter_report.py` emits parameter and setpoint evidence.
- `export_functional_description.py` builds a functional-description draft.
- `export_corpus_report.py` reports compatibility across an L5X corpus.
- `analyze_rll_corpus.py` publishes per-fixture rung and instruction coverage.

## Analysis demonstrations

- `analyze_aoi_portability.py`
- `analyze_rll_coverage.py`
- `analyze_structured_text.py`
- `analyze_structured_text_semantics.py`
- `export_conversion_readiness.py`
- `export_cyclic_io_report.py`
- `export_diagnostic_report.py`

These are evidence and engineering-analysis APIs. They are not alternate
implementations of an installed export command.

## CODESYS and PLCopen target experiments

- `export_aoi_codesys.py`
- `export_codesys_module_equivalence.py`
- `export_codesys_sys_module_binding.py`
- `export_codesys_visualization.py`
- `export_powerflex525_codesys.py`
- `export_powerflex525_codesys_application.py`
- `export_powerflex525_codesys_bundle.py`
- `diff_codesys_visualizations.py`
- `modify_codesys_visualization.py`
- `report_codesys_visualization.py`
- `report_codesys_visualization_opaque.py`

`export_openplc.py` is also retained in this category. It demonstrates an older
PLCopen XML evaluation adapter aimed at OpenPLC; it does **not** generate the
native OpenPLC project directory produced by `twinforge export --target
openplc`.

## Native OpenPLC fixture demonstrations

- `export_openplc_and.py`
- `export_openplc_counter.py`
- `export_openplc_fail_safe_seal_in.py`
- `export_openplc_or.py`
- `export_openplc_seal_in.py`
- `export_openplc_smoke.py`
- `export_openplc_timer.py`

These scripts construct or export narrow runtime-evidenced fixtures. Use the
installed OpenPLC target for ordinary L5X conversion.

## SNMP laboratory demonstrations

- `SNMPSim/capture_loopback.py` captures only from the explicit loopback lab.
- `SNMPSim/inventory_corpus.py` inventories an external recording corpus.
- `SNMPSim/measure_corpus.py` measures a previously inventoried corpus offline.

No example performs unrestricted network scanning. Live laboratory examples
must retain explicit scope, authorization, and bounded target behavior.

## Deferred discovery and twin-building prototypes

These files preserve planned pycomm3 discovery and digital-twin workflows:

- `build_twin.py`
- `discover_controlnet.py`
- `discover_routes.py`
- `discover_tags.py`
- `inventory.py`
- `scan_controller.py`

They are intentionally retained but are not currently supported user commands.
Five are placeholders. `build_twin.py` records the former builder shape for an
API that has not yet been implemented. Development must resume through the
bounded, authorized discovery roadmap rather than treating these prototypes as
working network tools.
