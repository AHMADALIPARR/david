-- Synthetic David — product hybrid retrieve against `evidence`
-- Schema: sql/001_agent_and_evidence_indexes.sql
--
-- Parameters (bind as $1..$n; comments document intent):
--   $1  query_embedding   vector(1536)   -- dense cosine query
--   $2  query_text         text           -- lexical plainto_tsquery input
--   $3  source_types       text[]         -- optional; NULL / empty = no filter
--   $4  min_authority      real           -- provenance floor on source_authority
--   $5  require_parent     boolean        -- if true, parent_evidence must be non-empty
--   $6  top_k              int            -- LIMIT
--
-- Score weights (deterministic merge / rerank — no dense floor):
--   dense     = 1 - (embedding <=> $1)     -- cosine similarity from cosine distance
--   lexical   = ts_rank_cd(content_tsv, plainto_tsquery('english', $2))
--   authority = source_authority
--   penalty   = CASE WHEN $5 AND cardinality(parent_evidence)=0 THEN 1.0 ELSE 0.0 END
--   score     = dense + lexical + authority - penalty
--
-- ORDER BY score DESC, evidence_id  (stable tie-break)
-- Hybrid note: weak dense + strong lexical can still rank (no hard dense floor).

SELECT
  evidence_id,
  source_id,
  source_type,
  document_id,
  location,
  content,
  content_hash,
  source_authority,
  parent_evidence,
  -- component scores for retrieval_metadata / provenance
  (1.0 - (embedding <=> $1::vector))                         AS dense,     -- weight 1.0
  ts_rank_cd(content_tsv, plainto_tsquery('english', $2))    AS lexical,   -- weight 1.0
  source_authority                                           AS authority, -- weight 1.0
  CASE
    WHEN COALESCE($5::boolean, false)
         AND cardinality(parent_evidence) = 0
    THEN 1.0
    ELSE 0.0
  END                                                        AS parent_penalty, -- weight 1.0
  (
    (1.0 - (embedding <=> $1::vector))
    + ts_rank_cd(content_tsv, plainto_tsquery('english', $2))
    + source_authority
    - CASE
        WHEN COALESCE($5::boolean, false)
             AND cardinality(parent_evidence) = 0
        THEN 1.0
        ELSE 0.0
      END
  )                                                          AS score
FROM evidence
WHERE
  -- provenance: authority floor
  source_authority >= COALESCE($4::real, 0.0)
  -- optional metadata: source_type = ANY(...)
  AND (
    $3::text[] IS NULL
    OR cardinality($3::text[]) = 0
    OR source_type = ANY ($3::text[])
  )
  -- optional provenance: require non-empty parent_evidence
  AND (
    NOT COALESCE($5::boolean, false)
    OR cardinality(parent_evidence) > 0
  )
  -- lexical gate (rows with zero tsquery match still allowed via dense path:
  -- keep OR so weak-dense / strong-lexical AND strong-dense / weak-lexical both survive)
  AND (
    content_tsv @@ plainto_tsquery('english', $2)
    OR embedding IS NOT NULL
  )
ORDER BY score DESC, evidence_id
LIMIT GREATEST(COALESCE($6::int, 10), 0);

-- Dense-only sketch (reference):
--   ORDER BY embedding <=> $1
-- Lexical-only sketch (reference):
--   WHERE content_tsv @@ plainto_tsquery('english', $2)
