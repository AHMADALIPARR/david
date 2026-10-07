-- Synthetic David: separate AGENT and EVIDENCE vector spaces (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- AGENT INDEX — "Who should work?"
CREATE TABLE IF NOT EXISTS agent_registry (
  agent_id            text PRIMARY KEY,
  domain              text NOT NULL,
  capabilities        text[] NOT NULL DEFAULT '{}',
  languages           text[] NOT NULL DEFAULT '{}',
  input_types         text[] NOT NULL DEFAULT '{}',
  output_types        text[] NOT NULL DEFAULT '{}',
  required_evidence   text[] NOT NULL DEFAULT '{}',
  permissions         text[] NOT NULL DEFAULT '{}',
  risk_class          text NOT NULL CHECK (risk_class IN ('low','medium','high','critical')),
  dependencies        text[] NOT NULL DEFAULT '{}',
  execution_endpoint  text NOT NULL,
  control_plane       boolean NOT NULL DEFAULT false,
  embed_text          text NOT NULL,
  embedding           vector(1536),
  historical_success  real NOT NULL DEFAULT 0.0,
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_registry_embedding_hnsw
  ON agent_registry USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS agent_registry_capabilities_gin
  ON agent_registry USING gin (capabilities);

-- EVIDENCE INDEX — "What evidence should they use?"
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id       text PRIMARY KEY,
  source_id         text NOT NULL,
  source_type       text NOT NULL,
  document_id       text,
  location          text,
  content           text NOT NULL,
  content_hash      text NOT NULL,
  embedding         vector(1536),
  content_tsv       tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  source_authority  real NOT NULL DEFAULT 0.5,
  retrieved_by      text,
  retrieval_score   real,
  parent_evidence   text[] NOT NULL DEFAULT '{}',
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS evidence_embedding_hnsw
  ON evidence USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS evidence_content_tsv_gin
  ON evidence USING gin (content_tsv);

-- Hybrid evidence retrieval sketch:
-- dense:  ORDER BY embedding <=> $query_vec
-- lexical: content_tsv @@ plainto_tsquery('english', $q)
-- then metadata + provenance filters, then rerank.
