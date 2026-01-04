# Supabase Diagnostics Skill

To diagnose issues on the Raspberry Pi without SSH, use the Supabase MCP tool to query the `system_logs` table.

## Common Queries

### 1. Check for recent errors
```sql
select timestamp, module, message, trace 
from system_logs 
where level in ('ERROR', 'CRITICAL') 
order by timestamp desc 
limit 10;
```

### 2. Check system heartbeat (is it running?)
```sql
select timestamp, message 
from system_logs 
where module = 'tradeagent' 
and message like '%Heartbeat%' 
order by timestamp desc 
limit 5;
```

### 3. Check specific module activity
```sql
select timestamp, level, message 
from system_logs 
where module = 'src.agents.orchestrator' 
order by timestamp desc 
limit 20;
```

## Setup Verification
If logs are missing, ensure `database/create_logs_table.sql` was run in the Supabase SQL Editor.
