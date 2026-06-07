"""ETL pipeline for ESR data: Extract, Transform, Load."""

from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import logging
from datetime import datetime, date

from .api_client import ESRAPIClient, ESRAPIError
from .data_store import ESRDataStore
from .validation import ESRDataValidator, ValidationError


logger = logging.getLogger(__name__)


class ESRETLPipeline:
    """ETL pipeline for ESR export data processing."""
    
    def __init__(self, 
                 api_client: Optional[ESRAPIClient] = None,
                 data_store: Optional[ESRDataStore] = None,
                 validator: Optional[ESRDataValidator] = None,
                 api_key: Optional[str] = None):
        """Initialize ETL pipeline.
        
        Args:
            api_client: ESR API client (creates default if None)
            data_store: Data storage handler (creates default if None)
            validator: Data validator (creates default if None)
            api_key: API key for USDA ESR API (used if creating default client)
        """
        self.api_client = api_client or ESRAPIClient(api_key=api_key)
        self.data_store = data_store or ESRDataStore()
        self.validator = validator or ESRDataValidator(fail_on_structural_errors=True)
        self._country_ref_checked = False

    def check_freshness(self, commodity_code: int) -> Tuple[bool, Optional[str], Optional[int]]:
        """Check if data needs to be refreshed based on release timestamps.
        
        Args:
            commodity_code: USDA commodity code
            
        Returns:
            Tuple of (needs_refresh, latest_timestamp, market_year)
        """
        try:
            # Get release info from API
            release_info = self.api_client.get_release_info_for_commodity(commodity_code)
            
            if not release_info:
                logger.warning(f"No release information found for commodity {commodity_code}")
                return True, None, None
            
            api_timestamp = release_info.get('releaseTimeStamp')
            market_year = release_info.get('marketYear')
            
            if not api_timestamp:
                logger.warning(f"No release timestamp found for commodity {commodity_code}")
                return True, None, market_year
            
            # Get stored timestamp
            stored_timestamp = self.data_store.get_last_release_timestamp(commodity_code)
            
            if not stored_timestamp:
                logger.info(f"No stored timestamp for commodity {commodity_code}, refresh needed")
                return True, api_timestamp, market_year
            
            # Compare timestamps
            needs_refresh = api_timestamp != stored_timestamp
            
            if needs_refresh:
                logger.info(f"Data refresh needed for commodity {commodity_code}: "
                          f"API={api_timestamp}, Stored={stored_timestamp}")
            else:
                logger.info(f"Data is current for commodity {commodity_code}")
                
            return needs_refresh, api_timestamp, market_year
            
        except ESRAPIError as e:
            logger.error(f"Failed to check freshness for commodity {commodity_code}: {e}")
            # On API error, assume refresh needed to avoid stale data
            return True, None, None

    COUNTRY_REF_MAX_AGE_DAYS = 7

    def ensure_country_reference(self) -> None:
        """Populate/refresh dim_country if missing or stale.

        Runs at most once per pipeline instance and refetches at most once
        per COUNTRY_REF_MAX_AGE_DAYS (tracked in dim_metadata), so every
        path that loads country facts — batch, backfill, single-commodity —
        gets named countries without hammering the API. Never fails the run.
        """
        if self._country_ref_checked:
            return
        self._country_ref_checked = True
        try:
            last = self.data_store.get_metadata('country_reference_synced_at')
            if last:
                age = datetime.now() - datetime.fromisoformat(last)
                if age.days < self.COUNTRY_REF_MAX_AGE_DAYS:
                    return
            countries = self.api_client.get_countries()
            n = self.data_store.upsert_countries(countries)
            self.data_store.set_metadata(
                'country_reference_synced_at', datetime.now().isoformat())
            logger.info(f"Synced {n} country reference rows")
        except Exception as e:
            logger.warning(f"Country reference sync failed (continuing): {e}")

    def extract_raw_data(self, commodity_code: int, market_year: int) -> pd.DataFrame:
        """Extract raw export data from ESR API.
        
        Args:
            commodity_code: USDA commodity code
            market_year: Marketing year to fetch
            
        Returns:
            DataFrame with raw API data
            
        Raises:
            ESRAPIError: If API request fails
        """
        logger.info(f"Extracting data for commodity {commodity_code}, market year {market_year}")
        
        try:
            raw_data = self.api_client.get_export_data(commodity_code, market_year)
            
            if not raw_data:
                raise ESRAPIError(f"No data returned for commodity {commodity_code}, MY {market_year}")
            
            df = pd.DataFrame(raw_data)
            logger.info(f"Extracted {len(df)} records for commodity {commodity_code}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to extract data for commodity {commodity_code}: {e}")
            raise ESRAPIError(f"Data extraction failed: {e}") from e
    
    def transform_to_world_aggregates(self, raw_df: pd.DataFrame, commodity_code: int, 
                                    market_year: int) -> pd.DataFrame:
        """Transform country-level data to world aggregates.
        
        Args:
            raw_df: Raw country-level data from API
            commodity_code: USDA commodity code
            market_year: Marketing year
            
        Returns:
            DataFrame with world-aggregated weekly data
        """
        logger.info(f"Transforming {len(raw_df)} raw records to world aggregates")
        
        if raw_df.empty:
            logger.warning("Empty DataFrame provided for transformation")
            return pd.DataFrame()
        
        # Group by week and aggregate across all countries
        agg_cols = {
            'weeklyExports': 'sum',
            'accumulatedExports': 'sum', 
            'outstandingSales': 'sum',
            'currentMYNetSales': 'sum',
            'currentMYTotalCommitment': 'sum'
        }
        
        # Handle null values and data quality issues
        df_clean = raw_df.copy()
        for col in agg_cols.keys():
            if col in df_clean.columns:
                # Convert to numeric, coercing errors to NaN
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                
                # Replace infinity values with NaN
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
                
                # Fill NaN with 0 for aggregation (appropriate for sum operations)
                df_clean[col] = df_clean[col].fillna(0)
        
        # Group by weekEndingDate and sum across countries
        world_data = df_clean.groupby('weekEndingDate').agg(agg_cols).reset_index()
        
        # Add commodity and market year info
        world_data['commodity_code'] = commodity_code
        world_data['market_year'] = market_year
        
        # Rename columns to match database schema
        column_mapping = {
            'weekEndingDate': 'week_ending',
            'weeklyExports': 'weekly_exports_mt',
            'accumulatedExports': 'accumulated_exports_mt',
            'outstandingSales': 'outstanding_sales_mt',
            'currentMYNetSales': 'net_sales_mt',
            'currentMYTotalCommitment': 'total_commitment_mt'
        }
        
        world_data = world_data.rename(columns=column_mapping)
        
        # Convert date column to date format (remove time component)
        # Ensure the dates are properly formatted as strings for SQLite
        try:
            world_data['week_ending'] = pd.to_datetime(world_data['week_ending'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Remove any rows where date conversion failed (resulting in NaT -> 'NaT' string)
            invalid_dates = world_data['week_ending'] == 'NaT'
            if invalid_dates.any():
                logger.warning(f"Removing {invalid_dates.sum()} rows with invalid dates")
                world_data = world_data[~invalid_dates]
                
        except Exception as e:
            logger.error(f"Failed to convert dates in world_data: {e}")
            raise ValueError(f"Date conversion failed: {e}")
        
        # Sort by date
        world_data = world_data.sort_values('week_ending').reset_index(drop=True)
        
        # Validate that all dates are actually Thursdays before database insertion
        dates_series = pd.to_datetime(world_data['week_ending'])
        non_thursdays = dates_series[dates_series.dt.dayofweek != 3]
        if len(non_thursdays) > 0:
            logger.warning(f"Found {len(non_thursdays)} non-Thursday dates in world aggregates:")
            for date in non_thursdays:
                logger.warning(f"  {date.strftime('%Y-%m-%d')} is a {date.strftime('%A')}")
            # This should not happen with valid ESR data, but let's warn rather than fail
            # The database CHECK constraint will prevent insertion of invalid dates
        
        logger.info(f"Transformed to {len(world_data)} world aggregate records")
        
        return world_data
    
    def transform_to_country_weekly(self, raw_df: pd.DataFrame,
                                    commodity_code: int,
                                    market_year: int) -> pd.DataFrame:
        """Transform raw API rows into the fact_esr_country_weekly schema.

        Keeps full country granularity — no aggregation across countries.
        """
        if raw_df.empty:
            return pd.DataFrame()

        df = raw_df.copy()
        numeric_cols = ['weeklyExports', 'accumulatedExports', 'outstandingSales',
                        'currentMYNetSales', 'currentMYTotalCommitment']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').replace(
                    [np.inf, -np.inf], np.nan).fillna(0)

        df['commodity_code'] = commodity_code
        df['market_year'] = market_year

        rename = {
            'countryCode': 'country_code',
            'weekEndingDate': 'week_ending',
            'weeklyExports': 'weekly_exports_mt',
            'accumulatedExports': 'accumulated_exports_mt',
            'outstandingSales': 'outstanding_sales_mt',
            'currentMYNetSales': 'net_sales_mt',
            'currentMYTotalCommitment': 'total_commitment_mt',
        }
        df = df.rename(columns=rename)

        df['week_ending'] = pd.to_datetime(
            df['week_ending'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df[df['week_ending'].notna() & (df['week_ending'] != 'NaT')]

        cols = ['commodity_code', 'market_year', 'week_ending', 'country_code',
                'weekly_exports_mt', 'accumulated_exports_mt',
                'outstanding_sales_mt', 'net_sales_mt', 'total_commitment_mt']
        return df[cols].reset_index(drop=True)

    def load_to_database(self, world_df: pd.DataFrame) -> int:
        """Load world-aggregated data to database.
        
        Args:
            world_df: World-aggregated DataFrame
            
        Returns:
            Number of records loaded
        """
        if world_df.empty:
            logger.warning("No data to load to database")
            return 0
        
        logger.info(f"Loading {len(world_df)} records to database")
        
        try:
            records_loaded = self.data_store.upsert_weekly_data(world_df)
            logger.info(f"Successfully loaded {records_loaded} records to database")
            return records_loaded
            
        except Exception as e:
            logger.error(f"Failed to load data to database: {e}")
            raise
    
    def run_etl(self, commodity_code: int, 
                force_refresh: bool = False,
                validate_data: bool = True,
                target_market_year: Optional[int] = None) -> Dict[str, Any]:
        """Run the complete ETL pipeline for a commodity.
        
        Args:
            commodity_code: USDA commodity code (e.g., 107 for All Wheat)
            force_refresh: Force refresh even if data is current
            validate_data: Run data validation checks
            target_market_year: Specific marketing year to fetch (None = current)
            
        Returns:
            Dictionary with ETL run results and statistics
        """
        start_time = datetime.now()
        results = {
            'commodity_code': commodity_code,
            'start_time': start_time.isoformat(),
            'success': False,
            'records_processed': 0,
            'records_loaded': 0,
            'validation_summary': {},
            'error': None
        }
        
        try:
            logger.info(f"Starting ETL pipeline for commodity {commodity_code}")
            
            # Step 1: Determine market year and check freshness
            if target_market_year:
                # Fetching specific historical year - always refresh
                market_year = target_market_year
                api_timestamp = None
                logger.info(f"Fetching historical data for marketing year {market_year}")
            elif not force_refresh:
                # Check if current data needs refresh
                needs_refresh, api_timestamp, market_year = self.check_freshness(commodity_code)
                if not needs_refresh:
                    results.update({
                        'success': True,
                        'skipped': True,
                        'message': 'Data is current, no refresh needed'
                    })
                    return results
            else:
                # Force refresh for current year
                release_info = self.api_client.get_release_info_for_commodity(commodity_code)
                if not release_info:
                    raise ESRAPIError(f"No release info found for commodity {commodity_code}")
                    
                api_timestamp = release_info.get('releaseTimeStamp')
                market_year = release_info.get('marketYear')
            
            if not market_year:
                raise ESRAPIError(f"No market year found for commodity {commodity_code}")
            
            # Step 2: Extract raw data
            raw_df = self.extract_raw_data(commodity_code, market_year)
            results['records_processed'] = len(raw_df)
            
            # Step 3: Validate raw data (optional)
            if validate_data:
                logger.info("Running validation on raw data")
                validation_results = self.validator.validate_all(
                    raw_df, 
                    expected_commodity=commodity_code,
                    expected_market_year=market_year
                )
                results['validation_summary'] = self.validator.get_summary()
                
                # Log validation issues but continue processing
                for category, checks in validation_results.items():
                    failed_checks = [check for check in checks if not check.passed]
                    if failed_checks:
                        logger.warning(f"Validation issues in {category}: "
                                     f"{len(failed_checks)} failed checks")
            
            # Step 4: Transform to world aggregates
            world_df = self.transform_to_world_aggregates(raw_df, commodity_code, market_year)
            
            # Step 5: Validate aggregated data
            if validate_data and not world_df.empty:
                logger.info("Running validation on aggregated data")
                agg_validation = self.validator.validate_aggregation(raw_df, world_df)
                
            # Step 6: Load to database (world aggregate)
            records_loaded = self.load_to_database(world_df)
            results['records_loaded'] = records_loaded

            # Country reference must exist before country facts are useful.
            self.ensure_country_reference()

            # Step 6b: Country-level load (additive — country granularity).
            # Failures do not fail the world load, but they must be VISIBLE:
            # recorded in results and logged at error level so callers can
            # surface them (batch_etl exits non-zero).
            try:
                country_df = self.transform_to_country_weekly(
                    raw_df, commodity_code, market_year)
                country_loaded = self.data_store.upsert_country_data(country_df)
                results['country_records_loaded'] = country_loaded
            except Exception as e:
                logger.error(f"Country-level load failed for {commodity_code}: {e}")
                results['country_records_loaded'] = 0
                results['country_load_error'] = str(e)
            
            # Step 7: Update metadata with successful timestamp (only for current year)
            if api_timestamp and not target_market_year:
                self.data_store.set_last_release_timestamp(commodity_code, api_timestamp)
                logger.info(f"Updated release timestamp for commodity {commodity_code}")
            elif target_market_year:
                logger.info(f"Historical data fetch - no timestamp update needed")
            
            # Success!
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results.update({
                'success': True,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'market_year': market_year,
                'api_timestamp': api_timestamp
            })
            
            logger.info(f"ETL pipeline completed successfully for commodity {commodity_code} "
                       f"in {duration:.2f}s. Processed {results['records_processed']} records, "
                       f"loaded {records_loaded} to database.")
            
            return results
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = str(e)
            results.update({
                'success': False,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'error': error_msg
            })
            
            logger.error(f"ETL pipeline failed for commodity {commodity_code} "
                        f"after {duration:.2f}s: {error_msg}")
            
            return results
    
    def export_to_csv(self, commodity_code: int, output_path: str, 
                     market_year: Optional[int] = None) -> str:
        """Export processed data to CSV file.
        
        Args:
            commodity_code: USDA commodity code
            output_path: Path for output CSV file
            market_year: Optional specific market year (defaults to current)
            
        Returns:
            Path to created CSV file
        """
        logger.info(f"Exporting commodity {commodity_code} data to CSV: {output_path}")
        
        try:
            csv_path = self.data_store.export_to_csv(
                commodity_code=commodity_code,
                output_path=output_path,
                market_year=market_year
            )
            
            logger.info(f"Successfully exported data to {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to export CSV for commodity {commodity_code}: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        return self.data_store.get_database_stats()
    
    def run_batch_etl(self, commodity_codes: List[int], 
                      force_refresh: bool = False,
                      validate_data: bool = True,
                      target_market_year: Optional[int] = None) -> Dict[str, Any]:
        """Run ETL pipeline for multiple commodities in batch.
        
        Args:
            commodity_codes: List of USDA commodity codes to process
            force_refresh: Force refresh even if data is current
            validate_data: Run data validation checks
            target_market_year: Specific marketing year to fetch (None = current)
            
        Returns:
            Dictionary with batch ETL results and statistics per commodity
        """
        start_time = datetime.now()
        batch_results = {
            'start_time': start_time.isoformat(),
            'commodity_codes': commodity_codes,
            'success': False,
            'completed_commodities': 0,
            'total_records_processed': 0,
            'total_records_loaded': 0,
            'commodity_results': {},
            'summary': {
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }
        }
        
        logger.info(f"Starting batch ETL pipeline for {len(commodity_codes)} commodities")
        
        try:
            for commodity_code in commodity_codes:
                logger.info(f"Processing commodity {commodity_code}")
                
                # Run individual ETL for this commodity
                result = self.run_etl(
                    commodity_code=commodity_code,
                    force_refresh=force_refresh,
                    validate_data=validate_data,
                    target_market_year=target_market_year
                )
                
                batch_results['commodity_results'][commodity_code] = result
                batch_results['completed_commodities'] += 1
                
                if result['success']:
                    if result.get('skipped'):
                        batch_results['summary']['skipped'] += 1
                    else:
                        batch_results['summary']['successful'] += 1
                        batch_results['total_records_processed'] += result.get('records_processed', 0)
                        batch_results['total_records_loaded'] += result.get('records_loaded', 0)
                else:
                    batch_results['summary']['failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    batch_results['summary']['errors'].append(f"Commodity {commodity_code}: {error_msg}")
            
            # Calculate overall success
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            batch_results.update({
                'success': batch_results['summary']['failed'] == 0,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration
            })
            
            logger.info(f"Batch ETL pipeline completed in {duration:.2f}s. "
                       f"Processed {batch_results['completed_commodities']} commodities: "
                       f"{batch_results['summary']['successful']} successful, "
                       f"{batch_results['summary']['skipped']} skipped, "
                       f"{batch_results['summary']['failed']} failed")
            
            return batch_results
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = str(e)
            batch_results.update({
                'success': False,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'error': error_msg
            })
            
            logger.error(f"Batch ETL pipeline failed after {duration:.2f}s: {error_msg}")
            
            return batch_results
    
    def close(self):
        """Close connections and clean up resources."""
        if hasattr(self.api_client, 'close'):
            self.api_client.close()
        if hasattr(self.data_store, 'close'):
            self.data_store.close()
