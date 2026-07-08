-- ============================================================
-- 0005_rls_policies.sql
-- Enforces tenant isolation at the database level for
-- documents and chunks. Even a buggy or compromised app-level
-- query cannot leak data across tenants once these are active.
-- ============================================================

-- ============================
-- RLS for the documents table
-- ============================

alter table documents enable row level security;

create policy "tenant_isolation_select_documents"
  on documents for select
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);


create policy "tenant_isolation_insert_documents"
  on documents for insert
  with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);


create policy "tenant_isolation_update_documents"
on documents for update
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
  with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

  create policy "tenant_isolation_delete_documents"
  on documents for delete
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);


-- ==============================================================

alter table chunks enable row level security;

create policy "tenant_isolation_select_chunks"
  on chunks for select
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

create policy "tenant_isolation_insert_chunks"
  on chunks for insert
  with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

create policy "tenant_isolation_update_chunks"
  on chunks for update
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
  with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

create policy "tenant_isolation_delete_chunks"
  on chunks for delete
  using (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);