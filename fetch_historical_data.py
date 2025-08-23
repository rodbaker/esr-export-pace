#!/usr/bin/env python3
"""
Fetch historical ESR data for pace analysis.

This script fetches 10 years of historical data for all wheat classes to enable 
robust pace analysis comparing current year to 5-year historical averages.

Supports all 7 wheat commodity classes:
- 101: Durum Wheat
- 102: Hard Red Spring Wheat  
- 103: Hard Red Winter Wheat
- 104: Soft Red Winter Wheat
- 105: Hard White Wheat
- 106: Soft White Wheat
- 107: All Wheat (aggregate)

Target: 10 marketing years (2017-2026) for comprehensive historical analysis.
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
        default=list(range(2017, 2027)),  # 2017-2026 = 10 years
        help='Marketing years to fetch (default: 2017-2026)'
    )
    
    parser.add_argument(
        '--commodities', 
        type=int, 
        nargs='+',
        default=[101, 102, 103, 104, 105, 106, 107],  # All wheat classes
        help='Commodity codes to fetch (default: all wheat classes 101-107)'
    )
    
    parser.add_argument(
        '--commodity', 
        type=int, 
        help='Single commodity code (alternative to --commodities)'
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
    
    # Determine which commodities to process
    if args.commodity:
        commodities = [args.commodity]
    else:
        commodities = args.commodities
    
    logger.info(f"Target commodities: {commodities}")
    logger.info(f"Marketing years: {args.years}")
    logger.info(f"Total operations: {len(commodities)} commodities × {len(args.years)} years = {len(commodities) * len(args.years)}")
    
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
        successful_operations = []
        failed_operations = []
        operation_count = 0
        total_operations = len(commodities) * len(args.years)
        
        # Process each commodity and year combination
        for commodity_code in commodities:
            logger.info(f"\n{'='*50}")
            logger.info(f"PROCESSING COMMODITY {commodity_code}")
            logger.info(f"{'='*50}")
            
            commodity_records = 0
            commodity_successful_years = []
            
            # Fetch each marketing year for this commodity
            for year in args.years:
                operation_count += 1
                logger.info(f"\n--- [{operation_count}/{total_operations}] Commodity {commodity_code}, MY {year} ---")
                
                try:
                    # Check if data already exists to avoid unnecessary API calls
                    existing_check = pipeline.get_database_stats()
                    existing_data = False
                    
                    if existing_check and 'records_by_commodity_year' in existing_check:
                        for existing_commodity, existing_year, count in existing_check['records_by_commodity_year']:
                            if existing_commodity == commodity_code and existing_year == year and count > 0:
                                existing_data = True
                                logger.info(f"   Data already exists: {count} weeks - skipping fetch")
                                successful_operations.append((commodity_code, year))
                                break
                    
                    if existing_data:
                        continue
                    
                    # Fetch specific historical year
                    results = pipeline.run_etl(
                        commodity_code=commodity_code,
                        force_refresh=True,
                        validate_data=True,
                        target_market_year=year
                    )
                    
                    if results['success']:
                        logger.info(f"✅ Commodity {commodity_code} MY {year}: {results['records_processed']} raw → {results['records_loaded']} aggregated")
                        total_records += results['records_loaded']
                        commodity_records += results['records_loaded']
                        successful_operations.append((commodity_code, year))
                        commodity_successful_years.append(year)
                        
                        # Show validation summary
                        validation = results.get('validation_summary', {})
                        if validation:
                            logger.info(f"   Validation: {validation['passed_checks']}/{validation['total_checks']} passed")
                    else:
                        logger.error(f"❌ Commodity {commodity_code} MY {year} failed: {results.get('error', 'Unknown error')}")
                        failed_operations.append((commodity_code, year, results.get('error', 'Unknown error')))
                        
                except Exception as e:
                    logger.error(f"❌ Failed to fetch Commodity {commodity_code} MY {year}: {e}")
                    failed_operations.append((commodity_code, year, str(e)))
                    continue
            
            logger.info(f"\nCommodity {commodity_code} Summary:")
            logger.info(f"  Successful years: {commodity_successful_years}")
            logger.info(f"  Records loaded: {commodity_records}")
        
        # Comprehensive Summary
        logger.info(f"\n{'='*60}")
        logger.info("HISTORICAL DATA FETCH COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total operations attempted: {total_operations}")
        logger.info(f"Successful operations: {len(successful_operations)}")
        logger.info(f"Failed operations: {len(failed_operations)}")
        logger.info(f"Total records loaded: {total_records}")
        
        if successful_operations:
            logger.info(f"\n✅ SUCCESSFUL OPERATIONS:")
            by_commodity = {}
            for commodity, year in successful_operations:
                if commodity not in by_commodity:
                    by_commodity[commodity] = []
                by_commodity[commodity].append(year)
            
            for commodity, years in sorted(by_commodity.items()):
                logger.info(f"  Commodity {commodity}: MY {sorted(years)}")
        
        if failed_operations:
            logger.warning(f"\n❌ FAILED OPERATIONS:")
            for commodity, year, error in failed_operations:
                logger.warning(f"  Commodity {commodity} MY {year}: {error}")
        
        # Calculate coverage statistics
        target_operations = len(commodities) * len(args.years)
        success_rate = (len(successful_operations) / target_operations * 100) if target_operations > 0 else 0
        logger.info(f"\nSuccess rate: {success_rate:.1f}% ({len(successful_operations)}/{target_operations})")
        
        # Assess readiness for pace analysis
        successful_years_per_commodity = {}
        for commodity, year in successful_operations:
            if commodity not in successful_years_per_commodity:
                successful_years_per_commodity[commodity] = set()
            successful_years_per_commodity[commodity].add(year)
        
        ready_commodities = []
        for commodity, years in successful_years_per_commodity.items():
            if len(years) >= 5:  # Need at least 5 years for 5-year baseline
                ready_commodities.append(commodity)
        
        logger.info(f"\n📊 PACE ANALYSIS READINESS:")
        if ready_commodities:
            logger.info(f"✅ {len(ready_commodities)} commodities ready for 5-year pace analysis: {ready_commodities}")
        else:
            logger.warning("⚠️  No commodities have sufficient data (5+ years) for robust pace analysis")
        
        for commodity in commodities:
            year_count = len(successful_years_per_commodity.get(commodity, set()))
            status = "✅ Ready" if year_count >= 5 else f"⚠️  Need {5-year_count} more years"
            logger.info(f"  Commodity {commodity}: {year_count}/10 years - {status}")
        
        # Show updated database stats
        stats = pipeline.get_database_stats()
        logger.info(f"\n📈 DATABASE STATUS:")
        logger.info(f"  Total records: {stats['total_records']}")
        logger.info(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        logger.info(f"\n  Records by commodity and year:")
        for commodity, year, count in sorted(stats['records_by_commodity_year']):
            logger.info(f"    Commodity {commodity} (MY {year}): {count} weeks")
        
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