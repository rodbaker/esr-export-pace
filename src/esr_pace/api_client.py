"""USDA ESR API client with retry logic and error handling."""

import requests
import time
import random
import logging
from typing import Dict, List, Optional, Any


logger = logging.getLogger(__name__)


class ESRAPIError(Exception):
    """Base exception for ESR API errors."""
    pass


class ESRAPIClient:
    """USDA ESR API client with retry logic and rate limiting."""
    
    def __init__(self, 
                 base_url: str = "https://api.fas.usda.gov",
                 api_key: Optional[str] = None,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 connection_timeout: float = 10.0,
                 read_timeout: float = 30.0,
                 request_delay: float = 1.0):
        """Initialize ESR API client.
        
        Args:
            base_url: Base URL for USDA ESR API
            api_key: API key for authentication (required for most endpoints)
            max_retries: Maximum number of retries for failed requests
            base_delay: Base delay in seconds for retry backoff
            backoff_factor: Multiplier for exponential backoff
            jitter: Whether to add jitter to retry delays
            connection_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            request_delay: Delay between requests to be respectful
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.request_delay = request_delay
        
        self.session = requests.Session()
        headers = {
            'User-Agent': 'ESR-Export-Pace-Tracker/1.0',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        }
        
        # Add API key to headers if provided
        # Try different common API key header formats
        if self.api_key:
            headers['API_KEY'] = self.api_key
            headers['X-API-Key'] = self.api_key
            headers['Authorization'] = f'Bearer {self.api_key}'
            
        self.session.headers.update(headers)
        
    def _should_retry(self, response: Optional[requests.Response], 
                     exception: Optional[Exception]) -> bool:
        """Determine if a request should be retried."""
        if exception:
            # Retry on connection errors, timeouts, DNS failures
            if isinstance(exception, (requests.exceptions.ConnectionError,
                                    requests.exceptions.Timeout,
                                    requests.exceptions.RequestException)):
                return True
            return False
            
        if response is None:
            return False
            
        # Retry on server errors and rate limiting
        if response.status_code >= 500 or response.status_code == 429:
            return True
            
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and optional jitter."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        if self.jitter:
            delay *= random.uniform(0.5, 1.5)
        return delay
    
    def _make_request(self, endpoint: str) -> List[Dict[str, Any]]:
        """Make HTTP request with retry logic.
        
        Args:
            endpoint: API endpoint (without base URL)
            
        Returns:
            List of dictionaries from API response
            
        Raises:
            ESRAPIError: For API errors or validation failures
        """
        url = f"{self.base_url}{endpoint}"
        
        # Add API key as query parameter if provided
        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
            
        last_exception = None
        last_response = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url,
                    params=params,
                    timeout=(self.connection_timeout, self.read_timeout)
                )
                
                # Don't retry on 4xx errors (except 429)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    response.raise_for_status()
                
                response.raise_for_status()
                
                # Validate JSON response
                try:
                    data = response.json()
                except ValueError as e:
                    logger.error(f"Invalid JSON response from {url}: {e}")
                    raise ESRAPIError(f"Invalid JSON response: {e}")
                
                # Validate response is a list
                if not isinstance(data, list):
                    logger.error(f"Expected list response from {url}, got {type(data)}")
                    raise ESRAPIError(f"Expected list response, got {type(data)}")
                
                # Add delay between requests
                if attempt < self.max_retries:
                    time.sleep(self.request_delay)
                
                logger.debug(f"Successfully received {len(data)} records from {url}")
                return data
                
            except Exception as e:
                last_exception = e
                last_response = getattr(e, 'response', None)
                
                if not self._should_retry(last_response, e):
                    logger.error(f"Non-retryable error for {url}: {e}")
                    raise ESRAPIError(f"API request failed: {e}") from e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Request to {url} failed (attempt {attempt + 1}), "
                                 f"retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded for {url}: {e}")
                    break
        
        # All retries exhausted
        if last_response and last_response.status_code:
            raise ESRAPIError(f"API request failed after {self.max_retries} retries: "
                            f"HTTP {last_response.status_code}")
        else:
            raise ESRAPIError(f"API request failed after {self.max_retries} retries: "
                            f"{last_exception}")
    
    def get_data_release_dates(self) -> List[Dict[str, Any]]:
        """Get data release information for all commodities.
        
        Returns:
            List of release date records with fields:
            - commodityCode: int
            - marketYearStart: str (ISO datetime)
            - marketYearEnd: str (ISO datetime)  
            - marketYear: int (ending year)
            - releaseTimeStamp: str (ISO datetime)
        """
        return self._make_request("/api/esr/datareleasedates")
    
    def get_commodities(self) -> List[Dict[str, Any]]:
        """Get commodity reference data.
        
        Returns:
            List of commodity records with fields:
            - commodityCode: int
            - commodityName: str
            - unitId: int
        """
        return self._make_request("/api/esr/commodities")
    
    def get_countries(self) -> List[Dict[str, Any]]:
        """Get country reference data.
        
        Returns:
            List of country records with fields:
            - countryCode: int
            - countryName: str
            - countryDescription: str
            - regionId: int
            - gencCode: str or None
        """
        return self._make_request("/api/esr/countries")
    
    def get_units_of_measure(self) -> List[Dict[str, Any]]:
        """Get units of measure reference data.
        
        Returns:
            List of unit records with fields:
            - unitId: int
            - unitNames: str
        """
        return self._make_request("/api/esr/unitsOfMeasure")
    
    def get_export_data(self, commodity_code: int, market_year: int) -> List[Dict[str, Any]]:
        """Get weekly export data for a commodity and marketing year.
        
        Args:
            commodity_code: USDA commodity code (e.g., 107 for All Wheat)
            market_year: Marketing year (ending year, e.g., 2025 for 2024-2025 MY)
            
        Returns:
            List of export records with fields:
            - commodityCode: int
            - countryCode: int
            - weeklyExports: float or None (Metric Tons)
            - accumulatedExports: float or None (Metric Tons) 
            - outstandingSales: float or None (Metric Tons)
            - grossNewSales: float or None (Metric Tons)
            - currentMYNetSales: float or None (Metric Tons)
            - currentMYTotalCommitment: float or None (Metric Tons)
            - nextMYOutstandingSales: float or None (Metric Tons)
            - nextMYNetSales: float or None (Metric Tons)
            - unitId: int (should be 1 for wheat)
            - weekEndingDate: str (ISO datetime, should be Thursday)
        """
        endpoint = f"/api/esr/exports/commodityCode/{commodity_code}/allCountries/marketYear/{market_year}"
        return self._make_request(endpoint)
    
    def get_export_data_by_country(self, commodity_code: int, country_code: int, 
                                  market_year: int) -> List[Dict[str, Any]]:
        """Get weekly export data for a specific commodity, country, and marketing year.
        
        Args:
            commodity_code: USDA commodity code
            country_code: USDA country code  
            market_year: Marketing year (ending year)
            
        Returns:
            List of export records (same structure as get_export_data)
        """
        endpoint = f"/api/esr/exports/commodityCode/{commodity_code}/countryCode/{country_code}/marketYear/{market_year}"
        return self._make_request(endpoint)
    
    def get_release_info_for_commodity(self, commodity_code: int) -> Optional[Dict[str, Any]]:
        """Get release information for a specific commodity.
        
        Args:
            commodity_code: USDA commodity code
            
        Returns:
            Release info record or None if not found
        """
        all_releases = self.get_data_release_dates()
        for release in all_releases:
            if release.get('commodityCode') == commodity_code:
                return release
        return None
    
    def close(self):
        """Close the HTTP session."""
        if hasattr(self, 'session'):
            self.session.close()
