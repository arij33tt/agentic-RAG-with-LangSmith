create table if not exists documents(

    id uuid primary key default gen_random_uuid(),

    tenant_id uuid not null, -- multi tenant isolation 

    title text not null,

    source_uri text,

    source_type text not null, -- pdf or html or txt 

    checksum text not null , -- sha256 checksum of the document de duplicate detection
   
    status text not null default 'pending', -- pending, processed, failed
    
    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz default now(),

    updated_at timestamptz default now()

    
);


-- creating index for tenant_id and checksum for faster lookups instead of full table scan 

create unique index if not exists idx_documents_tenant_checksum on documents (tenant_id, checksum);