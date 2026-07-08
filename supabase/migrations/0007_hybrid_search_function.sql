-- ============================================================
-- 0007_hybrid_search_function.sql
-- RPC function: combines vector similarity search + keyword
-- (full-text) search using Reciprocal Rank Fusion (RRF).
-- Called from Python via: supabase.rpc("match_chunks_hybrid", {...})
-- ============================================================

create or replace function match_chunks_hybrid(
  query_embedding vector(768),      -- match your embedding dimension
  query_text text,
  filter_tenant_id uuid,
  match_count int default 10
)
returns table (
  chunk_id uuid,
  content text,
  document_id uuid,
  rrf_score float
)
language sql
as $$
  with vector_results as (
    select
      id as chunk_id,
      row_number() over (order by embedding <=> query_embedding) as rank
    from chunks
    where tenant_id = filter_tenant_id
    order by embedding <=> query_embedding
    limit 50
  ),
  keyword_results as (
    select
      id as chunk_id,
      row_number() over (
        order by ts_rank(to_tsvector('english', content),
                          plainto_tsquery('english', query_text)) desc
      ) as rank
    from chunks
    where tenant_id = filter_tenant_id
      and to_tsvector('english', content) @@ plainto_tsquery('english', query_text)
    limit 50
  ),
  fused as (
    select
      coalesce(v.chunk_id, k.chunk_id) as chunk_id,
      coalesce(1.0 / (60 + v.rank), 0.0) + coalesce(1.0 / (60 + k.rank), 0.0) as rrf_score
    from vector_results v
    full outer join keyword_results k on v.chunk_id = k.chunk_id
  )
  select
    c.id as chunk_id,
    c.content,
    c.document_id,
    f.rrf_score
  from fused f
  join chunks c on c.id = f.chunk_id
  order by f.rrf_score desc
  limit match_count;
$$;