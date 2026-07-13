from pathlib import Path

import pytest

from data.loader import load_dominica_codas

DOMINICA_PATH = Path("external/sw-combinatoriality/data/DominicaCodas.csv")


class TestFixtureCounts:
    def test_total_rows(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        assert result.row_count == 8719, (
            f"Expected 8719 rows, got {result.row_count}"
        )

    def test_permissive_quarantines_ici_inconsistencies(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        ici_warnings = [w for w in result.validation_warnings if "QUARANTINED" in w]
        assert len(ici_warnings) == 5, (
            f"Expected 5 ICI-inconsistent rows, got {len(ici_warnings)}"
        )
        assert len(result.quarantined) == 5
        assert {row.coda_id_raw for row in result.quarantined} == {
            "5092",
            "5734",
            "6574",
            "6754",
            "8576",
        }
        assert all(row.raw_values for row in result.quarantined)

    def test_strict_rejects_ici_inconsistencies(self):
        with pytest.raises(ValueError, match="ICI layout inconsistent"):
            load_dominica_codas(str(DOMINICA_PATH), qc_mode="strict")

    def test_13_units(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        units = {r.unit for r in result.records}
        assert len(units) == 13, f"Expected 13 units, got {len(units)}"

    def test_2_clans(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        clans = {r.clan for r in result.records}
        assert len(clans) == 2, f"Expected 2 clans, got {len(clans)}"

    def test_idn_zero_count(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        assert result.cohort_counts["unresolved_unknown"] == 5752
        assert result.cohort_counts["unresolved_composite"] == 15
        assert result.cohort_counts["unresolved_uncertain"] == 1
        assert result.cohort_counts["resolved"] == 2951

    def test_no_duplicate_coda_ids(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        ids = [r.coda_id for r in result.records]
        assert len(ids) == len(set(ids))


class TestLoaderValidation:
    def test_date_parsing(self):
        """Verify dates parse correctly"""
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        dated = [r for r in result.records if r.date is not None]
        assert len(dated) > 0
        for r in dated[:10]:
            parts = r.date.split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4

    def test_resolved_has_whale_id_raw(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        resolved = [
            r for r in result.records if r.identity_status.value == "resolved"
        ]
        assert len(resolved) > 0
        for r in resolved:
            assert r.whale_id_raw not in ("0", "9999", "")
            assert "/" not in r.whale_id_raw
            assert "?" not in r.whale_id_raw
            assert r.whale_id == r.whale_id_raw

    def test_unresolved_has_id_raw_preserved(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        unknown = [
            r
            for r in result.records
            if r.identity_status.value == "unresolved_unknown"
        ]
        if unknown:
            for r in unknown:
                assert r.whale_id_raw in ("0", "9999")
                assert r.whale_id is None

    def test_canonical_icis_no_padding(self):
        """ICIs after nClicks-1 are removed"""
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        for r in result.records[:100]:
            expected = r.click_count - 1
            assert len(r.icis_s) == expected, (
                f"coda {r.coda_id}: expected {expected} ICIs, got {len(r.icis_s)}"
            )

    def test_all_icis_non_negative(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        for r in result.records:
            assert all(x >= 0 for x in r.icis_s)


class TestProvenance:
    def test_dataset_hash_present(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        assert len(result.dataset_hash) == 64

    def test_source_ref_row(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        first = result.records[0]
        assert first.source_ref.dataset == "DominicaCodas.csv"
        assert first.source_ref.row >= 2
        assert first.source_values["codaNUM2018"] == "1"

    def test_schema_version(self):
        result = load_dominica_codas(str(DOMINICA_PATH), qc_mode="permissive")
        assert result.schema_version == "0.1.0"
