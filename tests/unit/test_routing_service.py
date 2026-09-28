"""Confidence: a recommendation is worth only as much as what it rests on."""

from src.services.routing_service import DEFAULT_CONFIDENCE_THRESHOLD, classify_intent, recommend


def _c(tid: str, score: int) -> dict:
    return {"template_id": tid, "industry": "CMN", "pattern": "VectorRAG", "score": score}


class TestConfidenceReflectsEvidence:
    def test_a_single_incidental_hit_is_not_certainty(self):
        """Sharing out the total score gave a lone one-word match the whole mass and
        reported 1.0 — the strongest possible claim from the weakest possible evidence."""
        assert classify_intent("q", [_c("SAMPLE-DOCGEN-01", 1)])["confidence"] < DEFAULT_CONFIDENCE_THRESHOLD

    def test_a_well_evidenced_unrivalled_match_is_certain(self):
        assert classify_intent("q", [_c("SAMPLE-RET-01", 4)])["confidence"] == 1.0

    def test_a_tie_is_reported_as_unresolved(self):
        """Two equally-plausible matches must not be settled by list order."""
        candidates = [_c("SAMPLE-RET-01", 3), _c("SAMPLE-FIN-01", 3)]
        assert classify_intent("q", candidates)["confidence"] < DEFAULT_CONFIDENCE_THRESHOLD


class TestNoMatch:
    def test_nothing_matched_names_no_template(self):
        rec = recommend([], {"confidence": 0.0})
        assert rec["template_id"] is None
        assert rec["top_candidates"] == []
        assert "Describe what the agent should do" in rec["rationale"]
