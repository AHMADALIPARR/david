"""Tests for in-memory hybrid evidence retrieval."""

from __future__ import annotations

import unittest

from evidence.retrieve import (
    COBOL_BALANCE_QUERY,
    COBOL_BALANCE_QUERY_VEC,
    EvidenceIndex,
    empty_bundle,
    lexical_score,
    retrieve,
    seed_cobol_corpus,
)


class RetrieveTests(unittest.TestCase):
    def setUp(self):
        self.index = EvidenceIndex(seed_cobol_corpus())
        self.query = COBOL_BALANCE_QUERY
        self.qvec = COBOL_BALANCE_QUERY_VEC

    def test_cobol_balance_prefers_legacy_not_quant(self):
        bundle = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            min_authority=0.5,
            require_parent_evidence=True,
            top_k=5,
        )
        ids = [s["evidence_id"] for s in bundle["sources"]]
        self.assertTrue(ids, "expected non-empty sources")
        # Top hit must not be the quant pricing chunk
        self.assertNotEqual(ids[0], "ev_quant_pricing_01")
        # COBOL / copybook / schema evidence should appear
        self.assertTrue(
            any(
                i in ids
                for i in ("ev_copybook_01", "ev_cobol_src_01", "ev_db2_schema_01")
            ),
            f"expected legacy evidence in {ids}",
        )
        # Quant must not be the top hit; preferably absent from top-3 when
        # authority + dense favor legacy chunks
        top3 = ids[:3]
        self.assertNotIn("ev_quant_pricing_01", top3)

    def test_provenance_authority_drops_junk(self):
        # Without filter, junk may score on lexical overlap
        open_bundle = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            min_authority=0.0,
            require_parent_evidence=False,
            top_k=10,
        )
        open_ids = {s["evidence_id"] for s in open_bundle["sources"]}
        self.assertIn("ev_junk_lowauth_01", open_ids)

        filtered = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            min_authority=0.5,
            require_parent_evidence=True,
            top_k=10,
        )
        filt_ids = {s["evidence_id"] for s in filtered["sources"]}
        self.assertNotIn("ev_junk_lowauth_01", filt_ids)
        # Every returned source has provenance fields
        for src in filtered["sources"]:
            self.assertIn("content_hash", src)
            self.assertIn("source_authority", src)
            self.assertIn("parent_evidence", src)
            self.assertTrue(src["parent_evidence"])

    def test_hybrid_lexical_can_lift_weak_dense(self):
        """Rule: score = dense + lexical + authority - penalties (no dense floor).

        ev_lexical_lift_01 has weak cosine vs the COBOL query vector but strong
        token overlap on cobol/payment/balance, so it can appear in results.
        """
        # Dense-only ranking of lexical_lift should be poor
        from evidence.retrieve import cosine_similarity

        lift = self.index._by_id["ev_lexical_lift_01"]
        dense_lift = cosine_similarity(self.qvec, lift.embedding)
        dense_copy = cosine_similarity(
            self.qvec, self.index._by_id["ev_copybook_01"].embedding
        )
        self.assertLess(dense_lift, dense_copy)
        self.assertLess(dense_lift, 0.55)  # weak dense

        lex = lexical_score(self.query, lift.content)
        self.assertGreaterEqual(lex, 0.5)  # strong lexical

        bundle = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            min_authority=0.5,
            require_parent_evidence=True,
            top_k=10,
        )
        ids = [s["evidence_id"] for s in bundle["sources"]]
        self.assertIn(
            "ev_lexical_lift_01",
            ids,
            "lexical-strong / dense-weak chunk should appear under hybrid score",
        )
        # Confirm retrieval_metadata records both components
        meta = {
            m["evidence_id"]: m for m in bundle["retrieval_metadata"]
        }
        self.assertIn("ev_lexical_lift_01", meta)
        self.assertGreaterEqual(meta["ev_lexical_lift_01"]["lexical"], 0.5)
        self.assertLess(meta["ev_lexical_lift_01"]["dense"], 0.55)

    def test_empty_query_returns_empty_bundle(self):
        bundle = retrieve("", query_embedding=self.qvec, index=self.index)
        self.assertEqual(bundle, empty_bundle())
        self.assertEqual(bundle["sources"], [])
        self.assertEqual(bundle["facts"], [])

    def test_no_match_returns_empty_bundle(self):
        # Metadata filter that matches nothing
        bundle = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            source_types=["nonexistent_type"],
            top_k=5,
        )
        self.assertEqual(bundle["sources"], [])
        self.assertEqual(bundle["facts"], [])
        self.assertEqual(bundle["provenance"], [])
        self.assertEqual(bundle["retrieval_metadata"], [])

    def test_bundle_shape_has_provenance(self):
        bundle = retrieve(
            self.query,
            query_embedding=self.qvec,
            index=self.index,
            min_authority=0.5,
            top_k=3,
        )
        for key in ("facts", "sources", "provenance", "retrieval_metadata"):
            self.assertIn(key, bundle)
        self.assertEqual(len(bundle["sources"]), len(bundle["provenance"]))
        # No bare text: each source carries provenance fields
        for src in bundle["sources"]:
            self.assertTrue(src.get("content_hash"))
            self.assertIsNotNone(src.get("source_authority"))


if __name__ == "__main__":
    unittest.main()
