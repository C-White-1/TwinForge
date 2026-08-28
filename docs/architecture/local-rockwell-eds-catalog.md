# Local Rockwell EDS catalogue adapter

TwinForge can use a locally installed Rockwell `Export EDS All` directory as
a read-only device-description catalogue. The Rockwell files remain outside
the repository and are not redistributed by TwinForge.

## Boundary

`RockwellEdsExportCatalog` treats `EDS/Database/export.db` as an index rather
than authoritative device content. It opens SQLite using `mode=ro` and
`immutable=1`, validates the expected schema, resolves indexed paths beneath
the export root, and verifies Rockwell's Base64-encoded SHA-256 value before
parsing an EDS.

Authoritative CIP identity comes from TwinForge's loss-preserving EDS parser.
The database row remains attached as raw evidence so fields not represented by
the neutral model are not discarded.

## Catalogue lookup

Two catalogue-number operations have deliberately different semantics:

- `find_by_catalog_number()` performs an exact, case-insensitive comparison;
- `find_by_base_catalog_number()` also accepts Rockwell `/series` suffixes.

For example, base catalogue `1756-IB16` may resolve `1756-IB16/A`, but it does
not resolve related models such as `1756-IB16D/A`. Multiple results are
retained because the export can contain several EDS revisions. Selecting one
for a configured device requires separate electronic-key compatibility logic.

`reconcile_catalog_candidates()` provides that separate step. Exact keying may
select a candidate only when all five CIP identity fields match and the result
is unique. Compatible Module results are marked as advisory and remain
unselected because product-family acceptance ultimately belongs to the device.

The installed command exposes the same boundary without requiring Python code:

```powershell
uv run twinforge catalog eds `
  --root C:\RA\ExportEDSAll_V38.00 `
  --base-catalog-number 1756-IB16 `
  --format json
```

JSON output contains promoted neutral identity and local provenance. It does
not dump raw EDS statements or every proprietary database field.

An entire Controller L5X can be assessed offline:

```powershell
uv run twinforge catalog l5x controller.L5X `
  --root C:\RA\ExportEDSAll_V38.00 `
  --format json `
  --output reports\eds-catalog-reconciliation.json
```

The result records modules with no indexed candidate, uniquely selected exact
matches, advisory Compatible Module candidates, and unresolved evidence.
The output is replaced atomically. Its Draft 2020-12 JSON Schema can be
exported for CI, MCP clients, or other consumers:

```powershell
uv run twinforge catalog schema `
  --output schemas\eds-catalog-reconciliation.v1.schema.json
```

## Vendor normalization

The export contains several spellings of Allen-Bradley and Rockwell
Automation. When the parsed EDS supplies CIP Vendor ID 1, TwinForge presents
the canonical display name `Allen-Bradley / Rockwell Automation`. The original
database spelling and parsed EDS source extension are preserved unchanged.

## Safety and licensing

The adapter performs no network access and writes nothing into the Rockwell
export. Tests use a TwinForge-authored synthetic SQLite database and EDS file.
Users remain responsible for obtaining and using vendor files under their
applicable Rockwell terms.
