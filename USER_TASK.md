# TradeAgent - AI/LLM Integration Aufgaben

**Erstellt:** 2025-11-19
**Status:** Empfehlungen für zukünftige LLM-Integration

---

## ❓ Frage: Welches Sprachmodell wird im System genutzt?

### ⚠️ ANTWORT: **KEINS!**

Das aktuelle TradeAgent System ist **zu 100% deterministisch** und verwendet **KEINE Sprachmodelle (LLMs)** für Trading-Entscheidungen.

**Warum kein LLM für Trading?**

1. **Regulierung** - Finanzaufsicht erfordert nachvollziehbare, deterministische Entscheidungen
2. **Zuverlässigkeit** - LLMs können halluzinieren, Geld-Verluste wären inakzeptabel
3. **Latenz** - Trading erfordert Millisekunden-Entscheidungen, LLM-Calls sind zu langsam
4. **Kosten** - Hunderte API-Calls pro Tag wären teuer
5. **Auditierbarkeit** - Mathematische Formeln sind besser dokumentierbar als LLM-Outputs

---

## 📊 Aktuelles System: 100% Regelbasiert

### Trading-Entscheidungen erfolgen durch:

**Defensive Core Strategy:**
```python
# Pure Mathematik - KEIN LLM
target_value = portfolio_value * 0.25  # 25% für VTI
diff = target_value - current_value
if diff > 100:
    action = "BUY" if diff > 0 else "SELL"
```

**Momentum Strategy:**
```python
# Technische Indikatoren - KEIN LLM
if (50 < rsi < 70 and
    macd_histogram > 0 and
    price > sma20 and
    volume_ratio > 1.0):
    signal = "BUY"
```

**Risk Management:**
```python
# Hard-coded Limits - KEIN LLM
MAX_POSITIONS = 5
MAX_POSITION_SIZE_PCT = 0.10
DAILY_LOSS_LIMIT_PCT = 0.03
```

---

## 🤖 Wo KÖNNTE ein LLM sinnvoll sein?

Es gibt **sinnvolle nicht-Trading Use Cases** für LLMs:

### ✅ SINNVOLL: LLM für Analyse & Reporting

#### 1. Sentiment Analysis
**Use Case:** News & Social Media Sentiment als zusätzlicher Indikator (NICHT für direkte Trades!)

```python
# Beispiel: Sentiment Score als Filter
sentiment = llm_analyze_news(ticker)
if sentiment < -0.5:
    logger.warning(f"Negative sentiment for {ticker}, consider skipping")
    # Aber: Final decision bleibt mathematisch!
```

**Vorteile:**
- Frühwarnung bei negativen News
- Ergänzt technische Indikatoren
- Kann Trades verhindern (nicht auslösen!)

#### 2. Trade Explanations
**Use Case:** Generiere natürlichsprachige Erklärungen für Trades

```python
# Beispiel: Trade Kommentierung
trade_explanation = llm_explain_trade(
    ticker="AAPL",
    action="BUY",
    reason="RSI=62, MACD>0, Volume 1.8x avg",
    portfolio_context=portfolio
)
# Output: "Bought AAPL due to strong bullish momentum..."
```

**Vorteile:**
- Bessere User Experience
- Audit Trail mit natürlicher Sprache
- Einfacher für regulatorische Reports

#### 3. Portfolio Kommentare
**Use Case:** Wöchentliche Portfolio-Zusammenfassung in natürlicher Sprache

```python
# Beispiel: Weekly Report Narrative
narrative = llm_generate_weekly_summary(
    trades=weekly_trades,
    performance=weekly_performance,
    market_context=market_data
)
# Output: "This week showed strong momentum in tech..."
```

**Vorteile:**
- Professionelle Reports
- Erkenntnisse in natürlicher Sprache
- Email-freundliches Format

#### 4. Risk Assessment Narrative
**Use Case:** Erkläre Portfolio-Risiken in natürlicher Sprache

```python
# Beispiel: Risk Explanation
risk_report = llm_analyze_risk(
    positions=current_positions,
    correlations=correlation_matrix,
    market_conditions=market_state
)
# Output: "Your portfolio has high concentration in tech..."
```

**Vorteile:**
- Risiko-Bewusstsein erhöhen
- Bessere Kommunikation mit Stakeholdern
- Proaktive Warnungen

#### 5. Market Regime Detection
**Use Case:** Identifiziere Marktphasen via News/Reports

```python
# Beispiel: Market Regime
regime = llm_detect_market_regime(
    news_articles=recent_news,
    fed_statements=fed_data,
    analyst_reports=reports
)
# Output: {"regime": "risk_off", "confidence": 0.85}
```

**Vorteile:**
- Strategie-Anpassung (mehr defensive Allocation bei Risk-Off)
- Frühwarnung vor Krisen
- Ergänzt quantitative Signale

---

## ❌ NICHT SINNVOLL: LLM für Trading-Entscheidungen

### NIEMALS LLM verwenden für:
- ❌ Entry/Exit Signale
- ❌ Position Sizing
- ❌ Stop-Loss/Take-Profit Levels
- ❌ Portfolio Rebalancing
- ❌ Risk Limits

**Grund:** Zu unzuverlässig, zu langsam, nicht regulierungskonform

---

## 📋 Empfohlene LLM-Integration Tasks

### Phase 1: Reporting & Explanations (Low Risk)

#### Task 1.1: Trade Explanation Generator
**Priorität:** Hoch
**Aufwand:** 2-3 Tage
**LLM:** Claude Sonnet 4.5 (via Anthropic API)

```python
# Zu implementieren: src/llm/trade_explainer.py

import anthropic

async def explain_trade(trade: Trade, portfolio: Portfolio) -> str:
    """Generate natural language explanation for a trade.

    Args:
        trade: The executed trade
        portfolio: Current portfolio state

    Returns:
        Human-readable trade explanation
    """
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    prompt = f"""
    You are a financial analyst. Explain this trade:

    Ticker: {trade.ticker}
    Action: {trade.action}
    Quantity: {trade.quantity}
    Price: ${trade.entry_price}
    Strategy: {trade.strategy}

    Technical Context:
    - RSI: {trade.rsi}
    - MACD: {trade.macd_histogram}
    - Volume Ratio: {trade.volume_ratio}

    Portfolio Context:
    - Portfolio Value: ${portfolio.portfolio_value}
    - Cash: ${portfolio.cash}

    Provide a 2-3 sentence explanation suitable for a trade log.
    """

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

**Integration Point:**
```python
# In src/main.py nach Trade-Ausführung
explanation = await explain_trade(trade, portfolio)
await SupabaseClient.log_trade_explanation(trade.id, explanation)
```

**Kosten-Schätzung:** ~$0.10-0.20 pro Tag (10-20 Trades @ ~500 tokens pro Call)

---

#### Task 1.2: Weekly Report Generator
**Priorität:** Mittel
**Aufwand:** 1-2 Tage
**LLM:** Claude Sonnet 4.5

```python
# Zu implementieren: src/llm/report_generator.py

async def generate_weekly_narrative(
    trades: list[Trade],
    performance: WeeklyPerformance,
    market_data: dict
) -> str:
    """Generate natural language weekly summary."""
    # Ähnlich wie Task 1.1, aber für Weekly Report
```

**Integration Point:**
```python
# In src/core/performance_analyzer.py
narrative = await generate_weekly_narrative(weekly_trades, performance, market_data)
await SupabaseClient.log_weekly_narrative(narrative)
# Email to user
```

---

### Phase 2: Sentiment Analysis (Medium Risk)

#### Task 2.1: News Sentiment Analyzer
**Priorität:** Mittel
**Aufwand:** 3-5 Tage
**LLM:** Claude Sonnet 4.5 + News API

```python
# Zu implementieren: src/llm/sentiment_analyzer.py

from newsapi import NewsApiClient

async def analyze_ticker_sentiment(ticker: str) -> dict:
    """Analyze news sentiment for a ticker.

    Returns:
        {
            "sentiment_score": -1.0 to 1.0,
            "confidence": 0.0 to 1.0,
            "summary": "Brief explanation",
            "articles_analyzed": 10
        }
    """
    # 1. Fetch recent news (NewsAPI, Alpha Vantage News, etc.)
    news_api = NewsApiClient(api_key=config.NEWS_API_KEY)
    articles = news_api.get_everything(
        q=ticker,
        language='en',
        sort_by='publishedAt',
        page_size=10
    )

    # 2. Analyze sentiment with Claude
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    articles_text = "\n\n".join([
        f"Title: {a['title']}\nDescription: {a['description']}"
        for a in articles['articles']
    ])

    prompt = f"""
    Analyze the sentiment of these news articles about {ticker}.

    {articles_text}

    Provide:
    1. Sentiment score (-1.0 = very negative, 0 = neutral, 1.0 = very positive)
    2. Confidence (0.0 to 1.0)
    3. Brief 1-sentence summary

    Format as JSON.
    """

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

**Integration Point:**
```python
# In src/strategies/momentum_trading.py
# BEFORE executing trade
sentiment = await analyze_ticker_sentiment(signal.ticker)

if sentiment["sentiment_score"] < -0.5:
    logger.warning(f"Negative sentiment for {signal.ticker}: {sentiment['summary']}")
    # Optional: Skip this trade
    continue
```

**Wichtig:** Sentiment ist ein **Filter**, NICHT der Hauptsignal-Geber!

**Kosten-Schätzung:**
- News API: $449/month (Professional Plan für realtime data)
- Anthropic API: ~$0.50-1.00 pro Tag (10 Analysen @ ~2000 tokens pro Call)

---

#### Task 2.2: Market Regime Detector
**Priorität:** Niedrig
**Aufwand:** 5-7 Tage
**LLM:** Claude Opus 4 (für komplexere Analyse)

```python
# Zu implementieren: src/llm/regime_detector.py

async def detect_market_regime() -> dict:
    """Detect current market regime (risk-on, risk-off, etc.)

    Returns:
        {
            "regime": "risk_on" | "risk_off" | "transitioning" | "uncertain",
            "confidence": 0.0 to 1.0,
            "reasoning": "Explanation",
            "recommended_allocation": {
                "defensive_core_pct": 0.5,  # May increase to 0.7 in risk-off
                "momentum_pct": 0.5  # May decrease to 0.3 in risk-off
            }
        }
    """
```

**Integration Point:**
```python
# In src/main.py vor Trading Loop
regime = await detect_market_regime()

if regime["regime"] == "risk_off" and regime["confidence"] > 0.8:
    logger.warning("Risk-off detected, increasing defensive allocation")
    # Adjust TARGET_ALLOCATIONS temporarily
    # (Erfordert dynamische Allocation-Anpassung)
```

---

### Phase 3: Advanced Features (Future)

#### Task 3.1: Portfolio Coach Chatbot
**Use Case:** User kann Fragen zum Portfolio stellen
**Beispiel:**
- User: "Warum hast du AAPL verkauft?"
- Bot: "AAPL wurde verkauft wegen RSI > 75 (overbought) und MACD Momentum Umkehr..."

#### Task 3.2: Risk Warning System
**Use Case:** Proaktive Warnungen bei erhöhtem Risiko
**Beispiel:**
- Bot: "Warnung: Dein Portfolio hat 60% Tech-Exposure, empfehle Diversifikation in andere Sektoren"

---

## 🛠️ Empfohlene LLM-Wahl

### Für Production: **Claude Sonnet 4.5**
**Warum?**
- ✅ Exzellente Financial Domain Knowledge
- ✅ Reliable Output (wenig Halluzinationen)
- ✅ Schnell (1-2 Sekunden Response Time)
- ✅ Cost-Efficient ($3 per Million Input Tokens)
- ✅ 200k Context Window (für lange Reports)

**API:**
```bash
pip install anthropic
```

**Config:**
```python
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

### Alternative: **OpenAI GPT-4o**
**Wann verwenden?**
- Wenn bereits OpenAI Account vorhanden
- Für strukturierte JSON Outputs (Function Calling)

**Nicht empfohlen:** GPT-3.5 (zu schwach für Financial Analysis)

---

## 💰 Kosten-Schätzung

### Szenario: Trade Explanations + Weekly Reports

**Annahmen:**
- 10 Trades pro Tag
- 1 Weekly Report
- 500 Tokens Input + 200 Tokens Output pro Trade Explanation
- 2000 Tokens Input + 500 Tokens Output pro Weekly Report

**Kosten (Claude Sonnet 4.5):**
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

**Monatliche Kosten:**
```
Trade Explanations:
  - 10 trades/day * 30 days = 300 trades/month
  - Input: 300 * 500 tokens * $3/1M = $0.45
  - Output: 300 * 200 tokens * $15/1M = $0.90
  - Subtotal: $1.35

Weekly Reports:
  - 4 reports/month
  - Input: 4 * 2000 tokens * $3/1M = $0.024
  - Output: 4 * 500 tokens * $15/1M = $0.03
  - Subtotal: $0.054

Total: ~$1.40/Monat
```

**Mit Sentiment Analysis (+$0.50/Tag):**
```
Total: ~$16.40/Monat
```

**Mit News API:**
```
Total: ~$465/Monat (hauptsächlich News API)
```

---

## 🚦 Implementierungs-Roadmap

### ✅ Jetzt starten (Sofort)
1. **Task 1.1: Trade Explanation Generator**
   - Niedrige Kosten (~$1.40/Monat)
   - Großer UX-Benefit
   - Kein Trading-Risiko

### 📅 Nächste 1-2 Wochen
2. **Task 1.2: Weekly Report Generator**
   - Inkludiert in $1.40/Monat
   - Professionelle Reports
   - Email-Integration

### 📅 Nächste 1-2 Monate (Optional)
3. **Task 2.1: News Sentiment Analyzer**
   - Erfordert News API ($449/Monat)
   - Erst testen ob es Mehrwert bringt
   - Kann auch mit Free News APIs starten (Alpha Vantage Free Tier)

### 📅 Future (3+ Monate)
4. **Task 2.2: Market Regime Detector**
5. **Task 3.1: Portfolio Coach Chatbot**

---

## 📝 Implementation Checklist

### Voraussetzungen
- [ ] Anthropic API Key beantragen (https://console.anthropic.com/)
- [ ] API Key in .env hinzufügen
- [ ] `anthropic` Package installieren (`pip install anthropic`)
- [ ] Budget Limit setzen in Anthropic Console ($10/Monat empfohlen)

### Task 1.1: Trade Explanation Generator
- [ ] Erstelle `src/llm/` Directory
- [ ] Implementiere `src/llm/trade_explainer.py`
- [ ] Füge `explanation` Feld zu `trades` Tabelle hinzu (Supabase)
- [ ] Integriere in `src/main.py` nach Trade-Ausführung
- [ ] Teste mit 5 Trades
- [ ] Monitoring: Kosten tracken
- [ ] Dokumentiere in README.md

### Task 1.2: Weekly Report Generator
- [ ] Implementiere `src/llm/report_generator.py`
- [ ] Füge `narrative` Feld zu `weekly_reports` Tabelle hinzu
- [ ] Integriere in `src/core/performance_analyzer.py`
- [ ] Email-Integration (optional)
- [ ] Teste wöchentlichen Report
- [ ] Dokumentiere in README.md

---

## ⚠️ Wichtige Sicherheitshinweise

### 1. NIEMALS für Trading-Entscheidungen verwenden
```python
# ❌ FALSCH - NIEMALS SO MACHEN
llm_decision = llm_should_i_buy("AAPL")
if llm_decision == "yes":
    submit_order("AAPL", "BUY")  # GEFÄHRLICH!

# ✅ RICHTIG - LLM nur für Erklärungen
deterministic_signal = check_technical_indicators("AAPL")
if deterministic_signal.action == "BUY":
    submit_order("AAPL", "BUY")
    explanation = llm_explain_trade(signal)  # OK!
```

### 2. Immer Fallback haben
```python
try:
    explanation = await llm_explain_trade(trade)
except Exception as e:
    logger.error(f"LLM failed: {e}")
    explanation = f"Automated trade: {trade.action} {trade.ticker}"
    # System funktioniert weiter!
```

### 3. Rate Limiting beachten
```python
# Anthropic: 50 requests/minute für Tier 1
# Implementiere Rate Limiter wie für Alpaca
```

### 4. Kosten monitoren
```python
# Tracke API Usage in Datenbank
await log_llm_usage(
    tokens_input=500,
    tokens_output=200,
    cost_usd=0.004,
    model="claude-sonnet-4-20250514"
)
```

---

## 📚 Ressourcen

### Anthropic API
- Dokumentation: https://docs.anthropic.com/
- Pricing: https://www.anthropic.com/pricing
- Best Practices: https://docs.anthropic.com/claude/docs/best-practices

### Financial LLM Use Cases
- FinGPT: https://github.com/AI4Finance-Foundation/FinGPT
- Bloomberg GPT: Research Paper
- ChatGPT for Finance: Use Cases & Limits

### News APIs
- NewsAPI: https://newsapi.org/ ($449/month)
- Alpha Vantage: https://www.alphavantage.co/documentation/ (Free Tier available)
- Finnhub: https://finnhub.io/ (Free Tier available)

---

## 🎯 Zusammenfassung

**Aktueller Status:**
- ❌ KEIN LLM im Trading System (zu 100% deterministisch)
- ✅ Mathematische Formeln für alle Trading-Entscheidungen
- ✅ Regulierungskonform & Auditierbar

**Empfehlung:**
1. ✅ **STARTE mit Task 1.1** (Trade Explanations) - Niedrige Kosten, hoher Nutzen
2. ⏳ **Später:** Sentiment Analysis (nur als zusätzlicher Filter!)
3. ❌ **NIEMALS:** LLM für Trading-Entscheidungen

**Nächster Schritt:**
1. Anthropic API Key beantragen
2. Task 1.1 implementieren (2-3 Tage)
3. Testen mit 1 Woche Trades
4. Evaluieren ob es Mehrwert bringt

---

**Erstellt von:** Claude Code (Sonnet 4.5)
**Letzte Aktualisierung:** 2025-11-19

---

**Ende der LLM Integration Aufgaben**
