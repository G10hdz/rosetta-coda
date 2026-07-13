# SPEC-002 — Metadata loader and identity cohorts

Status: Verified  
Owner: Engineering  
Depends on: SPEC-001

## Outcome

Load upstream metadata without silent coercion and assign identity eligibility without inventing identities.

## Input contract

Primary file: `external/sw-combinatoriality/data/DominicaCodas.csv`, pinned by SHA-256. Required columns:

`codaNUM2018`, `Date`, `nClicks`, `Duration`, `ICI1..ICI9`, `CodaType`, `Clan`, `Unit`, `UnitNum`, `IDN`.

Rules:

- Decode `utf-8-sig`; strip BOM only from header.
- Accept both `%d/%m/%Y` and `%d-%m-%Y`, emitting canonical ISO date.
- Treat zero ICIs after `nClicks - 1` as padding, not observations.
- Preserve source row number and raw values in provenance.
- Reject negative numeric values, duplicate coda IDs, missing required columns, and unexplained non-padding ICI counts.

## Identity contract

- `resolved`: single non-sentinel label with no `/` or `?`.
- `unresolved_unknown`: `0` or `9999`.
- `unresolved_composite`: contains `/`.
- `unresolved_uncertain`: contains `?`.

No alias correction occurs in loader.

## Output contract

`load_dominica_codas(path) -> LoadResult` containing validated `CodaRecord` values, dataset hash, schema version, row counts, cohort counts, and validation warnings.

Known upstream fixture expectations:

- 8,719 rows
- 13 units
- 2 clans
- 5,705 rows with `IDN=0`
- 47 rows with `IDN=9999`
- five observed rows with ICI-layout inconsistencies must be surfaced, not silently repaired: three have too few non-zero ICIs; two contain zeros inside the expected ICI span followed by non-zero values

## Acceptance criteria

- [x] Known fixture counts match.
- [x] Date formats normalize correctly.
- [x] Padding is removed from canonical ICI vectors.
- [x] All unresolved categories receive `whale_id = null` plus preserved `whale_id_raw`.
- [x] Strict mode rejects the five inconsistent rows; permissive mode quarantines them with warnings and raw provenance.
- [x] No input file is modified.

## Stop conditions

Schema drift or unexplained count mismatch produces a failed load artifact and blocks normalization.
