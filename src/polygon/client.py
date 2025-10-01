"""Polygon.io API client wrapper with error handling.

This module provides a wrapper around the Polygon.io REST API client
with enhanced error handling, connection validation, and market status checks.

Note: Free tier has limitations:
- 5 API calls per minute
- End-of-day data only (no real-time)
- No extended hours data
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, date
import time

from polygon import RESTClient
from polygon.exceptions import BadResponse, AuthError
import requests

from src.utils.config import config


class PolygonAPIError(Exception):
    """Custom exception for Polygon API errors."""
    pass


class PolygonClientWrapper:
    """Wrapper around Polygon SDK with error handling and free tier support.

    This wrapper handles:
    - API key validation
    - Connection testing
    - Market status checks
    - Error handling with retries
    - Rate limiting (free tier: 5 calls/minute)

    Attributes:
        client: Polygon RESTClient instance
        api_key: API key from config
        plan_tier: 'free', 'starter', or 'advanced'
        rate_limit_calls: Max API calls per minute
        last_call_time: Timestamp of last API call
        call_count: Number of calls in current minute

    Example:
        >>> client = PolygonClientWrapper()
        >>> if client.test_connection():
        ...     status = client.get_market_status('2024-01-15')
        ...     print(f"Market open: {status['open']}")
    """

    def __init__(self, api_key: Optional[str] = None, plan_tier: str = 'free'):
        """Initialize Polygon client.

        Args:
            api_key: Polygon API key (defaults to env variable)
            plan_tier: API plan tier ('free', 'starter', 'advanced')

        Raises:
            PolygonAPIError: If API key is missing
        """
        self.api_key = api_key or config.polygon_api_key

        if not self.api_key:
            raise PolygonAPIError(
                "Polygon API key not found. Set POLYGON_API_KEY in .env file"
            )

        # Initialize Polygon client
        try:
            self.client = RESTClient(api_key=self.api_key)
        except Exception as e:
            raise PolygonAPIError(f"Failed to initialize Polygon client: {e}")

        # Configure rate limiting based on plan
        self.plan_tier = plan_tier.lower()
        self.rate_limit_calls = {
            'free': 5,      # 5 calls per minute
            'starter': 100, # Effectively unlimited for our use
            'advanced': 1000
        }.get(self.plan_tier, 5)

        # Rate limiting tracking
        self.last_call_time = 0.0
        self.call_count = 0
        self.minute_window = 60.0  # seconds

    def _enforce_rate_limit(self):
        """Enforce rate limiting based on plan tier.

        For free tier: max 5 calls per minute, sleep if exceeded
        """
        if self.plan_tier != 'free':
            return  # No strict rate limiting for paid plans

        current_time = time.time()
        elapsed = current_time - self.last_call_time

        # Reset counter if more than 1 minute has passed
        if elapsed > self.minute_window:
            self.call_count = 0
            self.last_call_time = current_time

        # Check if we've hit the rate limit
        if self.call_count >= self.rate_limit_calls:
            sleep_time = self.minute_window - elapsed
            if sleep_time > 0:
                print(f"⏳ Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                self.call_count = 0
                self.last_call_time = time.time()

        self.call_count += 1

    def test_connection(self, retries: int = 3) -> bool:
        """Verify API key is valid by making a test request.

        Args:
            retries: Number of retry attempts

        Returns:
            True if connection successful, False otherwise

        Example:
            >>> client = PolygonClientWrapper()
            >>> if client.test_connection():
            ...     print("✅ Connected to Polygon API")
        """
        for attempt in range(retries):
            try:
                self._enforce_rate_limit()

                # Simple test: get market status for today
                # This endpoint is available on free tier
                response = self.client.get_market_status()

                if response:
                    print(f"✅ Polygon API connection successful (Plan: {self.plan_tier})")
                    return True

            except BadResponse as e:
                if "403" in str(e) or "401" in str(e):
                    print(f"❌ Invalid API key or insufficient permissions")
                    return False
                print(f"⚠️  Connection attempt {attempt + 1}/{retries} failed: {e}")

            except Exception as e:
                print(f"⚠️  Connection attempt {attempt + 1}/{retries} failed: {e}")

            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

        return False

    def get_market_status(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Check if market was open on given date.

        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary with market status info:
            - open: bool - was market open
            - date: str - date checked
            - exchanges: dict - status by exchange

        Raises:
            PolygonAPIError: If API call fails

        Example:
            >>> status = client.get_market_status('2024-01-15')
            >>> if status['open']:
            ...     print("Market was open")
        """
        try:
            self._enforce_rate_limit()

            if date_str:
                # Parse date to check if it's a weekend
                check_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Quick weekend check
                if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    return {
                        'open': False,
                        'date': date_str,
                        'reason': 'Weekend',
                        'exchanges': {}
                    }

            # Get current market status
            response = self.client.get_market_status()

            # Extract relevant info
            result = {
                'open': False,
                'date': date_str or datetime.now().strftime('%Y-%m-%d'),
                'exchanges': {}
            }

            if hasattr(response, 'market'):
                result['open'] = response.market == 'open'

            if hasattr(response, 'exchanges'):
                result['exchanges'] = {
                    exchange: status
                    for exchange, status in response.exchanges.items()
                }

            return result

        except Exception as e:
            raise PolygonAPIError(f"Failed to get market status: {e}")

    def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker details to validate symbol exists.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')

        Returns:
            Dictionary with ticker details or None if not found

        Example:
            >>> details = client.get_ticker_details('AAPL')
            >>> print(details['name'])  # 'Apple Inc.'
        """
        try:
            self._enforce_rate_limit()

            response = self.client.get_ticker_details(symbol)

            if response:
                return {
                    'ticker': response.ticker if hasattr(response, 'ticker') else symbol,
                    'name': response.name if hasattr(response, 'name') else None,
                    'market': response.market if hasattr(response, 'market') else None,
                    'active': response.active if hasattr(response, 'active') else True,
                }

            return None

        except (BadResponse, Exception) as e:
            # No results or other error - return None
            if "404" in str(e) or "not found" in str(e).lower():
                return None
            # For other errors, log and return None
            return None
        except Exception as e:
            print(f"⚠️  Failed to get ticker details for {symbol}: {e}")
            return None

    def is_free_tier(self) -> bool:
        """Check if using free tier API.

        Returns:
            True if free tier, False otherwise
        """
        return self.plan_tier == 'free'

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dictionary with rate limit info
        """
        elapsed = time.time() - self.last_call_time
        remaining_time = max(0, self.minute_window - elapsed)

        return {
            'plan_tier': self.plan_tier,
            'calls_per_minute': self.rate_limit_calls,
            'calls_made': self.call_count,
            'calls_remaining': self.rate_limit_calls - self.call_count,
            'reset_in_seconds': remaining_time
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<PolygonClientWrapper(plan='{self.plan_tier}', rate_limit={self.rate_limit_calls}/min)>"
