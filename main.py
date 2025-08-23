#!/usr/bin/env python3
"""
ESR Export Pace Tracker - Main Script

Fetch current marketing year data for All Wheat (commodity 107) from USDA ESR API,
process it through the ETL pipeline, and export to CSV.

Usage:
    python main.py [--force-refresh] [--output OUTPUT_PATH] [--verbose]
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
    pass  # python-dotenv not installed, skip

from src.esr_pace.etl import ESRETLPipeline
from src.esr_pace.api_client import ESRAPIError


# All Wheat commodity code
ALL_WHEAT_COMMODITY_CODE = 107


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('esr_etl.log')
        ]
    )
    
    # Reduce noise from requests library
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ESR Export Pace Tracker - Fetch and process All Wheat export data"
    )
    
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force data refresh even if current data exists'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data/all_wheat_exports.csv',
        help='Output CSV file path (default: data/all_wheat_exports.csv)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics after processing'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='USDA ESR API key (can also be set via ESR_API_KEY environment variable)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("=== ESR Export Pace Tracker Started ===")
    logger.info(f"Target commodity: {ALL_WHEAT_COMMODITY_CODE} (All Wheat)")
    logger.info(f"Output path: {args.output}")
    logger.info(f"Force refresh: {args.force_refresh}")
    
    pipeline = None
    
    try:
        # Get API key from argument or environment variable
        api_key = args.api_key or os.getenv('ESR_API_KEY')
        
        if not api_key:
            logger.error("API key is required. Provide it via --api-key argument or ESR_API_KEY environment variable.")
            return 1
        
        # Initialize ETL pipeline
        logger.info("Initializing ETL pipeline...")
        pipeline = ESRETLPipeline(api_key=api_key)
        
        # Run ETL for All Wheat
        logger.info("Running ETL pipeline for All Wheat...")
        results = pipeline.run_etl(
            commodity_code=ALL_WHEAT_COMMODITY_CODE,
            force_refresh=args.force_refresh,
            validate_data=True
        )
        
        # Check results
        if not results['success']:
            logger.error(f"ETL pipeline failed: {results.get('error', 'Unknown error')}")
            return 1
        
        if results.get('skipped'):
            logger.info(results.get('message', 'ETL was skipped'))
        else:
            logger.info(f"ETL completed successfully:")
            logger.info(f"  - Records processed: {results['records_processed']}")
            logger.info(f"  - Records loaded: {results['records_loaded']}")
            logger.info(f"  - Duration: {results['duration_seconds']:.2f}s")
            logger.info(f"  - Market year: {results.get('market_year', 'N/A')}")
            
            # Show validation summary if available
            validation_summary = results.get('validation_summary', {})
            if validation_summary:
                logger.info(f"  - Validation: {validation_summary['passed_checks']}/{validation_summary['total_checks']} checks passed "
                          f"({validation_summary['pass_rate']:.1%})")
                
                if validation_summary['failed_checks'] > 0:
                    logger.warning(f"    Failed checks by category: {validation_summary['failed_by_category']}")
        
        # Export to CSV
        logger.info(f"Exporting data to CSV: {args.output}")
        csv_path = pipeline.export_to_csv(
            commodity_code=ALL_WHEAT_COMMODITY_CODE,
            output_path=args.output
        )
        
        logger.info(f"✅ Data exported successfully to: {csv_path}")
        
        # Show database stats if requested
        if args.stats:
            logger.info("Database Statistics:")
            stats = pipeline.get_database_stats()
            logger.info(f"  - Total records: {stats['total_records']}")
            logger.info(f"  - Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            logger.info(f"  - Metadata entries: {stats['metadata_entries']}")
            
            if stats['records_by_commodity_year']:
                logger.info("  - Records by commodity/year:")
                for commodity, year, count in stats['records_by_commodity_year']:
                    logger.info(f"    {commodity} ({year}): {count} records")
        
        logger.info("=== ESR Export Pace Tracker Completed Successfully ===")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 130
        
    except ESRAPIError as e:
        logger.error(f"API Error: {e}")
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
        
    finally:
        # Clean up resources
        if pipeline:
            try:
                pipeline.close()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    sys.exit(main())