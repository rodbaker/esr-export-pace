"""SQLite database operations for ESR data storage."""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class ESRDataStore:
    """SQLite database operations for ESR export data."""
    
    def __init__(self, db_path: str = "data/esr_data.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._ensure_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self.conn.execute("PRAGMA journal_mode = WAL")
        return self.conn
    
    def _ensure_schema(self):
        """Create database schema if it doesn't exist."""
        conn = self._get_connection()
        
        # Create main fact table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_esr_world_weekly (
                commodity_code INTEGER NOT NULL,
                market_year INTEGER NOT NULL,
                week_ending DATE NOT NULL,
                weekly_exports_mt REAL NOT NULL DEFAULT 0,
                accumulated_exports_mt REAL NOT NULL DEFAULT 0,
                outstanding_sales_mt REAL NOT NULL DEFAULT 0,
                net_sales_mt REAL DEFAULT 0,
                total_commitment_mt REAL NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (commodity_code, market_year, week_ending),
                
                -- Constraints
                CHECK (weekly_exports_mt >= 0),
                CHECK (accumulated_exports_mt >= 0),
                CHECK (outstanding_sales_mt >= 0),
                CHECK (total_commitment_mt >= accumulated_exports_mt),
                CHECK (week_ending = date(week_ending, 'weekday 4'))  -- Thursday validation
            )
        """)
        
        # Create metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dim_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_esr_commodity_year 
            ON fact_esr_world_weekly(commodity_code, market_year)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_esr_week_ending 
            ON fact_esr_world_weekly(week_ending)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_updated 
            ON dim_metadata(updated_at)
        """)
        
        # Create views
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_current_marketing_year AS
            SELECT 
                commodity_code,
                market_year,
                week_ending,
                weekly_exports_mt,
                accumulated_exports_mt,
                outstanding_sales_mt,
                total_commitment_mt,
                -- Marketing week index (calculated from June 1 start)
                (julianday(week_ending) - julianday(market_year - 1 || '-06-01')) / 7 + 1 as marketing_week_index
            FROM fact_esr_world_weekly
            WHERE market_year = (SELECT MAX(market_year) FROM fact_esr_world_weekly)
            ORDER BY commodity_code, week_ending
        """)
        
        conn.commit()
        logger.info("Database schema initialized successfully")
    
    def _clean_data_for_sqlite(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame data to ensure SQLite compatibility.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame with proper data types and no problematic values
        """
        df_clean = df.copy()
        
        # Define the expected schema with proper data types
        numeric_columns = [
            'weekly_exports_mt', 'accumulated_exports_mt', 'outstanding_sales_mt',
            'net_sales_mt', 'total_commitment_mt'
        ]
        integer_columns = ['commodity_code', 'market_year']
        date_columns = ['week_ending']
        
        # Clean numeric columns - replace inf and NaN with appropriate values
        for col in numeric_columns:
            if col in df_clean.columns:
                # Convert to numeric, coercing errors to NaN
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                
                # Replace infinity with NaN first
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
                
                # For NOT NULL columns, replace NaN with 0.0 (appropriate for metrics)
                if col in ['weekly_exports_mt', 'accumulated_exports_mt', 'outstanding_sales_mt', 'total_commitment_mt']:
                    df_clean[col] = df_clean[col].fillna(0.0)
                else:  # net_sales_mt allows NULL
                    # Keep NaN as None for NULL columns
                    df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), None)
                
                # Ensure proper float64 type
                df_clean[col] = df_clean[col].astype('float64', errors='ignore')
        
        # Clean integer columns
        for col in integer_columns:
            if col in df_clean.columns:
                # Convert to numeric first
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                
                # Replace NaN with appropriate defaults
                if col == 'commodity_code':
                    # This should never be null - raise error if found
                    if df_clean[col].isna().any():
                        raise ValueError(f"NULL values found in required column {col}")
                elif col == 'market_year':
                    if df_clean[col].isna().any():
                        raise ValueError(f"NULL values found in required column {col}")
                
                # Convert to integer
                df_clean[col] = df_clean[col].astype('int64')
        
        # Clean date columns
        for col in date_columns:
            if col in df_clean.columns:
                # Handle various date formats and NaT values
                if df_clean[col].dtype == 'object':
                    # Remove any null/empty string values
                    df_clean = df_clean[df_clean[col].notna() & (df_clean[col] != '')]
                    
                    # Ensure string format (should already be YYYY-MM-DD from ETL)
                    df_clean[col] = df_clean[col].astype(str)
                    
                    # Validate date format
                    try:
                        pd.to_datetime(df_clean[col])
                    except Exception as e:
                        raise ValueError(f"Invalid date format in column {col}: {e}")
                else:
                    # Handle datetime objects
                    df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
                    
                    # Remove rows with NaT (Not a Time)
                    df_clean = df_clean[df_clean[col].notna()]
                    
                    # Convert to string format for SQLite
                    df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d')
        
        # Validate business logic constraints
        if 'total_commitment_mt' in df_clean.columns and 'accumulated_exports_mt' in df_clean.columns:
            # Ensure total_commitment_mt >= accumulated_exports_mt
            constraint_violations = df_clean['total_commitment_mt'] < df_clean['accumulated_exports_mt']
            if constraint_violations.any():
                logger.warning(f"Found {constraint_violations.sum()} records violating business constraint: "
                             "total_commitment_mt >= accumulated_exports_mt. Setting total_commitment_mt = accumulated_exports_mt")
                df_clean.loc[constraint_violations, 'total_commitment_mt'] = df_clean.loc[constraint_violations, 'accumulated_exports_mt']
        
        # Log any rows that were dropped
        original_len = len(df)
        cleaned_len = len(df_clean)
        if cleaned_len < original_len:
            logger.warning(f"Dropped {original_len - cleaned_len} rows during data cleaning")
        
        logger.debug(f"Data cleaning complete: {cleaned_len} records ready for insertion")
        return df_clean
    
    def upsert_weekly_data(self, df: pd.DataFrame) -> int:
        """Insert or update weekly ESR data.
        
        Args:
            df: DataFrame with columns matching fact_esr_world_weekly table
            
        Returns:
            Number of records affected
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to upsert_weekly_data")
            return 0
        
        # Validate required columns
        required_cols = [
            'commodity_code', 'market_year', 'week_ending',
            'weekly_exports_mt', 'accumulated_exports_mt', 'outstanding_sales_mt',
            'net_sales_mt', 'total_commitment_mt'
        ]
        
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        conn = self._get_connection()
        
        # Add updated_at timestamp and clean data for SQLite compatibility
        df = df.copy()
        df['updated_at'] = datetime.now().isoformat()
        
        # Clean and validate data before insertion
        df = self._clean_data_for_sqlite(df)
        
        try:
            # Delete existing records with same keys first (for true upsert behavior)
            for _, row in df.iterrows():
                conn.execute(
                    """DELETE FROM fact_esr_world_weekly 
                       WHERE commodity_code = ? AND market_year = ? AND week_ending = ?""",
                    (row['commodity_code'], row['market_year'], row['week_ending'])
                )
            
            # Insert the new data
            records_affected = df.to_sql(
                'fact_esr_world_weekly',
                conn,
                if_exists='append', 
                index=False,
                method='multi'
            )
            
            conn.commit()
            logger.info(f"Upserted {len(df)} records to fact_esr_world_weekly")
            return len(df)
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to upsert weekly data: {e}")
            raise
    
    def get_weekly_data(self, 
                       commodity_code: Optional[int] = None,
                       market_year: Optional[int] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """Retrieve weekly ESR data with optional filters.
        
        Args:
            commodity_code: Filter by commodity code
            market_year: Filter by marketing year
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            
        Returns:
            DataFrame with weekly data
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM fact_esr_world_weekly WHERE 1=1"
        params = []
        
        if commodity_code is not None:
            query += " AND commodity_code = ?"
            params.append(commodity_code)
            
        if market_year is not None:
            query += " AND market_year = ?"
            params.append(market_year)
            
        if start_date is not None:
            query += " AND week_ending >= ?"
            params.append(start_date)
            
        if end_date is not None:
            query += " AND week_ending <= ?"
            params.append(end_date)
            
        query += " ORDER BY commodity_code, market_year, week_ending"
        
        return pd.read_sql_query(query, conn, params=params)
    
    def get_current_marketing_year_data(self, commodity_code: Optional[int] = None) -> pd.DataFrame:
        """Get data for the current marketing year using the view.
        
        Args:
            commodity_code: Optional filter by commodity code
            
        Returns:
            DataFrame with current marketing year data including marketing_week_index
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM v_current_marketing_year"
        params = []
        
        if commodity_code is not None:
            query += " WHERE commodity_code = ?"
            params.append(commodity_code)
        
        return pd.read_sql_query(query, conn, params=params)
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata key-value pair.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        conn = self._get_connection()
        
        conn.execute(
            """INSERT OR REPLACE INTO dim_metadata (key, value, updated_at) 
               VALUES (?, ?, ?)""",
            (key, value, datetime.now().isoformat())
        )
        conn.commit()
        logger.debug(f"Set metadata: {key} = {value}")
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value by key.
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value or None if not found
        """
        conn = self._get_connection()
        
        cursor = conn.execute(
            "SELECT value FROM dim_metadata WHERE key = ?",
            (key,)
        )
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_last_release_timestamp(self, commodity_code: int) -> Optional[str]:
        """Get the last release timestamp for a commodity.
        
        Args:
            commodity_code: USDA commodity code
            
        Returns:
            ISO timestamp string or None if not found
        """
        key = f"last_release_timestamp_{commodity_code}"
        return self.get_metadata(key)
    
    def set_last_release_timestamp(self, commodity_code: int, timestamp: str) -> None:
        """Set the last release timestamp for a commodity.
        
        Args:
            commodity_code: USDA commodity code
            timestamp: ISO timestamp string
        """
        key = f"last_release_timestamp_{commodity_code}"
        self.set_metadata(key, timestamp)
    
    def export_to_csv(self, 
                     commodity_code: int,
                     output_path: str,
                     market_year: Optional[int] = None) -> str:
        """Export data to CSV file.
        
        Args:
            commodity_code: USDA commodity code
            output_path: Path for output CSV file
            market_year: Optional filter by marketing year (defaults to current)
            
        Returns:
            Path to created CSV file
        """
        # Get the data
        if market_year is None:
            df = self.get_current_marketing_year_data(commodity_code)
        else:
            df = self.get_weekly_data(commodity_code=commodity_code, market_year=market_year)
        
        if df.empty:
            raise ValueError(f"No data found for commodity {commodity_code}")
        
        # Create output directory if needed
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} records to {output_path}")
        
        return str(output_path)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        conn = self._get_connection()
        
        stats = {}
        
        # Count of records by commodity and market year
        cursor = conn.execute("""
            SELECT commodity_code, market_year, COUNT(*) as record_count
            FROM fact_esr_world_weekly
            GROUP BY commodity_code, market_year
            ORDER BY commodity_code, market_year
        """)
        stats['records_by_commodity_year'] = cursor.fetchall()
        
        # Total records
        cursor = conn.execute("SELECT COUNT(*) FROM fact_esr_world_weekly")
        stats['total_records'] = cursor.fetchone()[0]
        
        # Date range
        cursor = conn.execute("""
            SELECT MIN(week_ending) as earliest_date, MAX(week_ending) as latest_date
            FROM fact_esr_world_weekly
        """)
        result = cursor.fetchone()
        stats['date_range'] = {
            'earliest': result[0],
            'latest': result[1]
        }
        
        # Metadata entries
        cursor = conn.execute("SELECT COUNT(*) FROM dim_metadata")
        stats['metadata_entries'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
