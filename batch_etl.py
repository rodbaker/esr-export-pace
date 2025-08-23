#!/usr/bin/env python3
"""
ESR Export Pace Tracker - Batch ETL Script

Process multiple wheat commodity classes in sequence through the ETL pipeline.
This script loads all enabled commodities from configuration and processes them.

Usage:
    python batch_etl.py [--force-refresh] [--verbose] [--include CODES] [--exclude CODES]
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

from src.esr_pace.etl import ESRETLPipeline
from src.esr_pace.api_client import ESRAPIError
from src.esr_pace.config import config_manager


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('batch_esr_etl.log')
        ]
    )
    
    # Reduce noise from requests library
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def parse_commodity_codes(codes_str: str) -> Set[int]:
    """Parse comma-separated commodity codes from command line."""
    if not codes_str:
        return set()
    
    codes = set()
    for code_str in codes_str.split(','):
        code_str = code_str.strip()
        if code_str:
            try:
                codes.add(int(code_str))
            except ValueError:
                raise ValueError(f"Invalid commodity code: {code_str}")
    
    return codes


def filter_commodities(all_commodities: List, include_codes: Set[int], exclude_codes: Set[int]) -> List:
    """Filter commodities based on include/exclude criteria."""
    filtered = []
    
    for commodity in all_commodities:
        # Apply include filter (if specified)
        if include_codes and commodity.code not in include_codes:
            continue
            
        # Apply exclude filter
        if exclude_codes and commodity.code in exclude_codes:
            continue
            
        filtered.append(commodity)
    
    return filtered


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ESR Export Pace Tracker - Batch process multiple wheat commodities"
    )
    
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force data refresh even if current data exists'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    parser.add_argument(
        '--include',
        type=str,
        help='Comma-separated list of commodity codes to include (e.g., "101,102,107")'
    )
    
    parser.add_argument(
        '--exclude',
        type=str,
        help='Comma-separated list of commodity codes to exclude (e.g., "106")'
    )
    
    parser.add_argument(
        '--list-commodities',
        action='store_true',
        help='List available commodities and exit'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show which commodities would be processed without running ETL'
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
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory for CSV exports (default: output)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Handle list commodities command
    if args.list_commodities:
        logger.info("Available commodities:")
        try:
            all_commodities = config_manager.load_config().commodities
            for commodity in all_commodities:
                status = "✅" if commodity.enabled else "❌"
                desc = f" - {commodity.description}" if commodity.description else ""
                logger.info(f"  {status} {commodity.code}: {commodity.name}{desc}")
        except Exception as e:
            logger.error(f"Failed to load commodities configuration: {e}")
            return 1
        return 0
    
    logger.info("=== ESR Batch ETL Processor Started ===")
    
    # Parse include/exclude filters
    try:
        include_codes = parse_commodity_codes(args.include) if args.include else set()
        exclude_codes = parse_commodity_codes(args.exclude) if args.exclude else set()
    except ValueError as e:
        logger.error(f"Failed to parse commodity codes: {e}")
        return 1
    
    # Load and filter commodities
    try:
        enabled_commodities = config_manager.get_enabled_commodities()
        target_commodities = filter_commodities(enabled_commodities, include_codes, exclude_codes)
        
        if not target_commodities:
            logger.error("No commodities selected for processing")
            logger.info("Use --list-commodities to see available options")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to load commodities configuration: {e}")
        return 1
    
    logger.info(f"Selected {len(target_commodities)} commodities for processing:")
    for commodity in target_commodities:
        desc = f" - {commodity.description}" if commodity.description else ""
        logger.info(f"  • {commodity.code}: {commodity.name}{desc}")
    
    # Handle dry run
    if args.dry_run:
        logger.info("Dry run completed - no data was processed")
        return 0
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pipeline = None
    results_summary = {
        'total_commodities': len(target_commodities),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    try:
        # Get API key from argument or environment variable
        api_key = args.api_key or os.getenv('ESR_API_KEY')
        
        if not api_key:
            logger.error("API key is required. Provide it via --api-key argument or ESR_API_KEY environment variable.")
            return 1
        
        # Initialize ETL pipeline
        logger.info("Initializing ETL pipeline...")
        pipeline = ESRETLPipeline(api_key=api_key)
        
        start_time = datetime.now()
        
        # Process each commodity
        for i, commodity in enumerate(target_commodities, 1):
            logger.info(f"\n[{i}/{len(target_commodities)}] Processing {commodity.name} (code: {commodity.code})")
            
            try:
                # Run ETL for this commodity
                results = pipeline.run_etl(
                    commodity_code=commodity.code,
                    force_refresh=args.force_refresh,
                    validate_data=True
                )
                
                if results['success']:
                    if results.get('skipped'):
                        logger.info(f"✓ Skipped {commodity.name}: {results.get('message', 'Data is current')}")
                        results_summary['skipped'] += 1
                    else:
                        logger.info(f"✅ Successfully processed {commodity.name}:")
                        logger.info(f"    Records processed: {results['records_processed']}")
                        logger.info(f"    Records loaded: {results['records_loaded']}")
                        logger.info(f"    Duration: {results['duration_seconds']:.2f}s")
                        
                        # Export to CSV
                        csv_filename = f"commodity_{commodity.code}_{commodity.name.lower().replace(' ', '_').replace('-', '_')}_exports.csv"
                        csv_path = output_dir / csv_filename
                        
                        try:
                            exported_path = pipeline.export_to_csv(
                                commodity_code=commodity.code,
                                output_path=str(csv_path)
                            )
                            logger.info(f"    Exported to: {exported_path}")
                        except Exception as e:
                            logger.warning(f"    CSV export failed: {e}")
                        
                        results_summary['successful'] += 1
                else:
                    error_msg = results.get('error', 'Unknown error')
                    logger.error(f"❌ Failed to process {commodity.name}: {error_msg}")
                    results_summary['failed'] += 1
                    results_summary['errors'].append(f"{commodity.name}: {error_msg}")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Exception processing {commodity.name}: {error_msg}")
                results_summary['failed'] += 1
                results_summary['errors'].append(f"{commodity.name}: {error_msg}")
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Print summary
        logger.info(f"\n=== Batch ETL Processing Summary ===")
        logger.info(f"Total duration: {total_duration:.1f}s")
        logger.info(f"Commodities processed: {results_summary['total_commodities']}")
        logger.info(f"  ✅ Successful: {results_summary['successful']}")
        logger.info(f"  ⏭️  Skipped: {results_summary['skipped']}")
        logger.info(f"  ❌ Failed: {results_summary['failed']}")
        
        if results_summary['errors']:
            logger.error(f"\nErrors encountered:")
            for error in results_summary['errors']:
                logger.error(f"  • {error}")
        
        # Show database stats if requested
        if args.stats:
            logger.info("\nDatabase Statistics:")
            try:
                stats = pipeline.get_database_stats()
                logger.info(f"  Total records: {stats['total_records']}")
                logger.info(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
                logger.info(f"  Metadata entries: {stats['metadata_entries']}")
                
                if stats['records_by_commodity_year']:
                    logger.info("  Records by commodity/year:")
                    for commodity_code, year, count in stats['records_by_commodity_year']:
                        commodity_name = config_manager.get_commodity_name(commodity_code)
                        logger.info(f"    {commodity_name} ({year}): {count} records")
            except Exception as e:
                logger.warning(f"Failed to get database statistics: {e}")
        
        # Determine exit code
        if results_summary['failed'] > 0:
            logger.warning("=== Batch Processing Completed with Errors ===")
            return 1
        else:
            logger.info("=== Batch Processing Completed Successfully ===")
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