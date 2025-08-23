#!/usr/bin/env python3
"""Get current cumulative exports for all wheat grades."""

import sqlite3
import pandas as pd
from datetime import datetime

def get_current_exports():
    """Retrieve and display current cumulative exports for all wheat grades."""
    
    # Connect to database
    conn = sqlite3.connect('data/esr_data.db')

    # Wheat class mapping
    wheat_classes = {
        101: 'Hard Red Winter (HRW)',
        102: 'Soft Red Winter (SRW)', 
        103: 'Hard Red Spring (HRS)',
        104: 'White Wheat',
        105: 'Durum Wheat',
        106: 'Mixed Wheat',
        107: 'All Wheat'
    }

    print('🌾 Current Cumulative Wheat Exports by Grade')
    print('=' * 70)

    results = []

    for code, name in wheat_classes.items():
        try:
            # Get the most recent data for each commodity
            query = '''
            SELECT 
                commodity_code,
                market_year,
                week_ending,
                accumulated_exports_mt,
                outstanding_sales_mt,
                total_commitment_mt,
                CAST((julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1 AS INTEGER) as marketing_week
            FROM fact_esr_world_weekly 
            WHERE commodity_code = ?
            ORDER BY market_year DESC, week_ending DESC 
            LIMIT 1
            '''
            
            df = pd.read_sql_query(query, conn, params=(code,))
            
            if not df.empty:
                row = df.iloc[0]
                results.append({
                    'code': code,
                    'name': name,
                    'market_year': int(row['market_year']),
                    'week_ending': row['week_ending'],
                    'marketing_week': int(row['marketing_week']),
                    'accumulated_exports_mt': row['accumulated_exports_mt'],
                    'outstanding_sales_mt': row['outstanding_sales_mt'],
                    'total_commitment_mt': row['total_commitment_mt']
                })
            else:
                print(f'❌ {name} ({code}): No data available')
                
        except Exception as e:
            print(f'❌ {name} ({code}): Error - {e}')

    conn.close()

    # Sort by accumulated exports (descending)
    results.sort(key=lambda x: x['accumulated_exports_mt'], reverse=True)

    print(f'\n📊 Latest Cumulative Export Data:\n')
    
    # Header
    print(f"{'Rank':<4} {'Code':<4} {'Wheat Grade':<25} {'MY':<4} {'Week':<4} {'Accumulated':<12} {'Outstanding':<12} {'Total Comm.':<12} {'As of Date'}")
    print('-' * 115)

    total_accumulated = 0
    total_outstanding = 0 
    total_commitment = 0

    for i, result in enumerate(results, 1):
        accumulated_millions = result['accumulated_exports_mt'] / 1_000_000
        outstanding_millions = result['outstanding_sales_mt'] / 1_000_000
        commitment_millions = result['total_commitment_mt'] / 1_000_000
        
        print(f"{i:<4} {result['code']:<4} {result['name']:<25} {result['market_year']:<4} {result['marketing_week']:<4} "
              f"{accumulated_millions:<11.1f}M {outstanding_millions:<11.1f}M {commitment_millions:<11.1f}M {result['week_ending']}")
        
        # Only sum individual classes (not All Wheat aggregate)  
        if result['code'] != 107:
            total_accumulated += result['accumulated_exports_mt']
            total_outstanding += result['outstanding_sales_mt']
            total_commitment += result['total_commitment_mt']

    print('-' * 115)
    print(f"{'Total Individual Classes:':<38} {total_accumulated/1_000_000:<11.1f}M {total_outstanding/1_000_000:<11.1f}M {total_commitment/1_000_000:<11.1f}M")

    print(f'\n🎯 Key Metrics:')
    for result in results:
        if result['name'] == 'All Wheat':
            print(f'   • All Wheat (Aggregate): {result["accumulated_exports_mt"]/1_000_000:.1f}M MT (MY {result["market_year"]}, Week {result["marketing_week"]})')
            break

    # Show percentage breakdown of individual classes
    print(f'\n📈 Grade Composition (Individual Classes Only):')
    individual_classes = [r for r in results if r['code'] != 107]
    if individual_classes and total_accumulated > 0:
        for result in individual_classes:
            percentage = (result['accumulated_exports_mt'] / total_accumulated) * 100
            print(f'   • {result["name"]:<25} {percentage:>5.1f}% ({result["accumulated_exports_mt"]/1_000_000:.1f}M MT)')
    
    # Show data currency
    print(f'\n📅 Data Currency:')
    data_years = set(r['market_year'] for r in results)
    current_year = max(data_years)
    historical_years = [y for y in data_years if y < current_year]
    
    if historical_years:
        print(f'   • Current Year Data (MY {current_year}): {len([r for r in results if r["market_year"] == current_year])} commodities')
        print(f'   • Historical Data: {len([r for r in results if r["market_year"] < current_year])} commodities from MY {min(historical_years)}-{max(historical_years)}')
    
    return results

if __name__ == "__main__":
    get_current_exports()