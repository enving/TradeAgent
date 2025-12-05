uu# Feature Request: Multi-Factor Signal Scoring System

**Status:** Konzeptionell (nicht implementiert)
**Datum:** 2025-11-19
**Priorität:** Medium-High
**Scope:** Global (alle Strategien: Defensive, Momentum, zukünftige Short-Term)

---

## 🎯 Problem Statement

**Beobachtung aus User-Chat:**
Ein User fragte eine andere KI nach Trading-Empfehlungen für europäische Aktien. Die Antworten waren:
- ❌ Zu vage ("könnte interessant sein")
- ❌ Keine quantifizierbaren Bewertungen (P/E, ROE, Debt/Equity fehlten)
- ❌ Kein Timing (wann einsteigen/aussteigen?)
- ❌ Kein Risiko-Management (Stop-Loss, Position Size)
- ❌ Narrative statt Zahlen ("positive Stimmung" ohne Sentiment-Score)

**Kernproblem:**
Aktuelle Trading-Entscheidungen im TradeAgent basieren auf:
1. **Technische Indikatoren** (RSI, MACD, Volume) → Momentum Strategy
2. **Feste Allokationen** (25% VTI, 15% VGK, 10% GLD) → Defensive Core

**Was fehlt:**
- ✅ **Fundamentale Bewertung** (P/E, PEG, Debt/Equity, ROE)
- ✅ **Sentiment-Analyse** (News, Social Media, Analystenmeinungen)
- ✅ **Multi-Factor Scoring** (kombiniere Technical + Fundamental + Sentiment)
- ✅ **Konfidenz-Level** (wie sicher ist dieses Signal?)
- ✅ **Risiko-Bewertung per Asset** (nicht nur Portfolio-Ebene)

---

## 💡 Lösungsansatz: Multi-Factor Signal Scoring

### **Konzept:**

**Statt:**
```python
# Aktuell: Nur Technische Indikatoren
if rsi < 30 and macd_crossover:
    return Signal(action="buy", symbol="AAPL")
```

**Besser:**
```python
# Multi-Factor: Kombiniere 3 Dimensionen
score = calculate_signal_score(
    symbol="AAPL",
    technical_score=0.8,      # RSI oversold + MACD bullish
    fundamental_score=0.6,    # P/E fair, aber ROE gut
    sentiment_score=0.7,      # News bullish, Analystenmeinungen neutral
)

# Nur handeln wenn ALLE 3 Faktoren OK
if score.confidence > 0.7 and score.risk_level < 0.5:
    return Signal(
        action="buy",
        symbol="AAPL",
        confidence=score.confidence,
        reasoning=score.explain()
    )
```

---

## 🏗️ Architektur-Vorschlag

### **1. Multi-Factor Scoring Engine**

```python
# src/core/signal_scorer.py

class SignalScorer:
    """Kombiniert Technical, Fundamental & Sentiment zu einem Score."""

    async def calculate_signal_score(self, symbol: str) -> SignalScore:
        """
        Returns:
            SignalScore mit:
            - technical_score: 0.0-1.0 (RSI, MACD, Volume)
            - fundamental_score: 0.0-1.0 (P/E, ROE, Debt/Equity)
            - sentiment_score: 0.0-1.0 (News, Social, Analystenmeinungen)
            - confidence: Gewichteter Durchschnitt
            - risk_level: Kombiniertes Risiko
            - reasoning: Erklärung (für LLM Trade Explainer)
        """

        # 1. Technical Analysis (bereits vorhanden)
        technical = await self._analyze_technical(symbol)

        # 2. Fundamental Analysis (NEU)
        fundamental = await self._analyze_fundamental(symbol)

        # 3. Sentiment Analysis (NEU)
        sentiment = await self._analyze_sentiment(symbol)

        # 4. Kombiniere mit Gewichtung
        confidence = (
            technical.score * 0.4 +      # 40% Technical
            fundamental.score * 0.35 +   # 35% Fundamental
            sentiment.score * 0.25       # 25% Sentiment
        )

        return SignalScore(
            symbol=symbol,
            technical_score=technical.score,
            fundamental_score=fundamental.score,
            sentiment_score=sentiment.score,
            confidence=confidence,
            risk_level=self._calculate_risk(technical, fundamental, sentiment),
            reasoning=self._explain(technical, fundamental, sentiment)
        )
```

### **2. Fundamental Analyzer (NEU)**

```python
# src/analyzers/fundamental_analyzer.py

class FundamentalAnalyzer:
    """Bewertet Aktien anhand fundamentaler Kennzahlen."""

    async def analyze(self, symbol: str) -> FundamentalScore:
        """
        Holt Fundamentaldaten und bewertet sie.

        Metriken:
        - P/E Ratio (Kurs-Gewinn-Verhältnis)
        - PEG Ratio (P/E zu Wachstum)
        - Debt/Equity (Verschuldung)
        - ROE (Return on Equity)
        - Free Cash Flow

        Returns:
            FundamentalScore mit:
            - score: 0.0-1.0
            - metrics: Dict mit allen Kennzahlen
            - flags: Liste von Warnungen (z.B. "hohe Verschuldung")
        """

        # Datenquellen (kostenlos/günstig):
        # 1. Alpha Vantage (kostenlos, fundamental data)
        # 2. Yahoo Finance Web Scraping
        # 3. Financial Modeling Prep (free tier)

        metrics = await self._fetch_fundamentals(symbol)

        # Bewertung
        score = 0.0
        flags = []

        # P/E Check
        if metrics.pe_ratio:
            if 12 <= metrics.pe_ratio <= 25:
                score += 0.25  # Fair bewertet
            elif metrics.pe_ratio > 40:
                score += 0.0   # Überbewertet
                flags.append("overvalued_pe")
            elif metrics.pe_ratio < 0:
                score += 0.0   # Negativ = Verlust
                flags.append("negative_earnings")

        # ROE Check
        if metrics.roe:
            if metrics.roe > 15:
                score += 0.25  # Gute Profitabilität
            elif metrics.roe < 0:
                score += 0.0   # Unprofitabel
                flags.append("negative_roe")

        # Debt/Equity Check
        if metrics.debt_to_equity:
            if metrics.debt_to_equity < 1.0:
                score += 0.25  # Gesund verschuldet
            elif metrics.debt_to_equity > 2.0:
                score += 0.0   # Überschuldet
                flags.append("high_debt")

        # PEG Check (P/E zu Wachstum)
        if metrics.peg_ratio:
            if metrics.peg_ratio < 1.5:
                score += 0.25  # Fair relativ zu Wachstum

        return FundamentalScore(
            score=score,
            metrics=metrics,
            flags=flags
        )
```

### **3. Sentiment Analyzer (NEU)**

```python
# src/analyzers/sentiment_analyzer.py

class SentimentAnalyzer:
    """Analysiert News, Social Media, Analystenmeinungen."""

    async def analyze(self, symbol: str) -> SentimentScore:
        """
        Aggregiert Sentiment aus mehreren Quellen.

        Quellen:
        - News (letzte 24h)
        - Reddit/Twitter (optional)
        - Analystenmeinungen

        Returns:
            SentimentScore mit:
            - score: 0.0-1.0 (0 = sehr bearish, 1 = sehr bullish)
            - news_sentiment: -1.0 bis +1.0
            - analyst_rating: buy/hold/sell count
            - confidence: Wie viele Quellen verfügbar
        """

        # Datenquellen (kostenlos/günstig):
        # 1. MarketAux API (kostenlos, News mit Sentiment)
        # 2. FinBERT (Hugging Face, kostenlos, lokal)
        # 3. Alpha Vantage News Sentiment (free tier)

        news_sentiment = await self._fetch_news_sentiment(symbol)
        analyst_rating = await self._fetch_analyst_rating(symbol)

        # Gewichtung
        score = 0.5  # Neutral baseline

        # News Sentiment
        if news_sentiment:
            score += news_sentiment * 0.4  # -0.4 bis +0.4

        # Analystenmeinungen
        if analyst_rating:
            if analyst_rating.buy_count > analyst_rating.sell_count:
                score += 0.1
            elif analyst_rating.sell_count > analyst_rating.buy_count:
                score -= 0.1

        # Clamp to 0-1
        score = max(0.0, min(1.0, score))

        return SentimentScore(
            score=score,
            news_sentiment=news_sentiment,
            analyst_rating=analyst_rating,
            confidence=self._calculate_confidence(news_sentiment, analyst_rating)
        )
```

---

## 🔌 Integration in bestehende Strategien

### **Defensive Core:**
```python
# src/strategies/defensive_core.py

async def should_rebalance(...) -> bool:
    # Bestehende Logik: First trading day + Drift
    if await adapter.is_first_trading_day_of_month(today):
        return True

    # NEU: Fundamental Red Flags
    for symbol in TARGET_ALLOCATIONS.keys():
        fundamental = await fundamental_analyzer.analyze(symbol)

        # Wenn fundamental schlecht → sofort rebalancen (verkaufen)
        if "negative_roe" in fundamental.flags or "high_debt" in fundamental.flags:
            logger.warning(f"{symbol} fundamental red flags: {fundamental.flags}")
            return True  # Trigger rebalancing

    return False
```

### **Momentum Trading:**
```python
# src/strategies/momentum_trading.py

async def scan_for_signals(watchlist: list[str]) -> list[Signal]:
    signals = []

    for symbol in watchlist:
        # Bestehende Technical Analysis
        technical = await analyze_technical(symbol)

        # NEU: Multi-Factor Score
        score = await signal_scorer.calculate_signal_score(symbol)

        # Nur signalisieren wenn ALLE 3 Faktoren OK
        if score.confidence > 0.7:  # 70%+ Confidence
            signals.append(Signal(
                symbol=symbol,
                action="buy",
                confidence=score.confidence,
                reasoning=score.reasoning,  # Für LLM Explainer
                metadata={
                    "technical_score": score.technical_score,
                    "fundamental_score": score.fundamental_score,
                    "sentiment_score": score.sentiment_score,
                }
            ))

    return signals
```

---

## 📊 Datenquellen (Kostenlos/Günstig)

| Datentyp | Quelle | Kosten | API Limit |
|----------|--------|--------|-----------|
| **Fundamentaldaten** | Alpha Vantage | Kostenlos | 5 calls/min, 500/day |
| **Fundamentaldaten** | Yahoo Finance (Scraping) | Kostenlos | Unbegrenzt (rate limit self-imposed) |
| **Fundamentaldaten** | Financial Modeling Prep | $0-15/mo | 250 calls/day free |
| **News Sentiment** | MarketAux | Kostenlos | 100 calls/month |
| **News Sentiment** | FinBERT (Hugging Face) | Kostenlos | Lokal, unbegrenzt |
| **News Sentiment** | Alpha Vantage News | Kostenlos | 5 calls/min |
| **Analystenmeinungen** | Yahoo Finance (Scraping) | Kostenlos | Unbegrenzt |
| **Technische Daten** | Alpaca (bereits vorhanden) | Kostenlos | Paper trading |

**Geschätzte Gesamtkosten:** $0-15/Monat (free tier reicht für 1-2 daily scans)

---

## 🎨 UI/UX für Ergebnisse

### **Signal Output (erweitert):**

**Aktuell:**
```
Signal: BUY AAPL @ $268.00
Reason: RSI oversold + MACD bullish crossover
```

**Mit Multi-Factor:**
```
Signal: BUY AAPL @ $268.00
Confidence: 78% (HIGH)

Scores:
├─ Technical:    ████████░░ 80% (RSI 28, MACD bullish)
├─ Fundamental:  ██████░░░░ 65% (P/E 28 fair, ROE 24% good)
└─ Sentiment:    ████████░░ 85% (News bullish, 12 buy ratings)

Risk Level: ████░░░░░░ 35% (MEDIUM)

Reasoning:
"Strong oversold technical setup combined with fair valuation
and positive news sentiment. Recent product launch driving
analyst upgrades. Moderate risk due to slightly elevated P/E."

Stop-Loss: $260.00 (-3%)
Take-Profit: $280.00 (+4.5%)
```

---

## 🚀 Implementierungs-Roadmap

### **Phase 1: Foundation (1-2 Wochen)**
- [ ] Create `SignalScore` Pydantic model
- [ ] Create `FundamentalAnalyzer` skeleton
- [ ] Integrate Alpha Vantage Fundamental Data API
- [ ] Create basic P/E, ROE, Debt/Equity scoring logic
- [ ] Unit tests

### **Phase 2: Sentiment (1-2 Wochen)**
- [ ] Create `SentimentAnalyzer` skeleton
- [ ] Integrate MarketAux News API
- [ ] Implement FinBERT (Hugging Face) for news analysis
- [ ] Create sentiment aggregation logic
- [ ] Unit tests

### **Phase 3: Integration (1 Woche)**
- [ ] Create `SignalScorer` orchestrator
- [ ] Integrate into `momentum_trading.py`
- [ ] Add fundamental red flags to `defensive_core.py`
- [ ] Update `Trade` model with confidence + reasoning
- [ ] Update LLM Trade Explainer to use new metadata

### **Phase 4: Testing & Tuning (1-2 Wochen)**
- [ ] Backtest with historical data
- [ ] Tune scoring weights (40/35/25 vs. 33/33/33?)
- [ ] Optimize confidence thresholds
- [ ] Validate against Paper Trading
- [ ] Performance comparison: With vs. Without Multi-Factor

**Total Effort:** 4-7 Wochen (je nach Komplexität)

---

## 🤔 Offene Fragen & Diskussion

### **1. Gewichtung der Faktoren**

**Frage:** Wie gewichten wir Technical vs. Fundamental vs. Sentiment?

**Optionen:**
- **A) Fixed Weights:** 40% Technical / 35% Fundamental / 25% Sentiment
- **B) Strategy-Specific:** Momentum = 60/20/20, Defensive = 20/60/20
- **C) Dynamic:** Machine Learning optimiert Gewichtung basierend auf Backtest

**Empfehlung:** Start mit **B) Strategy-Specific**, später erweitern zu **C) Dynamic**

### **2. Datenqualität vs. Kosten**

**Frage:** Kostenlose APIs (Alpha Vantage, MarketAux) vs. Premium (Bloomberg, FactSet)?

**Trade-offs:**
- **Kostenlos:** 5-10 calls/min, delayed data (15-20 min), weniger Coverage
- **Premium:** Echtzeit, volle Coverage, aber $100-500/Monat

**Empfehlung:** **Start mit kostenlos**, upgrade nur wenn nötig (z.B. für Short-Term Intraday)

### **3. Sentiment-Quellen**

**Frage:** News only vs. Social Media (Reddit, Twitter)?

**Trade-offs:**
- **News Only:** Zuverlässiger, weniger Noise, aber langsamer
- **Social Media:** Schneller, aber mehr Noise, Manipulation risk

**Empfehlung:** **Start mit News**, Social Media als experimentelle Feature

### **4. Fundamental-Update-Frequenz**

**Frage:** Wie oft Fundamentaldaten aktualisieren?

**Optionen:**
- **A) Daily:** Jeden Tag vor Market Open (hoher API-Verbrauch)
- **B) Weekly:** Jeden Montag (spart API calls)
- **C) On-Demand:** Nur wenn Technical Signal triggert (effizient)

**Empfehlung:** **C) On-Demand** für Momentum, **B) Weekly** für Defensive Core

### **5. Integration mit LLM**

**Frage:** Soll LLM Multi-Factor Score interpretieren oder selbst generieren?

**Optionen:**
- **A) LLM interpretiert Score:** System berechnet Score → LLM erklärt
- **B) LLM generiert Score:** LLM bekommt rohe Daten → berechnet selbst

**Empfehlung:** **A) LLM interpretiert** (deterministisch + erklärbar)

---

## 📚 Verwandte Konzepte & Inspirationen

### **User-Chat Insights:**

Aus dem analysierten Chat:
1. **"Quantifizierbare Bewertungen statt Narrative"** → Exakte P/E, ROE, Debt/Equity
2. **"Sentiment ohne Kontext ist nutzlos"** → Nicht nur "positive Stimmung", sondern +0.7 Score
3. **"Intraday-Mechanik fehlte"** → Für Short-Term Strategie relevant
4. **"Überbewertung ausrechnen"** → DCF Mini-Kalkulator als zukünftiges Feature

### **System-Prompt Inspiration:**

```
Du analysierst EXAKT 2-3 Trade-Setup pro Tag.

SETUP-FORMAT:
Ticker | Sektor | Signal-Typ | Einstieg | Stop-Loss | Gewinnziel | Rationale

AUSSCHLUSSKRITERIEN:
- P/E negativ oder < -5 (Distressed)
- ROE < 0% (unprofitabel)
- Debt/Equity > 2 (überschuldet)
- News Sentiment < -0.5 (bearish)

ENTSCHEIDUNGSLOGIK:
1. Filter nach Bewertung (P/E 12-25, PEG < 2)
2. Filter nach Sentiment (mindestens neutral)
3. Finde Intraday Setup (RSI, MACD, Breakout)
4. Kombiniere: Setup + Bewertung + Sentiment alle OK → Trade
5. WARNUNG: 2 von 3 Faktoren schlecht = Passe
```

→ **Dies ist exakt Multi-Factor Scoring!**

---

## 🎯 Success Metrics

Wie messen wir Erfolg nach Implementierung?

| Metric | Baseline (aktuell) | Target (mit Multi-Factor) |
|--------|-------------------|---------------------------|
| **Win Rate** | ? (noch nicht gemessen) | > 55% |
| **Sharpe Ratio** | 0.0 (neuer Account) | > 1.5 (nach 3 Monaten) |
| **Max Drawdown** | 0% (noch keine Trades) | < 10% |
| **False Positive Rate** | ? | < 30% (Signale die nicht profitabel) |
| **Avg Confidence** | N/A | > 0.7 (nur high-confidence trades) |

---

## 🔗 Anbindung an bestehendes System

### **Wo integrieren?**

```
TradeAgent/
├── src/
│   ├── analyzers/                    # NEU
│   │   ├── __init__.py
│   │   ├── fundamental_analyzer.py   # NEU - P/E, ROE, Debt/Equity
│   │   ├── sentiment_analyzer.py     # NEU - News, Social, Analystenmeinungen
│   │   └── technical_analyzer.py     # Refactor aus momentum_trading.py
│   │
│   ├── core/
│   │   ├── signal_scorer.py          # NEU - Orchestrator für Multi-Factor
│   │   └── risk_manager.py           # UPDATE - Nutze SignalScore.risk_level
│   │
│   ├── models/
│   │   ├── signal_score.py           # NEU - SignalScore, FundamentalScore, SentimentScore
│   │   └── trade.py                  # UPDATE - Add confidence, reasoning fields
│   │
│   ├── strategies/
│   │   ├── defensive_core.py         # UPDATE - Check fundamental red flags
│   │   └── momentum_trading.py       # UPDATE - Use SignalScorer
│   │
│   └── llm/
│       └── trade_explainer.py        # UPDATE - Use score.reasoning as input
│
└── tests/
    ├── test_fundamental_analyzer.py  # NEU
    ├── test_sentiment_analyzer.py    # NEU
    └── test_signal_scorer.py         # NEU
```

### **API Clients benötigt:**

```python
# src/clients/alpha_vantage_client.py (NEU)
class AlphaVantageClient:
    async def get_fundamental_data(symbol: str) -> FundamentalData
    async def get_news_sentiment(symbol: str) -> list[NewsSentiment]

# src/clients/marketaux_client.py (NEU)
class MarketAuxClient:
    async def get_news(symbol: str, limit: int = 50) -> list[NewsArticle]

# src/clients/finbert_client.py (NEU)
class FinBERTClient:
    async def analyze_sentiment(text: str) -> float  # -1.0 bis +1.0
```

---

## 💭 Gedanken & Offene Punkte

### **Pro Multi-Factor:**
✅ Reduziert False Positives (schlechte Signale werden gefiltert)
✅ Erhöht Confidence in Trades (User fühlt sich sicherer)
✅ Bessere Explainability (LLM kann präziser erklären warum Signal gut)
✅ Systematischer Ansatz (nicht nur "Bauchgefühl")
✅ Skalierbar (funktioniert für Defensive, Momentum, Short-Term)

### **Contra Multi-Factor:**
❌ Mehr API Calls = höherer Aufwand (aber: kostenlose Tiers reichen)
❌ Komplexere Logik = mehr Code (aber: klare Trennung in Analyzer)
❌ Längere Scan-Zeit (Technical + Fundamental + Sentiment = ~3-5s pro Symbol)
❌ Tuning benötigt (Gewichtung, Schwellenwerte müssen optimiert werden)

### **Unklarheiten:**
🤔 **Wie kombinieren wir Zeitrahmen?** Fundamental = langfristig (Quartalsberichte), Sentiment = kurzfristig (24h News), Technical = Intraday (15-Min Charts)
🤔 **Was tun bei widersprüchlichen Signalen?** Technical bullish, aber Fundamental bearish → Skip oder weighted decision?
🤔 **Wie validieren wir Sentiment-Qualität?** FinBERT könnte Sarkasmus falsch interpretieren
🤔 **Brauchen wir Sector-Specific Scoring?** Tech-Aktien haben höhere P/E als Utilities → andere Schwellenwerte?

---

## 🎬 Nächste Schritte (wenn Feature genehmigt)

1. **User Feedback einholen:**
   - Ist Multi-Factor Scoring gewünscht?
   - Welche Gewichtung bevorzugt? (40/35/25 vs. 33/33/33 vs. strategy-specific)
   - Welche Datenquellen? (kostenlos vs. premium)
   - Short-Term Intraday vs. Multi-Day Holding?

2. **Prototype bauen:**
   - Minimal `FundamentalAnalyzer` mit Alpha Vantage
   - Test mit 3-5 Symbolen (VTI, AAPL, SAP, etc.)
   - Vergleich: Technical-Only vs. Multi-Factor

3. **Backtest durchführen:**
   - Historische Daten (letzten 3 Monate)
   - Win Rate, Sharpe Ratio, Max Drawdown messen
   - Entscheiden: Lohnt sich der Aufwand?

4. **Implementierung (wenn Test erfolgreich):**
   - Full Rollout gemäß Roadmap oben
   - Integration in alle Strategien
   - LLM Trade Explainer Update

---

## 📝 Zusammenfassung

**Was wir bauen könnten:**
Ein **Multi-Factor Signal Scoring System**, das Technical Analysis, Fundamental Analysis und Sentiment Analysis kombiniert, um **höhere Confidence** und **weniger False Positives** zu erreichen.

**Warum jetzt?**
- User-Chat zeigt klaren Bedarf an **quantifizierbaren Bewertungen**
- Aktuelles System nutzt nur **Technical** → einseitig
- Fundamentale Red Flags könnten **Verluste vermeiden** (z.B. Bayer: negative ROE)
- Sentiment-Analyse könnte **News-getriebene Chancen** identifizieren

**Wie starten?**
- **Konzeptionell:** Diese Datei diskutieren, Feedback einholen
- **Technisch:** Prototype mit Alpha Vantage + FinBERT
- **Validierung:** Backtest → Entscheidung ob Full Rollout

**Aufwand vs. Nutzen:**
- **Aufwand:** 4-7 Wochen Entwicklung, $0-15/Monat API-Kosten
- **Nutzen:** Höhere Win Rate, bessere Risk-Adjusted Returns, systematischere Entscheidungen

---

**Erstellt von:** Claude Code (Sonnet 4.5)
**Datum:** 2025-11-19
**Basierend auf:** User-Chat-Analyse (shorttermstrategy.txt)

**Status:** ⏸️ Wartet auf User-Feedback & Diskussion

---

**Ende der konzeptionellen Feature Request**
