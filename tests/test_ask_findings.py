"""Tests for Ask Your Findings' retrieval layer (final.md B4).

Only the pure retrieval logic — tokenize, build_corpus, retrieve — is tested here. No network
call is made; call_claude() is exercised manually (see scripts/ask_findings.py's own docstring)
since it requires a live API key and this suite must run without one.

The property that matters most: **retrieval is a real gate, not a formality.** A question with no
matching evidence must retrieve nothing, because scripts/ask_findings.py's main() only calls the
API when retrieved is non-empty — the structural enforcement of "never answer from general
knowledge" lives in that empty-list short-circuit, not in a prompt instruction alone.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ask_findings as af  # noqa: E402


SAMPLE_DATA = {
    "records": [
        {"registry_id": "reg_0001", "brand_or_program": "Sonnet", "legal_underwriter": "Sonnet Insurance Company",
         "status": "blocked", "reason_code": "licence_number_required_hypothetical_profile",
         "distinct_rate_source_id": "rs_0001", "automation_notes": "Mandatory licence number field"},
        {"registry_id": "reg_0100", "brand_or_program": "Rates.ca", "legal_underwriter": "n/a",
         "status": "blocked", "reason_code": "RC_ACCESS_CONTROL",
         "distinct_rate_source_id": "rs_0020", "automation_notes": "Cloudflare managed challenge"},
    ],
    "results": [
        {"route_id": "rt_reg_0001", "registry_id": "reg_0001", "status": "blocked",
         "reason_code": "licence_number_required_hypothetical_profile",
         "variance_from_benchmark": [], "evidence": {"artifact_cids": ["cid:sha256-abc"]}},
    ],
    "evidence": {"artifacts": [
        {"cid": "cid:sha256-abc", "route_id": "rt_reg_0001", "source": "https://sonnet.example.com",
         "text_excerpt": "Driver's licence number. Case sensitive. Mandatory field."},
    ]},
    "frontier": {"ladder": [
        {"unlock": "run_under_operator_profile", "label": "Run under the operator's own profile",
         "records": [{"registry_id": "reg_0001", "brand": "Sonnet"}]},
    ]},
}


class TestTokenize(unittest.TestCase):
    def test_lowercases_and_strips_stopwords(self):
        tokens = af.tokenize("Which Rate Sources Stopped At A Licence Requirement?")
        self.assertIn("licence", tokens)
        self.assertIn("requirement", tokens)
        self.assertNotIn("which", tokens)
        self.assertNotIn("at", tokens)

    def test_short_tokens_are_dropped(self):
        self.assertNotIn("to", af.tokenize("go to the store"))


class TestBuildCorpus(unittest.TestCase):
    def test_every_source_type_is_represented(self):
        corpus = af.build_corpus(SAMPLE_DATA)
        kinds = {row["kind"] for row in corpus}
        self.assertEqual(kinds, {"registry_record", "result", "evidence", "frontier_rung"})

    def test_citations_are_the_checkable_identifiers(self):
        corpus = af.build_corpus(SAMPLE_DATA)
        evidence_row = next(r for r in corpus if r["kind"] == "evidence")
        self.assertEqual(evidence_row["citation"], "cid:sha256-abc")
        registry_row = next(r for r in corpus if r["kind"] == "registry_record" and r["id"] == "reg_0001")
        self.assertEqual(registry_row["citation"], "reg_0001")


class TestRetrieve(unittest.TestCase):
    def setUp(self):
        self.corpus = af.build_corpus(SAMPLE_DATA)

    def test_relevant_question_retrieves_matching_rows(self):
        results = af.retrieve("Which rate sources stopped at a licence requirement?", self.corpus)
        self.assertTrue(any("reg_0001" in r["citation"] or r["id"] == "reg_0001" for r in results))

    def test_unrelated_question_retrieves_nothing(self):
        """The structural gate: this is what makes main() refuse to call the API at all."""
        results = af.retrieve("What is the capital of France?", self.corpus)
        self.assertEqual(results, [])

    def test_results_are_ranked_by_overlap_not_insertion_order(self):
        results = af.retrieve("access control Cloudflare Rates.ca", self.corpus)
        self.assertTrue(results)
        self.assertIn("reg_0100", str(results[0]))


if __name__ == "__main__":
    unittest.main()
