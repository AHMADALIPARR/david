-- Synthetic David — COBOL modernization seed fixture (mirrors j/evidence.ijs)
-- embedding left NULL until an encoder exists; content/authority/parent drive smoke filters.
-- Fixture evidence_ids match pure-J seed corpus.

INSERT INTO evidence (
  evidence_id, source_id, source_type, document_id, location,
  content, content_hash, embedding, source_authority, parent_evidence
) VALUES
(
  'ev_copybook_01',
  'src_copybook_acct',
  'copybook',
  'ACCTREC.cpy',
  '01-ACCOUNT-BALANCE',
  '01 ACCOUNT-RECORD. 05 ACCOUNT-BALANCE PIC S9(9)V99. 05 PAYMENT-AMOUNT PIC S9(7)V99. 05 LAST-PAYMENT-DATE PIC X(8).',
  'seed_copybook_01',
  NULL,  -- vector(1536) when encoder exists; J smoke uses dim-8 stand-in
  0.95,
  ARRAY['ev_provenance_root']
),
(
  'ev_cobol_src_01',
  'src_cobol_pay',
  'cobol_source',
  'PAYROLL.cbl',
  'PROCEDURE DIVISION / CALC-BALANCE',
  'COMPUTE ACCOUNT-BALANCE = ACCOUNT-BALANCE - PAYMENT-AMOUNT. IF ACCOUNT-BALANCE < ZERO THEN PERFORM OVERDRAFT-CHECK. MOVE PAYMENT-AMOUNT TO WS-LAST-PAYMENT.',
  'seed_cobol_src_01',
  NULL,
  0.90,
  ARRAY['ev_provenance_root']
),
(
  'ev_db2_schema_01',
  'src_db2_acct',
  'db2_schema',
  'ACCT.DDL',
  'TABLE ACCOUNT_BALANCES',
  'CREATE TABLE ACCOUNT_BALANCES (ACCT_ID CHAR(12), BALANCE DECIMAL(11,2), LAST_PAYMENT DECIMAL(9,2), UPDATED_TS TIMESTAMP).',
  'seed_db2_schema_01',
  NULL,
  0.85,
  ARRAY['ev_provenance_root']
),
(
  'ev_quant_pricing_01',
  'src_quant_report',
  'quant_report',
  'PRICING_Q3.pdf',
  'section:monte_carlo',
  'Monte Carlo pricing of exotic options. Implied volatility surface and greek sensitivities. No COBOL or account balance fields.',
  'seed_quant_pricing_01',
  NULL,
  0.80,
  ARRAY['ev_provenance_root']
),
(
  'ev_lexical_lift_01',
  'src_glossary',
  'glossary',
  'LEGACY-GLOSSARY.txt',
  'entry:PAYMENT-BALANCE',
  'cobol payment balance glossary entry: PAYMENT and BALANCE fields on ACCOUNT records in legacy batch.',
  'seed_lexical_lift_01',
  NULL,
  0.70,
  ARRAY['ev_provenance_root']
),
(
  'ev_junk_low_auth',
  'src_web_scrape',
  'web_scrape',
  'random-blog.html',
  'body',
  'Someone said COBOL payment balance might work like a spreadsheet. Unverified forum post.',
  'seed_junk_low_auth',
  NULL,
  0.10,
  ARRAY[]::text[]
)
ON CONFLICT (evidence_id) DO NOTHING;
