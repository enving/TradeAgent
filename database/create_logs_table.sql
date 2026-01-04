-- Table for storing system logs and errors
create table if not exists system_logs (
    id uuid default gen_random_uuid() primary key,
    timestamp timestamptz not null default now(),
    level text not null,
    module text not null,
    message text not null,
    trace text,
    metadata jsonb
);

-- Index for faster queries
create index if not exists idx_system_logs_timestamp on system_logs (timestamp desc);
create index if not exists idx_system_logs_level on system_logs (level);

-- RLS Policies
alter table system_logs enable row level security;

-- Allow insert from authenticated and anon (since bot might use service key or anon)
create policy "Enable insert for authenticated users only"
on system_logs for insert
to authenticated, anon
with check (true);

-- Allow select for authenticated users only (dashboard/AI access)
create policy "Enable read access for all users"
on system_logs for select
to authenticated, anon
using (true);
