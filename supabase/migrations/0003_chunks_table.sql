create table chunks(
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    tenant_id uuid not null,
    content text not null,
    embedding vector(1024),
    token_count int,
    chunk_index int not null ,
    parent_chunk_id uuid,
    section_path text,
    metadata jsonb  default '{}'::jsonb,
    created_at timestamptz default now()
);