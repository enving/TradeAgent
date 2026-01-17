# Development Rules - TradeAgent

## General Best Practices
- **Safety First**: NEVER commit `.env` files or hardcode API keys.
- **Asyncio**: Use `async/await` for all network and database operations to prevent blocking the event loop.
- **Typing**: Use type hints (PEP 484) for all new functions and classes.
- **Logging**: Use the system logger. Critical errors should also be logged to Supabase (`system_logs` table).

## Documentation Rules
- **tasks.json**: Update `.opencode/tasks.json` after every significant change.
- **Checkpointing**: Use `/checkpoint` (or follow the protocol) when handing off to a new agent.
- **Comments**: Focus on *why*, not *what*. Keep code clean and self-documenting.

## Testing Standards
- **Local Testing**: Always test locally before pushing to `main`.
- **Integration Tests**: Use `test_integration.py` for full system checks.
- **Mocking**: Mock external APIs (Alpaca, NewsAPI) in unit tests.

## Git Workflow
- **Commit Messages**: Use descriptive, prefix-based messages (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
- **Pi Deployment**: Push to `main` for automatic deployment to Raspberry Pi (monitored by cron).

## Agent specific rules
- **Lies IMMER .opencode/tasks.json ZUERST**
- **Validiere gegen tasks.schema.json**
- **Markiere NUR Tasks als completed die du verifiziert hast**
- **Reviews können NUR vom NÄCHSTEN Agent gemacht werden, nicht vom gleichen**
- **Prüfe ob Dateien/Funktionen existieren bevor du sie referenzierst**
- **Update tasks.json nach jeder signifikanten Änderung**
