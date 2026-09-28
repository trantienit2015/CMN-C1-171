"""Catalog matching, including the language the request actually arrives in."""

import re

from src.services.catalog_kb_service import _CATALOG, catalog_size, is_valid_template_id, retrieve_candidates


class TestJapaneseRequestsMatch:
    """Every trigger was an English word, so a Japanese request scored zero against
    all ten entries and the ranking collapsed to catalog order."""

    def test_a_japanese_request_reaches_its_entry(self):
        top = retrieve_candidates("在庫の需要予測を店舗ごとに出したい", top_k=3)
        assert top and top[0]["template_id"] == "SAMPLE-RET-01"

    def test_japanese_matching_is_not_defeated_by_lowercasing(self):
        """Triggers are matched against the original text — casefolding is
        meaningless for Japanese and dropped nothing here, but the English path
        must keep working off the lowercased copy."""
        assert retrieve_candidates("MEDICAL guideline Q&A", top_k=3)[0]["template_id"] == "SAMPLE-HCR-01"


class TestNoMatchReturnsNothing:
    def test_an_unmatched_request_yields_no_candidates(self):
        """The generic CMN entries used to be returned at score 0, so an unmatched
        request came back carrying specific template ids."""
        assert retrieve_candidates("qwptzx nonsense zzz", top_k=5) == []


class TestMockSampleCatalog:
    """The shipped catalog is mock sample data; the S-3 membership gate is exact."""

    def test_catalog_holds_only_sample_placeholder_ids(self):
        ids = [e["template_id"] for e in _CATALOG]
        assert catalog_size() == 10 and len(set(ids)) == 10
        assert all(i.startswith("SAMPLE-") for i in ids)
        assert not any(re.fullmatch(r"[A-Z]{2,5}-C[123]-\d{2,4}", i) for i in ids)

    def test_every_sample_entry_is_a_member(self):
        assert all(is_valid_template_id(e["template_id"]) for e in _CATALOG)

    def test_unknown_ids_are_rejected(self):
        assert not is_valid_template_id("SAMPLE-UNKNOWN-99")
        assert not is_valid_template_id("sample-rag-01")
        assert not is_valid_template_id("")

    def test_a_query_routes_to_a_sample_entry(self):
        top = retrieve_candidates("I need a financial disclosure report", top_k=3)
        assert top and is_valid_template_id(top[0]["template_id"])
        assert top[0]["template_id"].startswith("SAMPLE-")
