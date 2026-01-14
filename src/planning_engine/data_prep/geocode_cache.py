"""
Shared geocode cache using SQLite.

This module provides a cross-platform (Mac, Windows, Linux) geocoding cache
that is shared across all users to reduce API costs and improve performance.
"""

import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from contextlib import contextmanager
from datetime import datetime


class GeocodeCache:
    """
    Thread-safe SQLite-based geocoding cache shared across all users.
    
    The cache stores geocoded addresses with normalized keys to handle
    slight variations in address formatting.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize the geocode cache.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            conn.execute("""
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address_hash TEXT UNIQUE NOT NULL,
                    street1 TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    zip TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    formatted_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_address_hash 
                ON geocode_cache(address_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state 
                ON geocode_cache(state)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _normalize_address(self, street: str, city: str, state: str, zip_code: Optional[str] = None) -> str:
        """
        Normalize address for consistent hashing.
        
        Handles common variations like:
        - Case differences (Main St vs main st)
        - Extra whitespace
        - Common abbreviations
        
        Args:
            street: Street address
            city: City name
            state: State abbreviation or name
            zip_code: Optional ZIP code
            
        Returns:
            Normalized address string
        """
        # Normalize each component
        street_norm = street.upper().strip()
        city_norm = city.upper().strip()
        state_norm = state.upper().strip()
        
        # Build normalized address
        parts = [street_norm, city_norm, state_norm]
        if zip_code:
            parts.append(zip_code.strip())
        
        return "|".join(parts)
    
    def _hash_address(self, street: str, city: str, state: str, zip_code: Optional[str] = None) -> str:
        """
        Create a hash for address lookup.
        
        Args:
            street: Street address
            city: City name
            state: State abbreviation or name
            zip_code: Optional ZIP code
            
        Returns:
            SHA256 hash of normalized address
        """
        normalized = self._normalize_address(street, city, state, zip_code)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def get(self, street: str, city: str, state: str, zip_code: Optional[str] = None) -> Optional[Dict]:
        """
        Get cached geocode result for an address.
        
        Args:
            street: Street address
            city: City name
            state: State abbreviation or name
            zip_code: Optional ZIP code
            
        Returns:
            Dictionary with lat, lon, and other geocode data, or None if not cached
        """
        addr_hash = self._hash_address(street, city, state, zip_code)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT latitude, longitude, formatted_address, street1, city, state, zip
                FROM geocode_cache
                WHERE address_hash = ?
            """, (addr_hash,))
            
            row = cursor.fetchone()
            if row:
                # Update access statistics
                conn.execute("""
                    UPDATE geocode_cache
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE address_hash = ?
                """, (addr_hash,))
                conn.commit()
                
                return {
                    'lat': row['latitude'],
                    'lon': row['longitude'],
                    'formatted': row['formatted_address'],
                    'street1': row['street1'],
                    'city': row['city'],
                    'state': row['state'],
                    'zip': row['zip']
                }
        
        return None
    
    def set(self, street: str, city: str, state: str, lat: float, lon: float, 
            zip_code: Optional[str] = None, formatted_address: Optional[str] = None):
        """
        Cache a geocode result.
        
        Args:
            street: Street address
            city: City name
            state: State abbreviation or name
            lat: Latitude
            lon: Longitude
            zip_code: Optional ZIP code
            formatted_address: Optional formatted address from geocoder
        """
        addr_hash = self._hash_address(street, city, state, zip_code)
        
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO geocode_cache 
                    (address_hash, street1, city, state, zip, latitude, longitude, formatted_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (addr_hash, street, city, state, zip_code, lat, lon, formatted_address))
                conn.commit()
            except sqlite3.IntegrityError:
                # Address already exists, update it
                conn.execute("""
                    UPDATE geocode_cache
                    SET latitude = ?, longitude = ?, formatted_address = ?,
                        last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE address_hash = ?
                """, (lat, lon, formatted_address, addr_hash))
                conn.commit()
    
    def batch_get(self, addresses: List[Tuple[str, str, str, Optional[str]]]) -> Dict[str, Optional[Dict]]:
        """
        Get multiple cached geocode results at once.
        
        Args:
            addresses: List of tuples (street, city, state, zip_code)
            
        Returns:
            Dictionary mapping address hash to geocode result (or None if not cached)
        """
        if not addresses:
            return {}
        
        # Generate hashes for all addresses
        hash_to_addr = {}
        for street, city, state, zip_code in addresses:
            addr_hash = self._hash_address(street, city, state, zip_code)
            hash_to_addr[addr_hash] = (street, city, state, zip_code)
        
        hashes = list(hash_to_addr.keys())
        results = {}
        
        with self._get_connection() as conn:
            # Build query with placeholders
            placeholders = ','.join('?' * len(hashes))
            cursor = conn.execute(f"""
                SELECT address_hash, latitude, longitude, formatted_address, 
                       street1, city, state, zip
                FROM geocode_cache
                WHERE address_hash IN ({placeholders})
            """, hashes)
            
            # Process results
            found_hashes = []
            for row in cursor:
                addr_hash = row['address_hash']
                found_hashes.append(addr_hash)
                results[addr_hash] = {
                    'lat': row['latitude'],
                    'lon': row['longitude'],
                    'formatted': row['formatted_address'],
                    'street1': row['street1'],
                    'city': row['city'],
                    'state': row['state'],
                    'zip': row['zip']
                }
            
            # Update access statistics for found entries
            if found_hashes:
                placeholders = ','.join('?' * len(found_hashes))
                conn.execute(f"""
                    UPDATE geocode_cache
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE address_hash IN ({placeholders})
                """, found_hashes)
                conn.commit()
        
        # Add None for addresses not found in cache
        for addr_hash in hash_to_addr:
            if addr_hash not in results:
                results[addr_hash] = None
        
        return results
    
    def batch_set(self, geocode_results: List[Dict]):
        """
        Cache multiple geocode results at once.
        
        Args:
            geocode_results: List of dicts with keys: street, city, state, zip, lat, lon, formatted
        """
        if not geocode_results:
            return
        
        with self._get_connection() as conn:
            for result in geocode_results:
                addr_hash = self._hash_address(
                    result['street'],
                    result['city'],
                    result['state'],
                    result.get('zip')
                )
                
                try:
                    conn.execute("""
                        INSERT INTO geocode_cache 
                        (address_hash, street1, city, state, zip, latitude, longitude, formatted_address)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        addr_hash,
                        result['street'],
                        result['city'],
                        result['state'],
                        result.get('zip'),
                        result['lat'],
                        result['lon'],
                        result.get('formatted')
                    ))
                except sqlite3.IntegrityError:
                    # Address already exists, update it
                    conn.execute("""
                        UPDATE geocode_cache
                        SET latitude = ?, longitude = ?, formatted_address = ?,
                            last_accessed = CURRENT_TIMESTAMP,
                            access_count = access_count + 1
                        WHERE address_hash = ?
                    """, (
                        result['lat'],
                        result['lon'],
                        result.get('formatted'),
                        addr_hash
                    ))
            
            conn.commit()
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses_per_entry
                FROM geocode_cache
            """)
            row = cursor.fetchone()
            
            return {
                'total_entries': row['total_entries'],
                'total_accesses': row['total_accesses'],
                'avg_accesses_per_entry': round(row['avg_accesses_per_entry'], 2) if row['avg_accesses_per_entry'] else 0
            }


# Global cache instance
_cache_instance: Optional[GeocodeCache] = None


def get_cache(cache_dir: Optional[Path] = None) -> GeocodeCache:
    """
    Get the global geocode cache instance.
    
    Args:
        cache_dir: Optional directory for the cache file. If not provided,
                   uses the project root's data directory.
    
    Returns:
        GeocodeCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        if cache_dir is None:
            # Use project root's data directory
            from planning_engine.paths import get_project_root
            root = get_project_root()
            # Store at project root level, not user-scoped
            # This ensures it's shared across all users
            if 'data' in str(root):
                # If we're in a user-scoped path like data/username/
                # Go up to the actual project root
                cache_dir = root.parent.parent / "data"
            else:
                cache_dir = root / "data"
        
        cache_path = cache_dir / "geocode_cache.db"
        _cache_instance = GeocodeCache(cache_path)
    
    return _cache_instance
