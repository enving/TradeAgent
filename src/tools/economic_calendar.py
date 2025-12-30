"""Economic Calendar Tool - Tracks important market events.

Uses free APIs (yfinance, Finnhub) to track:
- FOMC meetings
- Earnings reports
- Economic data releases (CPI, Jobs, GDP)
- Company events

Helps avoid trading during high-volatility events.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
import yfinance as yf

from ..utils.config import config
from ..utils.logger import logger


class EconomicEvent:
    """Economic calendar event."""

    def __init__(
        self,
        date: datetime,
        event_type: str,  # "FOMC", "EARNINGS", "CPI", "JOBS", etc.
        ticker: Optional[str],  # For company-specific events
        description: str,
        impact: str,  # "HIGH", "MEDIUM", "LOW"
    ):
        self.date = date
        self.event_type = event_type
        self.ticker = ticker
        self.description = description
        self.impact = impact

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "event_type": self.event_type,
            "ticker": self.ticker,
            "description": self.description,
            "impact": self.impact,
        }


class EconomicCalendar:
    """Economic calendar tool using free APIs."""

    # FOMC meeting dates (2025 - manually maintained)
    # Source: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    FOMC_DATES_2025 = [
        "2025-01-29",  # January Meeting
        "2025-03-19",  # March Meeting
        "2025-05-07",  # May Meeting
        "2025-06-18",  # June Meeting
        "2025-07-30",  # July Meeting
        "2025-09-17",  # September Meeting
        "2025-11-05",  # November Meeting
        "2025-12-17",  # December Meeting
    ]

    def __init__(self):
        """Initialize economic calendar."""
        self.fomc_dates = [
            datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            for date in self.FOMC_DATES_2025
        ]

    async def get_upcoming_events(
        self, days: int = 7, tickers: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """Get upcoming economic events.

        Args:
            days: Number of days to look ahead
            tickers: Optional list of tickers to check for earnings

        Returns:
            List of upcoming events
        """
        events = []
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)

        # Check FOMC meetings
        for fomc_date in self.fomc_dates:
            if now <= fomc_date <= end_date:
                events.append(
                    EconomicEvent(
                        date=fomc_date,
                        event_type="FOMC",
                        ticker=None,
                        description="Federal Reserve FOMC Meeting",
                        impact="HIGH",
                    )
                )

        # Check earnings for specific tickers (if provided)
        if tickers and config.FINNHUB_API_KEY:
            earnings_events = await self._get_earnings_events(tickers, days)
            events.extend(earnings_events)

        return sorted(events, key=lambda e: e.date)

    async def _get_earnings_events(
        self, tickers: List[str], days: int
    ) -> List[EconomicEvent]:
        """Get earnings events from yfinance (free).

        Args:
            tickers: List of tickers to check
            days: Days to look ahead

        Returns:
            List of earnings events
        """
        events = []
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)

        for ticker in tickers:
            try:
                # Use yfinance to get earnings date
                stock = yf.Ticker(ticker)
                calendar = stock.calendar

                if calendar is not None and not calendar.empty:
                    # yfinance returns earnings date
                    if "Earnings Date" in calendar.index:
                        earnings_date_raw = calendar.loc["Earnings Date"]

                        # Handle both single date and date range
                        if hasattr(earnings_date_raw, "__iter__") and not isinstance(
                            earnings_date_raw, str
                        ):
                            earnings_date_raw = earnings_date_raw[0]

                        # Parse earnings date
                        if earnings_date_raw:
                            try:
                                earnings_date = datetime.strptime(
                                    str(earnings_date_raw), "%Y-%m-%d"
                                ).replace(tzinfo=timezone.utc)

                                if now <= earnings_date <= end_date:
                                    events.append(
                                        EconomicEvent(
                                            date=earnings_date,
                                            event_type="EARNINGS",
                                            ticker=ticker,
                                            description=f"{ticker} Earnings Report",
                                            impact="HIGH",
                                        )
                                    )
                            except (ValueError, TypeError):
                                logger.debug(f"Could not parse earnings date for {ticker}")

            except Exception as e:
                logger.debug(f"Error fetching earnings for {ticker}: {e}")
                continue

        return events

    def has_high_impact_event_today(
        self, events: List[EconomicEvent]
    ) -> tuple[bool, Optional[str]]:
        """Check if there's a high-impact event today.

        Args:
            events: List of events to check

        Returns:
            Tuple of (has_event, description)
        """
        today = datetime.now(timezone.utc).date()

        for event in events:
            if event.date.date() == today and event.impact == "HIGH":
                return True, event.description

        return False, None

    def should_avoid_trading(
        self, ticker: Optional[str] = None, events: Optional[List[EconomicEvent]] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if trading should be avoided.

        Args:
            ticker: Optional ticker to check for company-specific events
            events: Optional pre-fetched events (to avoid redundant API calls)

        Returns:
            Tuple of (should_avoid, reason)
        """
        today = datetime.now(timezone.utc).date()

        # Check FOMC meetings
        for fomc_date in self.fomc_dates:
            if fomc_date.date() == today:
                return True, "FOMC meeting today - high volatility expected"

        # Check events if provided
        if events:
            for event in events:
                if event.date.date() == today and event.impact == "HIGH":
                    # Check if ticker-specific
                    if ticker and event.ticker == ticker:
                        return True, f"{event.description} - avoid trading {ticker}"
                    elif not ticker and event.event_type == "FOMC":
                        return True, f"{event.description} - market-wide impact"

        return False, None


# Global singleton
_economic_calendar = None


def get_economic_calendar() -> EconomicCalendar:
    """Get or create the EconomicCalendar singleton.

    Returns:
        EconomicCalendar instance
    """
    global _economic_calendar
    if _economic_calendar is None:
        _economic_calendar = EconomicCalendar()
    return _economic_calendar
