#!/usr/bin/env python3
"""Harness: COBOL evidence fixtures → evidence with deterministic 1536-d vectors.

Mirrors sql/003_evidence_seed_cobol.sql IDs/content; fills embedding (003 leaves NULL).
Reuse embed/fmt_vector from load_agent_registry (smoke hashed bag-of-tokens only).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_agent_registry import embed, fmt_vector

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Same fixtures as sql/003_evidence_seed_cobol.sql
FIXTURES = [
    {
        "evidence_id": "ev_copybook_01",
        "source_id": "src_copybook_acct",
        "source_type": "copybook",
        "document_id": "ACCTREC.cpy",
        "location": "01-ACCOUNT-BALANCE",
        "content": (
            "01 ACCOUNT-RECORD. 05 ACCOUNT-BALANCE PIC S9(9)V99. "
            "05 PAYMENT-AMOUNT PIC S9(7)V99. 05 LAST-PAYMENT-DATE PIC X(8)."
        ),
        "content_hash": "seed_copybook_01",
        "source_authority": 0.95,
        "parent_evidence": ["ev_provenance_root"],
    },
    {
        "evidence_id": "ev_cobol_src_01",
        "source_id": "src_cobol_pay",
        "source_type": "cobol_source",
        "document_id": "PAYROLL.cbl",
        "location": "PROCEDURE DIVISION / CALC-BALANCE",
        "content": (
            "COMPUTE ACCOUNT-BALANCE = ACCOUNT-BALANCE - PAYMENT-AMOUNT. "
            "IF ACCOUNT-BALANCE < ZERO THEN PERFORM OVERDRAFT-CHECK. "
            "MOVE PAYMENT-AMOUNT TO WS-LAST-PAYMENT."
        ),
        "content_hash": "seed_cobol_src_01",
        "source_authority": 0.90,
        "parent_evidence": ["ev_provenance_root"],
    },
    {
        "evidence_id": "ev_db2_schema_01",
        "source_id": "src_db2_acct",
        "source_type": "db2_schema",
        "document_id": "ACCT.DDL",
        "location": "TABLE ACCOUNT_BALANCES",
        "content": (
            "CREATE TABLE ACCOUNT_BALANCES (ACCT_ID CHAR(12), BALANCE DECIMAL(11,2), "
            "LAST_PAYMENT DECIMAL(9,2), UPDATED_TS TIMESTAMP)."
        ),
        "content_hash": "seed_db2_schema_01",
        "source_authority": 0.85,
        "parent_evidence": ["ev_provenance_root"],
    },
    {
        "evidence_id": "ev_quant_pricing_01",
        "source_id": "src_quant_report",
        "source_type": "quant_report",
        "document_id": "PRICING_Q3.pdf",
        "location": "section:monte_carlo",
        "content": (
            "Monte Carlo pricing of exotic options. Implied volatility surface and "
            "greek sensitivities. No COBOL or account balance fields."
        ),
        "content_hash": "seed_quant_pricing_01",
        "source_authority": 0.80,
        "parent_evidence": ["ev_provenance_root"],
    },
    {
        "evidence_id": "ev_lexical_lift_01",
        "source_id": "src_glossary",
        "source_type": "glossary",
        "document_id": "LEGACY-GLOSSARY.txt",
        "location": "entry:PAYMENT-BALANCE",
        "content": (
            "cobol payment balance glossary entry: PAYMENT and BALANCE fields on "
            "ACCOUNT records in legacy batch."
        ),
        "content_hash": "seed_lexical_lift_01",
        "source_authority": 0.70,
        "parent_evidence": ["ev_provenance_root"],
    },
    {
        "evidence_id": "ev_junk_low_auth",
        "source_id": "src_web_scrape",
        "source_type": "web_scrape",
        "document_id": "random-blog.html",
        "location": "body",
        "content": (
            "Someone said COBOL payment balance might work like a spreadsheet. "
            "Unverified forum post."
        ),
        "content_hash": "seed_junk_low_auth",
        "source_authority": 0.10,
        "parent_evidence": [],
    },
]


def normalize_for_embed(text: str) -> str:
    """Split identifiers on - _ / . so ACCOUNT_BALANCES → account balances tokens."""
    return re.sub(r"[-_./]+", " ", text.lower())


def embed_text_of(f: dict) -> str:
    """content + source_type + document_id + location for dense path."""
    parts = [
        f.get("source_type") or "",
        f.get("document_id") or "",
        f.get("location") or "",
        f["content"],
    ]
    return " ".join(p for p in parts if p)


def main() -> int:
    dsn = sys.argv[1] if len(sys.argv) > 1 else "dbname=david user=david host=127.0.0.1"
    if psycopg2 is None:
        print("psycopg2 missing", file=sys.stderr)
        return 2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        for f in FIXTURES:
            et = normalize_for_embed(embed_text_of(f))
            emb = fmt_vector(embed(et))
            cur.execute(
                """
                INSERT INTO evidence (
                  evidence_id, source_id, source_type, document_id, location,
                  content, content_hash, embedding, source_authority, parent_evidence
                ) VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s::vector, %s, %s::text[]
                )
                ON CONFLICT (evidence_id) DO UPDATE SET
                  source_id = EXCLUDED.source_id,
                  source_type = EXCLUDED.source_type,
                  document_id = EXCLUDED.document_id,
                  location = EXCLUDED.location,
                  content = EXCLUDED.content,
                  content_hash = EXCLUDED.content_hash,
                  embedding = EXCLUDED.embedding,
                  source_authority = EXCLUDED.source_authority,
                  parent_evidence = EXCLUDED.parent_evidence
                """,
                (
                    f["evidence_id"],
                    f["source_id"],
                    f["source_type"],
                    f["document_id"],
                    f["location"],
                    f["content"],
                    f["content_hash"],
                    emb,
                    f["source_authority"],
                    f["parent_evidence"],
                ),
            )
        cur.execute(
            "SELECT count(*) FILTER (WHERE embedding IS NOT NULL), count(*) FROM evidence"
        )
        with_emb, total = cur.fetchone()
    conn.close()
    print(f"loaded_evidence={total} with_embedding={with_emb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
