"""Disk-based caching for Polygon bar data.

This module implements a simple file-based cache to:
- Avoid redundant API calls
- Speed up repeated analysis
- Work within free tier rate limits
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz


UTC_TZ = pytz.UTC


class BarCache:
    """File-based cache for bar data with TTL expiration.

    Caches fetched bars to disk as JSON files, keyed by a hash
    of (symbol, start_time, end_time). Each cache entry has a
    time-to-live (TTL) after which it's considered expired.

    Attributes:
        cache_dir: Path to cache directory
        ttl_hours: Time-to-live in hours (default 24)

    Example:
        >>> cache = BarCache(cache_dir='data/cache')
        >>> key = cache.get_cache_key('AAPL', start_dt, end_dt)
        >>> cache.set(key, bars)
        >>> cached_bars = cache.get(key)
    """

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live for cached data (default 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Generate unique cache key from parameters.

        Args:
            symbol: Stock ticker
            start_time: Start datetime
            end_time: End datetime

        Returns:
            MD5 hash string as cache key

        Example:
            >>> key = cache.get_cache_key('AAPL', start, end)
            >>> print(key)  # 'a3f2b1c4d5e6f7...'
        """
        # Normalize symbol to uppercase
        symbol = symbol.upper()

        # Format timestamps consistently (ISO format)
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()

        # Create hash from components
        key_string = f"{symbol}:{start_str}:{end_str}"
        hash_obj = hashlib.md5(key_string.encode())

        return hash_obj.hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache key.

        Args:
            cache_key: Cache key hash

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get file path for cache metadata.

        Args:
            cache_key: Cache key hash

        Returns:
            Path to metadata file
        """
        return self.cache_dir / f"{cache_key}.meta.json"

    def get(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached bars if exists and not expired.

        Args:
            cache_key: Cache key from get_cache_key()

        Returns:
            List of bar dictionaries if cached and valid, None otherwise

        Example:
            >>> bars = cache.get(cache_key)
            >>> if bars:
            ...     print(f"Cache hit: {len(bars)} bars")
        """
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        # Check if cache file exists
        if not cache_path.exists():
            return None

        # Check if metadata exists
        if not meta_path.exists():
            # Metadata missing, consider cache invalid
            cache_path.unlink(missing_ok=True)
            return None

        try:
            # Read metadata
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            # Check if expired
            cached_at = datetime.fromisoformat(metadata['cached_at'])
            if cached_at.tzinfo is None:
                cached_at = UTC_TZ.localize(cached_at)

            age = datetime.now(UTC_TZ) - cached_at
            if age.total_seconds() > self.ttl_hours * 3600:
                # Expired, delete files
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                return None

            # Read cached data
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)

            # Convert timestamp strings back to datetime objects
            bars = []
            for bar in cached_data:
                bar_copy = bar.copy()
                bar_copy['timestamp'] = datetime.fromisoformat(bar['timestamp'])
                if bar_copy['timestamp'].tzinfo is None:
                    bar_copy['timestamp'] = UTC_TZ.localize(bar_copy['timestamp'])
                bars.append(bar_copy)

            return bars

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Cache corrupted, delete files
            print(f"⚠️  Cache corrupted for {cache_key}: {e}")
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            return None

    def set(
        self,
        cache_key: str,
        bars: List[Dict[str, Any]],
        ttl_hours: Optional[int] = None
    ):
        """Store bars in cache with expiration.

        Args:
            cache_key: Cache key from get_cache_key()
            bars: List of bar dictionaries to cache
            ttl_hours: Override default TTL (optional)

        Example:
            >>> cache.set(cache_key, bars, ttl_hours=48)
        """
        if not bars:
            return  # Don't cache empty results

        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        ttl = ttl_hours if ttl_hours is not None else self.ttl_hours

        try:
            # Prepare bars for JSON serialization (convert datetime to ISO string)
            serializable_bars = []
            for bar in bars:
                bar_copy = bar.copy()
                bar_copy['timestamp'] = bar['timestamp'].isoformat()
                serializable_bars.append(bar_copy)

            # Write cache data
            with open(cache_path, 'w') as f:
                json.dump(serializable_bars, f, indent=2)

            # Write metadata
            metadata = {
                'cached_at': datetime.now(UTC_TZ).isoformat(),
                'ttl_hours': ttl,
                'bar_count': len(bars),
                'symbol': bars[0].get('symbol', 'unknown') if bars else None
            }

            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"⚠️  Failed to cache data for {cache_key}: {e}")
            # Clean up partial writes
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)

    def clear_expired(self) -> int:
        """Remove cache files older than TTL.

        Returns:
            Number of cache entries deleted

        Example:
            >>> deleted = cache.clear_expired()
            >>> print(f"Deleted {deleted} expired cache entries")
        """
        deleted_count = 0

        # Iterate over metadata files
        for meta_path in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)

                cached_at = datetime.fromisoformat(metadata['cached_at'])
                if cached_at.tzinfo is None:
                    cached_at = UTC_TZ.localize(cached_at)

                ttl_hours = metadata.get('ttl_hours', self.ttl_hours)
                age = datetime.now(UTC_TZ) - cached_at

                if age.total_seconds() > ttl_hours * 3600:
                    # Expired, delete both files
                    cache_key = meta_path.stem.replace('.meta', '')
                    cache_path = self._get_cache_path(cache_key)

                    meta_path.unlink(missing_ok=True)
                    cache_path.unlink(missing_ok=True)
                    deleted_count += 1

            except (json.JSONDecodeError, KeyError, ValueError):
                # Corrupted metadata, delete it
                meta_path.unlink(missing_ok=True)
                deleted_count += 1

        return deleted_count

    def clear_all(self) -> int:
        """Remove all cache files.

        Returns:
            Number of cache entries deleted

        Example:
            >>> deleted = cache.clear_all()
            >>> print(f"Cleared {deleted} cache entries")
        """
        deleted_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            deleted_count += 1

        return deleted_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cache contents.

        Returns:
            Dictionary with cache statistics:
            - total_entries: int
            - total_size_mb: float
            - expired_entries: int
            - oldest_entry: datetime
            - newest_entry: datetime

        Example:
            >>> stats = cache.get_cache_stats()
            >>> print(f"Cache size: {stats['total_size_mb']:.2f} MB")
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        meta_files = list(self.cache_dir.glob("*.meta.json"))

        # Count actual cache entries (not metadata)
        data_files = [f for f in cache_files if not f.name.endswith('.meta.json')]

        stats = {
            'total_entries': len(data_files),
            'expired_entries': 0,
            'total_size_mb': 0.0,
            'oldest_entry': None,
            'newest_entry': None
        }

        if not data_files:
            return stats

        # Calculate total size
        stats['total_size_mb'] = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)

        # Check metadata for dates and expiration
        dates = []
        for meta_path in meta_files:
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)

                cached_at = datetime.fromisoformat(metadata['cached_at'])
                if cached_at.tzinfo is None:
                    cached_at = UTC_TZ.localize(cached_at)

                dates.append(cached_at)

                # Check if expired
                ttl_hours = metadata.get('ttl_hours', self.ttl_hours)
                age = datetime.now(UTC_TZ) - cached_at
                if age.total_seconds() > ttl_hours * 3600:
                    stats['expired_entries'] += 1

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        if dates:
            stats['oldest_entry'] = min(dates)
            stats['newest_entry'] = max(dates)

        return stats

    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_cache_stats()
        return (
            f"<BarCache(dir='{self.cache_dir}', "
            f"entries={stats['total_entries']}, "
            f"size_mb={stats['total_size_mb']:.2f})>"
        )
