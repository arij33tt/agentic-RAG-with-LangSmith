-- ============================================================
-- 0006_audit_log_table.sql
-- Records every query/response for debugging, compliance,
-- and security monitoring.
-- ============================================================

create table audit_log (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  user_id uuid,                          -- who asked (nullable if system/internal call)
  query_text text not null,              -- the raw question asked
  retrieved_chunk_ids uuid[],            -- array of chunk ids that were retrieved
  response_text text,                    -- the final answer given
  latency_ms int,                        -- how long the whole request took
  flagged boolean not null default false, -- true if a security guard caught something
  flagged_reason text,                   -- optional: why it was flagged
  created_at timestamptz not null default now()
);

-- Fast lookups by tenant and time (for dashboards/monitoring)
create index audit_log_tenant_created_idx
  on audit_log (tenant_id, created_at desc);

-- Fast lookup for flagged/security-review rows
create index audit_log_flagged_idx
  on audit_log (flagged) where flagged = true;

-- RLS: tenants can only see their own audit history
alter table audit_log enable row level security;

create policy "tenant_isolation_select_audit_log"
  on audit_log for select
  using (tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid);

create policy "tenant_isolation_insert_audit_log"
  on audit_log for insert
  with check (tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid);