create index if not exists chunks_embeddings_hnsw on
 chunks using hnsw (embedding vector_cosine_ops)
  with (m=16, ef_construction=128);


create index chunks_content_fts
  on chunks using gin (to_tsvector('english', content));

  create index chunks_tenant_idx on chunks (tenant_id);




