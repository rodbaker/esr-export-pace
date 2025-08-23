"""Data validation and quality checks for ESR data."""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, check_name: str, passed: bool, 
                 message: str = "", details: Optional[Dict[str, Any]] = None):
        self.check_name = check_name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"ValidationResult({self.check_name}: {status} - {self.message})"


class ESRDataValidator:
    """Comprehensive validation for ESR export data."""
    
    def __init__(self, fail_on_structural_errors: bool = True):
        """Initialize validator.
        
        Args:
            fail_on_structural_errors: Whether to raise exceptions on structural failures
        """
        self.fail_on_structural_errors = fail_on_structural_errors
        self.results: List[ValidationResult] = []
    
    def _add_result(self, result: ValidationResult):
        """Add validation result and optionally raise exception."""
        self.results.append(result)
        logger.debug(f"Validation check {result.check_name}: {'PASS' if result.passed else 'FAIL'}")
        
        if not result.passed:
            logger.warning(f"Validation failed: {result.check_name} - {result.message}")
            if self.fail_on_structural_errors and "structural" in result.check_name.lower():
                raise ValidationError(f"Structural validation failed: {result.message}")
    
    def validate_structural(self, df: pd.DataFrame, 
                           expected_commodity: Optional[int] = None,
                           expected_market_year: Optional[int] = None) -> List[ValidationResult]:
        """Core structural validation - fail fast if these fail.
        
        Args:
            df: DataFrame to validate
            expected_commodity: Expected commodity code
            expected_market_year: Expected market year
            
        Returns:
            List of validation results
        """
        results = []
        
        # Required columns check
        required_cols = [
            'commodityCode', 'countryCode', 'weekEndingDate', 'unitId',
            'weeklyExports', 'accumulatedExports', 'outstandingSales', 
            'currentMYNetSales', 'currentMYTotalCommitment'
        ]
        
        missing_cols = set(required_cols) - set(df.columns)
        result = ValidationResult(
            "structural_required_columns",
            len(missing_cols) == 0,
            f"Missing columns: {missing_cols}" if missing_cols else "All required columns present",
            {"missing_columns": list(missing_cols)}
        )
        results.append(result)
        self._add_result(result)
        
        if not result.passed:
            return results
        
        # Primary key uniqueness check
        pk_cols = ['commodityCode', 'countryCode', 'weekEndingDate']
        if all(col in df.columns for col in pk_cols):
            duplicates = df.duplicated(subset=pk_cols).sum()
            result = ValidationResult(
                "structural_primary_key_unique",
                duplicates == 0,
                f"Found {duplicates} duplicate primary keys" if duplicates > 0 else "Primary keys are unique",
                {"duplicate_count": duplicates}
            )
            results.append(result)
            self._add_result(result)
        
        # Thursday dates validation
        if 'weekEndingDate' in df.columns:
            df_dates = pd.to_datetime(df['weekEndingDate'])
            thursdays = df_dates.dt.dayofweek == 3  # Thursday = 3
            non_thursdays = (~thursdays).sum()
            
            result = ValidationResult(
                "structural_thursday_dates",
                non_thursdays == 0,
                f"Found {non_thursdays} non-Thursday dates" if non_thursdays > 0 else "All dates are Thursdays",
                {"non_thursday_count": non_thursdays}
            )
            results.append(result)
            self._add_result(result)
        
        # Unit ID consistency (should be 1 for wheat)
        if 'unitId' in df.columns:
            unit_ids = df['unitId'].unique()
            non_metric_tons = df[df['unitId'] != 1].shape[0]
            
            result = ValidationResult(
                "structural_unit_id_consistency",
                non_metric_tons == 0,
                f"Found {non_metric_tons} records with unitId != 1 (non-metric tons)" if non_metric_tons > 0 
                else "All records use metric tons (unitId=1)",
                {"unit_ids": unit_ids.tolist(), "non_metric_count": non_metric_tons}
            )
            results.append(result)
            self._add_result(result)
        
        # Commodity code consistency
        if expected_commodity and 'commodityCode' in df.columns:
            wrong_commodity = df[df['commodityCode'] != expected_commodity].shape[0]
            
            result = ValidationResult(
                "structural_commodity_consistency", 
                wrong_commodity == 0,
                f"Found {wrong_commodity} records with wrong commodity code" if wrong_commodity > 0
                else f"All records match expected commodity {expected_commodity}",
                {"expected_commodity": expected_commodity, "wrong_commodity_count": wrong_commodity}
            )
            results.append(result)
            self._add_result(result)
        
        # Date range bounds (within reasonable limits)
        if 'weekEndingDate' in df.columns:
            df_dates = pd.to_datetime(df['weekEndingDate'])
            min_date = df_dates.min()
            max_date = df_dates.max()
            current_date = datetime.now()
            
            # Check for future dates beyond next week
            future_cutoff = current_date + timedelta(days=7)
            future_dates = (df_dates > future_cutoff).sum()
            
            # Check for very old dates (before 1990)
            old_cutoff = datetime(1990, 1, 1)
            old_dates = (df_dates < old_cutoff).sum()
            
            result = ValidationResult(
                "structural_date_bounds",
                future_dates == 0 and old_dates == 0,
                f"Found {future_dates} future dates and {old_dates} pre-1990 dates" 
                if (future_dates > 0 or old_dates > 0) else "All dates within reasonable bounds",
                {
                    "min_date": min_date.isoformat(),
                    "max_date": max_date.isoformat(), 
                    "future_count": future_dates,
                    "old_count": old_dates
                }
            )
            results.append(result)
            self._add_result(result)
        
        return results
    
    def validate_arithmetic(self, df: pd.DataFrame) -> List[ValidationResult]:
        """Arithmetic validation - warn on failures.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        # Total commitment math: totalCommitment = accumulated + outstanding
        if all(col in df.columns for col in ['accumulatedExports', 'outstandingSales', 'currentMYTotalCommitment']):
            df_clean = df.copy()
            
            # Handle null values by treating as 0
            for col in ['accumulatedExports', 'outstandingSales', 'currentMYTotalCommitment']:
                df_clean[col] = df_clean[col].fillna(0)
            
            calculated_total = df_clean['accumulatedExports'] + df_clean['outstandingSales']
            commitment_diff = abs(calculated_total - df_clean['currentMYTotalCommitment'])
            
            # Allow small tolerance for floating point precision
            tolerance = 0.01
            math_errors = (commitment_diff > tolerance).sum()
            
            result = ValidationResult(
                "arithmetic_total_commitment_math",
                math_errors == 0,
                f"Found {math_errors} records where totalCommitment != accumulated + outstanding" 
                if math_errors > 0 else "All total commitment calculations are correct",
                {"math_errors": math_errors, "max_difference": commitment_diff.max()}
            )
            results.append(result)
            self._add_result(result)
        
        # Non-negative constraints
        non_negative_cols = ['weeklyExports', 'accumulatedExports', 'outstandingSales']
        available_cols = [col for col in non_negative_cols if col in df.columns]
        
        for col in available_cols:
            negative_count = (df[col].fillna(0) < 0).sum()
            
            result = ValidationResult(
                f"arithmetic_non_negative_{col.lower()}",
                negative_count == 0,
                f"Found {negative_count} negative values in {col}" if negative_count > 0 
                else f"All {col} values are non-negative",
                {"negative_count": negative_count, "column": col}
            )
            results.append(result)
            self._add_result(result)
        
        # Monotonic accumulated exports within commodity/marketing year
        if all(col in df.columns for col in ['commodityCode', 'weekEndingDate', 'accumulatedExports']):
            df_sorted = df.sort_values(['commodityCode', 'weekEndingDate'])
            
            violations = 0
            for commodity in df_sorted['commodityCode'].unique():
                commodity_data = df_sorted[df_sorted['commodityCode'] == commodity]
                accumulated = commodity_data['accumulatedExports'].fillna(0)
                
                # Check if accumulated exports are monotonic (non-decreasing)
                decreases = (accumulated.diff() < -tolerance).sum()
                violations += decreases
            
            result = ValidationResult(
                "arithmetic_monotonic_accumulated",
                violations == 0,
                f"Found {violations} decreases in accumulated exports" if violations > 0
                else "Accumulated exports are monotonic within each commodity",
                {"monotonic_violations": violations}
            )
            results.append(result)
            self._add_result(result)
        
        return results
    
    def validate_business_logic(self, df: pd.DataFrame) -> List[ValidationResult]:
        """Business rule validation - log warnings.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        # Volume range checks (extreme values for wheat)
        if 'weeklyExports' in df.columns:
            weekly_exports = df['weeklyExports'].fillna(0)
            max_reasonable = 5_000_000  # 5M MT per week is extremely high
            extreme_values = (weekly_exports > max_reasonable).sum()
            
            result = ValidationResult(
                "business_weekly_export_ranges",
                extreme_values == 0,
                f"Found {extreme_values} weekly export values > {max_reasonable:,} MT" 
                if extreme_values > 0 else "Weekly export volumes are within reasonable ranges",
                {
                    "extreme_count": extreme_values, 
                    "max_value": float(weekly_exports.max()),
                    "threshold": max_reasonable
                }
            )
            results.append(result)
            self._add_result(result)
        
        # Country coverage consistency (each week should have similar number of countries)
        if all(col in df.columns for col in ['weekEndingDate', 'countryCode']):
            countries_per_week = df.groupby('weekEndingDate')['countryCode'].nunique()
            
            if len(countries_per_week) > 1:
                mean_countries = countries_per_week.mean()
                std_countries = countries_per_week.std()
                
                # Flag weeks with very different country counts
                threshold = 2 * std_countries if std_countries > 0 else 0
                outlier_weeks = (abs(countries_per_week - mean_countries) > threshold).sum()
                
                result = ValidationResult(
                    "business_country_coverage_consistency",
                    outlier_weeks <= len(countries_per_week) * 0.1,  # Allow up to 10% of weeks to be outliers
                    f"Found {outlier_weeks} weeks with unusual country coverage" 
                    if outlier_weeks > len(countries_per_week) * 0.1 
                    else "Country coverage is consistent across weeks",
                    {
                        "outlier_weeks": outlier_weeks,
                        "mean_countries": float(mean_countries),
                        "std_countries": float(std_countries)
                    }
                )
                results.append(result)
                self._add_result(result)
        
        # Outlier detection in weekly exports (statistical)
        if 'weeklyExports' in df.columns:
            weekly_exports = df['weeklyExports'].fillna(0)
            if len(weekly_exports) > 10:  # Need sufficient data for statistical analysis
                mean_exports = weekly_exports.mean()
                std_exports = weekly_exports.std()
                
                if std_exports > 0:
                    # Values more than 3 standard deviations from mean
                    outliers = abs((weekly_exports - mean_exports) / std_exports) > 3
                    outlier_count = outliers.sum()
                    
                    result = ValidationResult(
                        "business_statistical_outliers",
                        outlier_count <= len(weekly_exports) * 0.05,  # Allow up to 5% outliers
                        f"Found {outlier_count} statistical outliers in weekly exports" 
                        if outlier_count > len(weekly_exports) * 0.05
                        else "Weekly exports follow expected statistical distribution",
                        {
                            "outlier_count": outlier_count,
                            "outlier_percentage": float(outlier_count / len(weekly_exports) * 100)
                        }
                    )
                    results.append(result)
                    self._add_result(result)
        
        return results
    
    def validate_aggregation(self, raw_data: pd.DataFrame, 
                           aggregated_data: pd.DataFrame) -> List[ValidationResult]:
        """Validate world aggregation calculations.
        
        Args:
            raw_data: Original country-level data
            aggregated_data: World-aggregated data
            
        Returns:
            List of validation results
        """
        results = []
        
        if 'weekEndingDate' not in raw_data.columns or 'week_ending' not in aggregated_data.columns:
            result = ValidationResult(
                "aggregation_missing_date_columns",
                False,
                "Missing date columns for aggregation validation",
                {}
            )
            results.append(result)
            self._add_result(result)
            return results
        
        # Check that each week in aggregated data matches sum of countries
        raw_data['weekEndingDate'] = pd.to_datetime(raw_data['weekEndingDate'])
        aggregated_data['week_ending'] = pd.to_datetime(aggregated_data['week_ending'])
        
        validation_cols = [
            ('weeklyExports', 'weekly_exports_mt'),
            ('accumulatedExports', 'accumulated_exports_mt'), 
            ('outstandingSales', 'outstanding_sales_mt'),
            ('currentMYNetSales', 'net_sales_mt'),
            ('currentMYTotalCommitment', 'total_commitment_mt')
        ]
        
        aggregation_errors = 0
        tolerance = 0.01
        
        for week in aggregated_data['week_ending'].unique():
            week_raw = raw_data[raw_data['weekEndingDate'] == week]
            week_agg = aggregated_data[aggregated_data['week_ending'] == week]
            
            if len(week_agg) != 1:
                aggregation_errors += 1
                continue
                
            agg_row = week_agg.iloc[0]
            
            for raw_col, agg_col in validation_cols:
                if raw_col in week_raw.columns and agg_col in agg_row:
                    raw_sum = week_raw[raw_col].fillna(0).sum()
                    agg_value = agg_row[agg_col]
                    
                    if abs(raw_sum - agg_value) > tolerance:
                        aggregation_errors += 1
                        break
        
        result = ValidationResult(
            "aggregation_world_totals_match",
            aggregation_errors == 0,
            f"Found {aggregation_errors} aggregation mismatches" if aggregation_errors > 0
            else "World totals match sum of country data",
            {"aggregation_errors": aggregation_errors}
        )
        results.append(result)
        self._add_result(result)
        
        return results
    
    def validate_all(self, df: pd.DataFrame, 
                    expected_commodity: Optional[int] = None,
                    expected_market_year: Optional[int] = None,
                    raw_data: Optional[pd.DataFrame] = None) -> Dict[str, List[ValidationResult]]:
        """Run all validation checks.
        
        Args:
            df: DataFrame to validate
            expected_commodity: Expected commodity code
            expected_market_year: Expected market year
            raw_data: Original raw data for aggregation validation
            
        Returns:
            Dictionary of validation results by category
        """
        self.results = []  # Reset results
        
        validation_results = {
            'structural': self.validate_structural(df, expected_commodity, expected_market_year),
            'arithmetic': self.validate_arithmetic(df),
            'business_logic': self.validate_business_logic(df)
        }
        
        if raw_data is not None:
            validation_results['aggregation'] = self.validate_aggregation(raw_data, df)
        
        return validation_results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of validation results.
        
        Returns:
            Dictionary with validation summary
        """
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks
        
        failed_by_category = {}
        for result in self.results:
            if not result.passed:
                category = result.check_name.split('_')[0]
                failed_by_category[category] = failed_by_category.get(category, 0) + 1
        
        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'failed_by_category': failed_by_category,
            'timestamp': datetime.now().isoformat()
        }
