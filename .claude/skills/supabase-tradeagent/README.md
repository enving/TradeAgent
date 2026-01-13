# Skill: supabase-tradeagent

This skill provides instructions and examples for interacting with the TradeAgent database via the Supabase MCP server.

## Overview

The TradeAgent system uses Supabase for persistent storage of trades, signals, performance metrics, and parameter changes. The Supabase MCP server allows direct interaction with these tables using SQL or high-level tools.

## Tables and Schema

### `trades`
Complete log of all executed trades.
- `ticker`: Stock symbol (e.g., AAPL)
- `action`: BUY or SELL
- `quantity`: Number of shares
- `entry_price`: Price at entry
- `exit_price`: Price at exit
- `pnl`: Profit and Loss in USD
- `strategy`: 'momentum' or 'defensive'

### `signals`
Log of all generated trading signals (even if not executed).
- `signal_type`: BUY, SELL, or HOLD
- `confidence`: 0.0 to 1.0
- `strategy`: Strategy name

### `daily_performance` / `strategy_metrics`
Aggregated metrics for tracking performance over time.

### `parameter_changes`
Audit trail of automatic strategy parameter adjustments by the AdaptiveOptimizer.

## OAuth Authentication in OpenCode

The Supabase MCP server in this environment uses OAuth for authentication. 

**Connection URL**: `https://mcp.supabase.com/mcp?project_ref=fwdwdbcirkojdhzvpnsz`

### How to Authenticate:
1. When you first use a Supabase tool, the system will prompt for authentication.
2. In the OpenCode environment, this usually triggers a browser-based OAuth flow.
3. Once authorized, the session is managed by the MCP client.

## Usage Examples (via skill_mcp)

### List all tools
```json
{
  "mcp_name": "supabase",
  "tool_name": "list_tools"
}
```

### Query recent trades
```json
{
  "mcp_name": "supabase",
  "tool_name": "query",
  "arguments": "SELECT * FROM trades ORDER BY date DESC LIMIT 5"
}
```

### Check strategy performance
```json
{
  "mcp_name": "supabase",
  "tool_name": "query",
  "arguments": "SELECT strategy, SUM(pnl) as total_profit FROM trades GROUP BY strategy"
}
```

## Maintenance Tools

You can also use Supabase-specific management tools if the MCP server provides them (e.g., `list_tables`, `get_table_schema`).
