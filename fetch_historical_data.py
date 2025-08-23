#!/usr/bin/env python3
"""
Fetch historical ESR data for pace analysis.

This script fetches 3+ years of historical data for All Wheat to enable 
pace analysis comparing current year to historical averages.
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.esr_pace.etl import ESRETLPipeline
from src.esr_pace.api_client import ESRAPIError


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('esr_historical_fetch.log')
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical ESR data for pace analysis"
    )
    
    parser.add_argument(
        '--years', 
        type=int, 
        nargs='+',
        default=[2023, 2024, 2025],
        help='Marketing years to fetch (default: 2023 2024 2025)'
    )
    
    parser.add_argument(
        '--commodity', 
        type=int, 
        default=107,
        help='Commodity code (default: 107 for All Wheat)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("=== ESR Historical Data Fetcher Started ===")
    logger.info(f"Target commodity: {args.commodity}")
    logger.info(f"Marketing years: {args.years}")
    
    # Get API key
    api_key = os.getenv('ESR_API_KEY')
    if not api_key:
        logger.error("API key is required. Set ESR_API_KEY environment variable.")
        return 1
    
    pipeline = None
    
    try:
        # Initialize ETL pipeline
        logger.info("Initializing ETL pipeline...")
        pipeline = ESRETLPipeline(api_key=api_key)
        
        total_records = 0
        successful_years = []
        
        # Fetch each marketing year
        for year in args.years:
            logger.info(f"\n--- Fetching Marketing Year {year} ---")
            
            try:
                # Fetch specific historical year
                results = pipeline.run_etl(
                    commodity_code=args.commodity,
                    force_refresh=True,
                    validate_data=True,
                    target_market_year=year
                )
                
                if results['success']:
                    logger.info(f"✅ MY {year}: {results['records_processed']} raw → {results['records_loaded']} aggregated")
                    total_records += results['records_loaded']
                    successful_years.append(year)
                    
                    # Show validation summary
                    validation = results.get('validation_summary', {})
                    if validation:
                        logger.info(f"   Validation: {validation['passed_checks']}/{validation['total_checks']} passed")
                else:
                    logger.error(f"❌ MY {year} failed: {results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to fetch MY {year}: {e}")
                continue
        
        # Summary
        logger.info(f"\n=== Historical Data Fetch Complete ===")
        logger.info(f"Successful years: {successful_years}")
        logger.info(f"Total records loaded: {total_records}")
        
        if len(successful_years) >= 3:
            logger.info("✅ Sufficient historical data for pace analysis!")
        else:
            logger.warning(f"⚠️  Only {len(successful_years)} years - recommend 3+ for reliable pace analysis")
        
        # Show database stats
        stats = pipeline.get_database_stats()
        logger.info(f"\nDatabase now contains:")
        logger.info(f"  - Total records: {stats['total_records']}")
        logger.info(f"  - Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        for commodity, year, count in stats['records_by_commodity_year']:
            logger.info(f"  - Commodity {commodity} (MY {year}): {count} weeks")
        
        return 0
        
    except Exception as e:
        logger.error(f"Historical fetch failed: {e}", exc_info=True)
        return 1
        
    finally:
        if pipeline:
            try:
                pipeline.close()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    sys.exit(main())