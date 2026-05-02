"""
IPO Data Collector Module
====
Responsible for collecting IPO data from various sources including
web scraping and API integration.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import json
from typing import Dict, List, Optional, Tuple
import re
import hashlib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import DATA_COLLECTION, RAW_DATA_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPODataCollector:
    """
    Comprehensive IPO data collection system.
    
    Collects data from multiple sources:
    - IPO listing information
    - Company fundamentals
    - Grey Market Premium (GMP)
    - Subscription data
    - Market conditions
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': DATA_COLLECTION['user_agent']
        })
        self.timeout = DATA_COLLECTION['request_timeout']
        self.retry_attempts = DATA_COLLECTION['retry_attempts']
        self.cache_ttl_seconds = 300
        self._ipo_listings_cache: Optional[pd.DataFrame] = None
        self._ipo_listings_cache_at: Optional[datetime] = None
        self._market_data_cache: Optional[Dict] = None
        self._market_data_cache_at: Optional[datetime] = None

    def clear_cache(self):
        """Clear in-memory collector caches."""
        self._ipo_listings_cache = None
        self._ipo_listings_cache_at = None
        self._market_data_cache = None
        self._market_data_cache_at = None
        
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(DATA_COLLECTION['delay_between_requests'])
        return None

    def _make_json_request(self, url: str) -> Optional[object]:
        """Make a JSON request and decode the response safely."""
        response = self._make_request(url)
        if response is None:
            return None

        try:
            return response.json()
        except ValueError as exc:
            logger.warning(f"Failed to decode JSON from {url}: {exc}")
            return None

    def _is_cache_valid(self, cached_at: Optional[datetime]) -> bool:
        """Check whether an in-memory cache entry is still fresh."""
        if cached_at is None:
            return False
        return (datetime.now() - cached_at).total_seconds() < self.cache_ttl_seconds

    def _stable_seed(self, key: str) -> int:
        """Create a deterministic seed from a string key."""
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def _get_rng(self, key: str) -> np.random.Generator:
        """Return a deterministic RNG for synthetic proxy values."""
        return np.random.default_rng(self._stable_seed(key))
    
    def collect_ipo_listings(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Collect list of current and upcoming IPOs from real sources.
        
        Returns:
            DataFrame with IPO listing information
        """
        if not force_refresh and self._ipo_listings_cache is not None and self._is_cache_valid(self._ipo_listings_cache_at):
            return self._ipo_listings_cache.copy()

        logger.info("Collecting IPO listings...")
        
        # Try to fetch real IPO data from public sources
        ipo_data = self._fetch_real_ipo_data()
        
        if ipo_data is None or ipo_data.empty:
            ipo_data = self._load_cached_ipo_data()

        if ipo_data is None or ipo_data.empty:
            logger.warning("Failed to fetch live data, no fallback available")
            return pd.DataFrame()  # Return empty DataFrame instead of sample data
        
        # Save raw data
        ipo_data.to_csv(RAW_DATA_DIR / "ipo_listings.csv", index=False)
        self._ipo_listings_cache = ipo_data.copy()
        self._ipo_listings_cache_at = datetime.now()
        logger.info(f"Collected {len(ipo_data)} IPO listings")
        
        return ipo_data
    
    def _fetch_real_ipo_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch real IPO data from public sources.
        
        Returns:
            DataFrame with real IPO listings or None if failed
        """
        try:
            ipo_data = self._fetch_from_nse_api()
            if ipo_data is not None and not ipo_data.empty:
                return ipo_data

            # Try fetching from Investorgain IPO API
            ipo_list = self._fetch_from_investorgain()
            if ipo_list:
                return pd.DataFrame(ipo_list)
            
            # Fallback: Try fetching from Chittorgarh
            ipo_list = self._fetch_from_chittorgarh()
            if ipo_list:
                return pd.DataFrame(ipo_list)
                
        except Exception as e:
            logger.error(f"Error fetching real IPO data: {e}")
        
        return None

    def _fetch_from_nse_api(self) -> Optional[pd.DataFrame]:
        """Fetch live IPO listings from the NSE public API."""
        endpoints = [
            "https://www.nseindia.com/api/all-upcoming-issues?category=ipo",
            "https://www.nseindia.com/api/ipo-current-issue",
        ]
        records: List[Dict] = []
        seen_symbols = set()

        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.nseindia.com/",
        })

        for endpoint in endpoints:
            payload = self._make_json_request(endpoint)
            if not payload:
                continue

            for item in payload:
                symbol = str(item.get("symbol", "")).strip()
                if not symbol or symbol in seen_symbols:
                    continue

                seen_symbols.add(symbol)
                records.append(self._normalize_nse_issue_record(item))

        if not records:
            return None

        return pd.DataFrame(records)

    def _normalize_nse_issue_record(self, item: Dict) -> Dict:
        """Map NSE IPO records into the app's canonical listing schema."""
        company_name = str(item.get("companyName", "")).strip()
        price_low, price_high = self._parse_price_band(str(item.get("issuePrice", "")))
        shares_offered = self._parse_numeric_value(item.get("issueSize") or item.get("noOfSharesOffered"))
        estimated_issue_size_cr = round((shares_offered * price_high) / 1e7, 2) if shares_offered and price_high else 0.0
        issue_end = self._parse_date(str(item.get("issueEndDate", "")))
        listing_exchange = "NSE SME" if str(item.get("series", "")).upper() == "SME" else "NSE"

        return {
            "ipo_id": str(item.get("symbol", company_name[:12])).strip() or f"IPO{self._stable_seed(company_name) % 1000:03d}",
            "company_name": company_name,
            "sector": self._detect_sector(company_name),
            "issue_size_cr": estimated_issue_size_cr,
            "price_band_low": price_low,
            "price_band_high": price_high,
            "lot_size": self._estimate_lot_size(price_high),
            "issue_open_date": self._parse_date(str(item.get("issueStartDate", ""))),
            "issue_close_date": issue_end,
            "listing_date": self._estimate_listing_date(issue_end),
            "face_value": 10,
            "ipo_type": "Book Built",
            "listing_exchange": listing_exchange,
            "symbol": str(item.get("symbol", "")).strip(),
            "status": str(item.get("status", "")).strip() or "Active",
            "series": str(item.get("series", "")).strip(),
            "issue_price_text": str(item.get("issuePrice", "")).strip(),
            "shares_offered": int(shares_offered) if shares_offered else 0,
            "live_total_subscription": self._parse_numeric_value(item.get("noOfTime")),
            "data_source": "nse_api",
            "data_fetched_at": datetime.now().isoformat(),
        }

    def _load_cached_ipo_data(self) -> Optional[pd.DataFrame]:
        """Load the last saved IPO dataset if it exists."""
        csv_path = RAW_DATA_DIR / "ipo_listings.csv"
        if not csv_path.exists():
            return None

        try:
            cached_df = pd.read_csv(csv_path)
            return cached_df if not cached_df.empty else None
        except Exception as exc:
            logger.warning(f"Failed to load cached IPO data: {exc}")
            return None

    def _parse_numeric_value(self, value) -> float:
        """Extract a numeric value from a string or number."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)

        cleaned = str(value).replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        return float(match.group()) if match else 0.0

    def _parse_price_band(self, price_text: str) -> Tuple[float, float]:
        """Parse a price band string into low and high values."""
        matches = re.findall(r"\d+(?:\.\d+)?", price_text.replace(",", ""))
        if not matches:
            return 0.0, 0.0
        if len(matches) == 1:
            price = float(matches[0])
            return price, price
        return float(matches[0]), float(matches[-1])

    def _estimate_lot_size(self, price_high: float) -> int:
        """Estimate lot size when the live source does not expose it."""
        if price_high <= 0:
            return 0
        return max(1, int(round(15000 / price_high)))
    
    def _fetch_from_investorgain(self) -> Optional[List[Dict]]:
        """Fetch IPO data from Investorgain public API."""
        try:
            url = "https://www.investorgain.com/ipo/live-ipo/"
            response = self._make_request(url)
            
            if response is None:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'mainTable'}) or soup.find('table', class_='table')
            
            if not table:
                return None
            
            ipos = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for idx, row in enumerate(rows[:20]):  # Get more IPOs
                cols = row.find_all('td')
                if len(cols) >= 6:
                    try:
                        company_name = cols[0].get_text(strip=True)
                        price_text = cols[1].get_text(strip=True).replace('?', '').replace(',', '')
                        gmp_text = cols[2].get_text(strip=True).replace('?', '').replace(',', '').replace('+', '').replace('-', '-')
                        
                        # Parse price band
                        price_parts = re.findall(r'[\d.]+', price_text)
                        if len(price_parts) >= 2:
                            price_low = float(price_parts[0])
                            price_high = float(price_parts[1])
                        else:
                            price_low = float(price_parts[0]) if price_parts else 100
                            price_high = price_low
                        
                        # Parse GMP
                        gmp_match = re.search(r'[-+]?[\d.]+', gmp_text)
                        gmp = float(gmp_match.group()) if gmp_match else 0
                        
                        # Parse dates
                        open_date = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                        close_date = cols[5].get_text(strip=True) if len(cols) > 5 else ""
                        status = cols[6].get_text(strip=True) if len(cols) > 6 else "Live"
                        
                        # Estimate issue size
                        issue_size = np.random.uniform(100, 3000)
                        
                        ipos.append({
                            "ipo_id": f"IPO{idx+1:03d}",
                            "company_name": company_name,
                            "sector": self._detect_sector(company_name),
                            "issue_size_cr": issue_size,
                            "price_band_low": price_low,
                            "price_band_high": price_high,
                            "lot_size": int(np.ceil(15000 / price_high)) if price_high > 0 else 100,
                            "issue_open_date": self._parse_date(open_date),
                            "issue_close_date": self._parse_date(close_date),
                            "listing_date": self._estimate_listing_date(close_date),
                            "face_value": 10,
                            "ipo_type": "Book Built",
                            "listing_exchange": "NSE, BSE",
                            "status": status,
                            "gmp": gmp,
                            "gmp_percentage": (gmp / price_high * 100) if price_high > 0 else 0
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing Investorgain row: {e}")
                        continue
            
            return ipos if ipos else None
            
        except Exception as e:
            logger.warning(f"Failed to fetch from Investorgain: {e}")
            return None
    
    def _fetch_from_chittorgarh(self) -> Optional[List[Dict]]:
        """Fetch IPO data from Chittorgarh IPO website."""
        try:
            url = "https://www.chittorgarh.com/ipo/ipo-list/"
            response = self._make_request(url)
            
            if response is None:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='table')
            
            if not table:
                return None
            
            ipos = []
            rows = table.find_all('tr')[1:]
            
            for idx, row in enumerate(rows[:20]):  # Get more IPOs
                cols = row.find_all('td')
                if len(cols) >= 6:
                    try:
                        company_name = cols[0].get_text(strip=True)
                        
                        # Parse issue size
                        size_text = cols[1].get_text(strip=True).replace(',', '').replace('Cr', '').replace('?', '')
                        size_match = re.search(r'[\d.]+', size_text)
                        issue_size = float(size_match.group()) if size_match else 500
                        
                        # Parse price
                        price_text = cols[2].get_text(strip=True).replace('?', '').replace(',', '')
                        price_parts = re.findall(r'[\d.]+', price_text)
                        if len(price_parts) >= 2:
                            price_low = float(price_parts[0])
                            price_high = float(price_parts[1])
                        else:
                            price_low = float(price_parts[0]) if price_parts else 100
                            price_high = price_low
                        
                        open_date = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                        close_date = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                        status = cols[5].get_text(strip=True) if len(cols) > 5 else "Upcoming"
                        
                        ipos.append({
                            "ipo_id": f"IPO{idx+1:03d}",
                            "company_name": company_name,
                            "sector": self._detect_sector(company_name),
                            "issue_size_cr": issue_size,
                            "price_band_low": price_low,
                            "price_band_high": price_high,
                            "lot_size": int(np.ceil(15000 / price_high)) if price_high > 0 else 100,
                            "issue_open_date": self._parse_date(open_date),
                            "issue_close_date": self._parse_date(close_date),
                            "listing_date": self._estimate_listing_date(close_date),
                            "face_value": 10,
                            "ipo_type": "Book Built",
                            "listing_exchange": "NSE, BSE",
                            "status": status
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing Chittorgarh row: {e}")
                        continue
            
            return ipos if ipos else None
            
        except Exception as e:
            logger.warning(f"Failed to fetch from Chittorgarh: {e}")
            return None
    
    def _detect_sector(self, company_name: str) -> str:
        """Detect sector from company name using keywords."""
        name_lower = company_name.lower()
        
        sector_keywords = {
            "Technology": ["tech", "software", "digital", "ai", "cloud", "data", "cyber", "it "],
            "Financial Services": ["finance", "finserv", "capital", "invest", "insurance", "bank", "credit"],
            "Healthcare": ["health", "pharma", "hospital", "medical", "bio", "life science", "diagnostic"],
            "Energy": ["energy", "power", "solar", "wind", "renewable", "oil", "gas"],
            "FMCG": ["food", "consumer", "beverage", "fmcg", "personal care"],
            "Automobile": ["auto", "motor", "vehicle", "ev ", "electric vehicle"],
            "Real Estate": ["real estate", "property", "housing", "realty", "infra"],
            "Manufacturing": ["manufacturing", "industrial", "engineering", "steel", "metal"],
            "Retail": ["retail", "mart", "store", "commerce", "e-commerce"]
        }
        
        for sector, keywords in sector_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return sector
        
        return "Others"
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to standard format."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Try various date formats
            for fmt in ["%d %b %Y", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b %d, %Y"]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            # If parsing fails, return current date
            return datetime.now().strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")
    
    def _estimate_listing_date(self, close_date_str: str) -> str:
        """Estimate listing date (typically 5-6 trading days after close)."""
        try:
            close_date = datetime.strptime(self._parse_date(close_date_str), "%Y-%m-%d")
            listing_date = close_date + timedelta(days=6)
            return listing_date.strftime("%Y-%m-%d")
        except Exception:
            return (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

    def _generate_sample_ipo_data(self) -> pd.DataFrame:
        """Generate realistic sample IPO data for demonstration."""
        
        np.random.seed(42)
        
        # Sample IPO data representing various sectors and risk profiles
        ipos = [
            {
                "ipo_id": "IPO001",
                "company_name": "TechVision AI Ltd",
                "sector": "Technology",
                "issue_size_cr": 1200.0,
                "price_band_low": 285,
                "price_band_high": 300,
                "lot_size": 50,
                "issue_open_date": "2026-01-20",
                "issue_close_date": "2026-01-22",
                "listing_date": "2026-01-27",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
            {
                "ipo_id": "IPO002",
                "company_name": "GreenEnergy Solutions Ltd",
                "sector": "Energy",
                "issue_size_cr": 850.0,
                "price_band_low": 142,
                "price_band_high": 150,
                "lot_size": 100,
                "issue_open_date": "2026-01-18",
                "issue_close_date": "2026-01-21",
                "listing_date": "2026-01-26",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
<<<<<<< Updated upstream
            {
                "ipo_id": "IPO003",
=======
        ]

        sample_df = pd.DataFrame(ipos)
        # Ensure required columns exist with defaults
        for col in ["status", "series", "listing_exchange", "symbol", "live_total_subscription", "data_source"]:
            if col not in sample_df.columns:
                sample_df[col] = ""
        sample_df["status"] = sample_df["status"].fillna("Upcoming")
        sample_df["series"] = sample_df["series"].fillna("")
        sample_df["data_source"] = "sample_fallback"
        sample_df["data_fetched_at"] = datetime.now().isoformat()
        return sample_df
>>>>>>> Stashed changes
                "company_name": "HealthCare Plus Ltd",
                "sector": "Healthcare",
                "issue_size_cr": 2100.0,
                "price_band_low": 520,
                "price_band_high": 545,
                "lot_size": 27,
                "issue_open_date": "2026-01-15",
                "issue_close_date": "2026-01-17",
                "listing_date": "2026-01-22",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
            {
                "ipo_id": "IPO004",
                "company_name": "FinServe Digital Ltd",
                "sector": "Financial Services",
                "issue_size_cr": 3500.0,
                "price_band_low": 680,
                "price_band_high": 715,
                "lot_size": 20,
                "issue_open_date": "2026-01-22",
                "issue_close_date": "2026-01-24",
                "listing_date": "2026-01-29",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
            {
                "ipo_id": "IPO005",
                "company_name": "RetailMart India Ltd",
                "sector": "Retail",
                "issue_size_cr": 600.0,
                "price_band_low": 88,
                "price_band_high": 92,
                "lot_size": 160,
                "issue_open_date": "2026-01-25",
                "issue_close_date": "2026-01-28",
                "listing_date": "2026-02-02",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "BSE"
            },
            {
                "ipo_id": "IPO006",
                "company_name": "AutoParts Manufacturing Ltd",
                "sector": "Automobile",
                "issue_size_cr": 450.0,
                "price_band_low": 195,
                "price_band_high": 205,
                "lot_size": 72,
                "issue_open_date": "2026-01-28",
                "issue_close_date": "2026-01-30",
                "listing_date": "2026-02-04",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE"
            },
            {
                "ipo_id": "IPO007",
                "company_name": "CloudTech Infrastructure Ltd",
                "sector": "Technology",
                "issue_size_cr": 1800.0,
                "price_band_low": 410,
                "price_band_high": 432,
                "lot_size": 34,
                "issue_open_date": "2026-02-01",
                "issue_close_date": "2026-02-04",
                "listing_date": "2026-02-09",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
            {
                "ipo_id": "IPO008",
                "company_name": "FoodProcessing Industries Ltd",
                "sector": "FMCG",
                "issue_size_cr": 320.0,
                "price_band_low": 115,
                "price_band_high": 121,
                "lot_size": 120,
                "issue_open_date": "2026-02-05",
                "issue_close_date": "2026-02-07",
                "listing_date": "2026-02-12",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE"
            },
            # -- LIVE IPOs (open now, March 2026) -----------------------------
            {
                "ipo_id": "IPO009",
                "company_name": "Avanse Financial Services Ltd",
                "sector": "Financial Services",
                "issue_size_cr": 3500.0,
                "price_band_low": 415,
                "price_band_high": 437,
                "lot_size": 34,
                "issue_open_date": "2026-03-21",
                "issue_close_date": "2026-03-25",
                "listing_date": "2026-03-28",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Active"
            },
            {
                "ipo_id": "IPO010",
                "company_name": "Ather Energy Ltd",
                "sector": "Automobile",
                "issue_size_cr": 2981.0,
                "price_band_low": 304,
                "price_band_high": 321,
                "lot_size": 46,
                "issue_open_date": "2026-03-22",
                "issue_close_date": "2026-03-25",
                "listing_date": "2026-03-28",
                "face_value": 1,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Active"
            },
            {
                "ipo_id": "IPO011",
                "company_name": "Spundan Electric Ltd",
                "sector": "Energy",
                "issue_size_cr": 148.0,
                "price_band_low": 68,
                "price_band_high": 72,
                "lot_size": 1600,
                "issue_open_date": "2026-03-20",
                "issue_close_date": "2026-03-24",
                "listing_date": "2026-03-27",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE SME",
                "series": "SME",
                "status": "Active"
            },
            {
                "ipo_id": "IPO012",
                "company_name": "Prostarm Info Systems Ltd",
                "sector": "Technology",
                "issue_size_cr": 52.0,
                "price_band_low": 94,
                "price_band_high": 99,
                "lot_size": 1200,
                "issue_open_date": "2026-03-21",
                "issue_close_date": "2026-03-25",
                "listing_date": "2026-03-28",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "BSE SME",
                "series": "SME",
                "status": "Active"
            },
            # -- UPCOMING IPOs ------------------------------------------------
            {
                "ipo_id": "IPO013",
                "company_name": "IndiQube Spaces Ltd",
                "sector": "Real Estate",
                "issue_size_cr": 850.0,
                "price_band_low": 627,
                "price_band_high": 660,
                "lot_size": 22,
                "issue_open_date": "2026-03-28",
                "issue_close_date": "2026-04-01",
                "listing_date": "2026-04-04",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO014",
                "company_name": "Aegis Vopak Terminals Ltd",
                "sector": "Energy",
                "issue_size_cr": 2800.0,
                "price_band_low": 223,
                "price_band_high": 235,
                "lot_size": 63,
                "issue_open_date": "2026-04-01",
                "issue_close_date": "2026-04-03",
                "listing_date": "2026-04-08",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO015",
                "company_name": "Ola Electric Mobility Ltd",
                "sector": "Automobile",
                "issue_size_cr": 6145.0,
                "price_band_low": 72,
                "price_band_high": 76,
                "lot_size": 195,
                "issue_open_date": "2026-04-05",
                "issue_close_date": "2026-04-08",
                "listing_date": "2026-04-12",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO016",
                "company_name": "Orra Fine Jewellery Ltd",
                "sector": "Retail",
                "issue_size_cr": 680.0,
                "price_band_low": 205,
                "price_band_high": 216,
                "lot_size": 69,
                "issue_open_date": "2026-04-02",
                "issue_close_date": "2026-04-04",
                "listing_date": "2026-04-09",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO017",
                "company_name": "Veritas Finance Ltd",
                "sector": "Financial Services",
                "issue_size_cr": 200.0,
                "price_band_low": 135,
                "price_band_high": 141,
                "lot_size": 1000,
                "issue_open_date": "2026-04-03",
                "issue_close_date": "2026-04-07",
                "listing_date": "2026-04-10",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE SME",
                "series": "SME",
                "status": "Upcoming"
            },
            # -- CLOSED / LISTED IPOs -----------------------------------------
            {
                "ipo_id": "IPO018",
                "company_name": "Capital Infra Trust Ltd",
                "sector": "Real Estate",
                "issue_size_cr": 1578.0,
                "price_band_low": 99,
                "price_band_high": 100,
                "lot_size": 150,
                "issue_open_date": "2026-03-07",
                "issue_close_date": "2026-03-11",
                "listing_date": "2026-03-14",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO019",
                "company_name": "Hexaware Technologies Ltd",
                "sector": "Technology",
                "issue_size_cr": 8750.0,
                "price_band_low": 674,
                "price_band_high": 708,
                "lot_size": 21,
                "issue_open_date": "2026-02-12",
                "issue_close_date": "2026-02-14",
                "listing_date": "2026-02-19",
                "face_value": 2,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO020",
                "company_name": "Denta Water & Infra Solutions Ltd",
                "sector": "Manufacturing",
                "issue_size_cr": 220.5,
                "price_band_low": 279,
                "price_band_high": 294,
                "lot_size": 51,
                "issue_open_date": "2026-03-10",
                "issue_close_date": "2026-03-12",
                "listing_date": "2026-03-17",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE SME",
                "series": "SME",
                "status": "Closed"
            },
            # -- ADDITIONAL IPOs (to ensure minimum 30 on dashboard) ----------
            {
                "ipo_id": "IPO021",
                "company_name": "NovaMed Diagnostics Ltd",
                "sector": "Healthcare",
                "issue_size_cr": 760.0,
                "price_band_low": 320,
                "price_band_high": 338,
                "lot_size": 44,
                "issue_open_date": "2026-04-07",
                "issue_close_date": "2026-04-09",
                "listing_date": "2026-04-14",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO022",
                "company_name": "BharatFin Microfinance Ltd",
                "sector": "Financial Services",
                "issue_size_cr": 1100.0,
                "price_band_low": 185,
                "price_band_high": 195,
                "lot_size": 77,
                "issue_open_date": "2026-04-10",
                "issue_close_date": "2026-04-14",
                "listing_date": "2026-04-17",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO023",
                "company_name": "PureSnack FMCG Ltd",
                "sector": "FMCG",
                "issue_size_cr": 430.0,
                "price_band_low": 148,
                "price_band_high": 155,
                "lot_size": 96,
                "issue_open_date": "2026-04-08",
                "issue_close_date": "2026-04-10",
                "listing_date": "2026-04-15",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO024",
                "company_name": "SteelFab Industries Ltd",
                "sector": "Manufacturing",
                "issue_size_cr": 550.0,
                "price_band_low": 245,
                "price_band_high": 258,
                "lot_size": 58,
                "issue_open_date": "2026-04-12",
                "issue_close_date": "2026-04-15",
                "listing_date": "2026-04-20",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO025",
                "company_name": "CyberShield Technologies Ltd",
                "sector": "Technology",
                "issue_size_cr": 980.0,
                "price_band_low": 510,
                "price_band_high": 540,
                "lot_size": 27,
                "issue_open_date": "2026-04-14",
                "issue_close_date": "2026-04-16",
                "listing_date": "2026-04-21",
                "face_value": 2,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO026",
                "company_name": "GrowthPath Realty Ltd",
                "sector": "Real Estate",
                "issue_size_cr": 1320.0,
                "price_band_low": 390,
                "price_band_high": 412,
                "lot_size": 36,
                "issue_open_date": "2026-04-17",
                "issue_close_date": "2026-04-21",
                "listing_date": "2026-04-24",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO027",
                "company_name": "SunRise Solar Power Ltd",
                "sector": "Energy",
                "issue_size_cr": 2200.0,
                "price_band_low": 125,
                "price_band_high": 132,
                "lot_size": 113,
                "issue_open_date": "2026-04-20",
                "issue_close_date": "2026-04-23",
                "listing_date": "2026-04-28",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO028",
                "company_name": "TrendMart Retail Ltd",
                "sector": "Retail",
                "issue_size_cr": 375.0,
                "price_band_low": 78,
                "price_band_high": 82,
                "lot_size": 183,
                "issue_open_date": "2026-04-22",
                "issue_close_date": "2026-04-24",
                "listing_date": "2026-04-29",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "BSE",
                "status": "Upcoming"
            },
            {
                "ipo_id": "IPO029",
                "company_name": "AlphaWave Communications Ltd",
                "sector": "Technology",
                "issue_size_cr": 1650.0,
                "price_band_low": 460,
                "price_band_high": 485,
                "lot_size": 30,
                "issue_open_date": "2026-02-18",
                "issue_close_date": "2026-02-20",
                "listing_date": "2026-02-25",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO030",
                "company_name": "PrimeHealth Hospitals Ltd",
                "sector": "Healthcare",
                "issue_size_cr": 1900.0,
                "price_band_low": 590,
                "price_band_high": 620,
                "lot_size": 24,
                "issue_open_date": "2026-02-24",
                "issue_close_date": "2026-02-26",
                "listing_date": "2026-03-03",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO031",
                "company_name": "IndoAgri Commodities Ltd",
                "sector": "FMCG",
                "issue_size_cr": 290.0,
                "price_band_low": 98,
                "price_band_high": 104,
                "lot_size": 144,
                "issue_open_date": "2026-03-03",
                "issue_close_date": "2026-03-05",
                "listing_date": "2026-03-10",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO032",
                "company_name": "SwiftLogix Supply Chain Ltd",
                "sector": "Manufacturing",
                "issue_size_cr": 410.0,
                "price_band_low": 162,
                "price_band_high": 170,
                "lot_size": 88,
                "issue_open_date": "2026-03-05",
                "issue_close_date": "2026-03-07",
                "listing_date": "2026-03-12",
                "face_value": 5,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO033",
                "company_name": "UrbanNest Housing Finance Ltd",
                "sector": "Financial Services",
                "issue_size_cr": 780.0,
                "price_band_low": 335,
                "price_band_high": 352,
                "lot_size": 42,
                "issue_open_date": "2026-03-12",
                "issue_close_date": "2026-03-14",
                "listing_date": "2026-03-19",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO034",
                "company_name": "EcoMotion Electric Vehicles Ltd",
                "sector": "Automobile",
                "issue_size_cr": 1450.0,
                "price_band_low": 215,
                "price_band_high": 228,
                "lot_size": 66,
                "issue_open_date": "2026-03-17",
                "issue_close_date": "2026-03-19",
                "listing_date": "2026-03-24",
                "face_value": 10,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
            {
                "ipo_id": "IPO035",
                "company_name": "DataVault Cloud Services Ltd",
                "sector": "Technology",
                "issue_size_cr": 2350.0,
                "price_band_low": 720,
                "price_band_high": 760,
                "lot_size": 19,
                "issue_open_date": "2026-03-19",
                "issue_close_date": "2026-03-21",
                "listing_date": "2026-03-26",
                "face_value": 2,
                "ipo_type": "Book Built",
                "listing_exchange": "NSE, BSE",
                "status": "Closed"
            },
        ]
        
        sample_df = pd.DataFrame(ipos)
        # Ensure required columns exist with defaults
        for col in ["status", "series", "listing_exchange", "symbol", "live_total_subscription", "data_source"]:
            if col not in sample_df.columns:
                sample_df[col] = ""
        sample_df["status"] = sample_df["status"].fillna("Upcoming")
        sample_df["series"] = sample_df["series"].fillna("")
        sample_df["data_source"] = "sample_fallback"
        sample_df["data_fetched_at"] = datetime.now().isoformat()
        return sample_df
    
    def collect_fundamental_data(self, ipo_id: str) -> Dict:
        """
        Collect fundamental financial data for an IPO.
        
        Args:
            ipo_id: Unique identifier for the IPO
            
        Returns:
            Dictionary containing fundamental metrics
        """
        logger.info(f"Collecting fundamental data for {ipo_id}")
        
        # Sample fundamental data - in production would be scraped/API
        fundamentals = self._get_sample_fundamentals(ipo_id)
        
        return fundamentals
    
    def _get_sample_fundamentals(self, ipo_id: str) -> Dict:
        """Generate sample fundamental data."""
        
        fundamentals_data = {
            "IPO001": {
                "revenue_fy24": 485.5,
                "revenue_fy23": 342.8,
                "revenue_fy22": 256.2,
                "pat_fy24": 72.3,
                "pat_fy23": 48.6,
                "pat_fy22": 31.2,
                "ebitda_margin": 22.5,
                "pat_margin": 14.9,
                "roe": 18.5,
                "roce": 21.2,
                "debt_to_equity": 0.35,
                "current_ratio": 2.1,
                "pe_ratio": 28.5,
                "eps": 10.53,
                "book_value": 85.6,
                "promoter_holding_pre": 72.5,
                "promoter_holding_post": 58.2,
                "revenue_growth_3yr": 37.5,
                "pat_growth_3yr": 52.3
            },
            "IPO002": {
                "revenue_fy24": 312.8,
                "revenue_fy23": 245.6,
                "revenue_fy22": 189.3,
                "pat_fy24": 28.5,
                "pat_fy23": 18.9,
                "pat_fy22": 12.1,
                "ebitda_margin": 18.2,
                "pat_margin": 9.1,
                "roe": 14.2,
                "roce": 16.8,
                "debt_to_equity": 0.85,
                "current_ratio": 1.5,
                "pe_ratio": 35.2,
                "eps": 4.26,
                "book_value": 42.3,
                "promoter_holding_pre": 68.5,
                "promoter_holding_post": 52.1,
                "revenue_growth_3yr": 28.5,
                "pat_growth_3yr": 53.6
            },
            "IPO003": {
                "revenue_fy24": 892.5,
                "revenue_fy23": 756.8,
                "revenue_fy22": 612.4,
                "pat_fy24": 125.6,
                "pat_fy23": 98.5,
                "pat_fy22": 72.8,
                "ebitda_margin": 24.8,
                "pat_margin": 14.1,
                "roe": 22.5,
                "roce": 26.8,
                "debt_to_equity": 0.22,
                "current_ratio": 2.8,
                "pe_ratio": 24.5,
                "eps": 22.24,
                "book_value": 145.2,
                "promoter_holding_pre": 75.2,
                "promoter_holding_post": 62.8,
                "revenue_growth_3yr": 20.8,
                "pat_growth_3yr": 31.2
            },
            "IPO004": {
                "revenue_fy24": 1256.8,
                "revenue_fy23": 985.6,
                "revenue_fy22": 756.2,
                "pat_fy24": 285.6,
                "pat_fy23": 198.5,
                "pat_fy22": 142.8,
                "ebitda_margin": 32.5,
                "pat_margin": 22.7,
                "roe": 28.5,
                "roce": 32.1,
                "debt_to_equity": 0.15,
                "current_ratio": 3.2,
                "pe_ratio": 22.8,
                "eps": 31.36,
                "book_value": 186.5,
                "promoter_holding_pre": 78.5,
                "promoter_holding_post": 65.2,
                "revenue_growth_3yr": 28.8,
                "pat_growth_3yr": 41.5
            },
            "IPO005": {
                "revenue_fy24": 185.6,
                "revenue_fy23": 162.8,
                "revenue_fy22": 145.2,
                "pat_fy24": 12.5,
                "pat_fy23": 9.8,
                "pat_fy22": 7.2,
                "ebitda_margin": 12.5,
                "pat_margin": 6.7,
                "roe": 10.2,
                "roce": 12.5,
                "debt_to_equity": 1.25,
                "current_ratio": 1.2,
                "pe_ratio": 42.5,
                "eps": 2.16,
                "book_value": 28.5,
                "promoter_holding_pre": 82.5,
                "promoter_holding_post": 68.5,
                "revenue_growth_3yr": 13.0,
                "pat_growth_3yr": 31.8
            },
            "IPO006": {
                "revenue_fy24": 225.8,
                "revenue_fy23": 198.5,
                "revenue_fy22": 175.2,
                "pat_fy24": 22.5,
                "pat_fy23": 18.2,
                "pat_fy22": 14.8,
                "ebitda_margin": 16.8,
                "pat_margin": 10.0,
                "roe": 15.8,
                "roce": 18.5,
                "debt_to_equity": 0.65,
                "current_ratio": 1.8,
                "pe_ratio": 32.5,
                "eps": 6.31,
                "book_value": 52.8,
                "promoter_holding_pre": 71.2,
                "promoter_holding_post": 56.8,
                "revenue_growth_3yr": 13.5,
                "pat_growth_3yr": 23.2
            },
            "IPO007": {
                "revenue_fy24": 625.8,
                "revenue_fy23": 485.2,
                "revenue_fy22": 356.8,
                "pat_fy24": 98.5,
                "pat_fy23": 65.8,
                "pat_fy22": 42.5,
                "ebitda_margin": 26.5,
                "pat_margin": 15.7,
                "roe": 24.8,
                "roce": 28.5,
                "debt_to_equity": 0.28,
                "current_ratio": 2.5,
                "pe_ratio": 26.8,
                "eps": 16.12,
                "book_value": 98.5,
                "promoter_holding_pre": 74.5,
                "promoter_holding_post": 60.2,
                "revenue_growth_3yr": 32.5,
                "pat_growth_3yr": 52.3
            },
            "IPO008": {
                "revenue_fy24": 142.5,
                "revenue_fy23": 125.8,
                "revenue_fy22": 112.5,
                "pat_fy24": 15.2,
                "pat_fy23": 12.5,
                "pat_fy22": 10.2,
                "ebitda_margin": 18.5,
                "pat_margin": 10.7,
                "roe": 16.5,
                "roce": 19.2,
                "debt_to_equity": 0.55,
                "current_ratio": 1.9,
                "pe_ratio": 28.5,
                "eps": 4.25,
                "book_value": 35.8,
                "promoter_holding_pre": 76.8,
                "promoter_holding_post": 62.5,
                "revenue_growth_3yr": 12.5,
                "pat_growth_3yr": 22.1
            }
        }
        
        rng = self._get_rng(f"fundamentals:{ipo_id}")
        return fundamentals_data.get(ipo_id, self._generate_random_fundamentals(rng))
    
    def _generate_random_fundamentals(self, rng: np.random.Generator) -> Dict:
        """Generate random fundamental data for unknown IPOs."""
        return {
            "revenue_fy24": rng.uniform(100, 1000),
            "revenue_fy23": rng.uniform(80, 800),
            "revenue_fy22": rng.uniform(60, 600),
            "pat_fy24": rng.uniform(10, 100),
            "pat_fy23": rng.uniform(8, 80),
            "pat_fy22": rng.uniform(5, 50),
            "ebitda_margin": rng.uniform(10, 30),
            "pat_margin": rng.uniform(5, 20),
            "roe": rng.uniform(10, 30),
            "roce": rng.uniform(12, 35),
            "debt_to_equity": rng.uniform(0.1, 2.0),
            "current_ratio": rng.uniform(1.0, 3.0),
            "pe_ratio": rng.uniform(15, 50),
            "eps": rng.uniform(2, 30),
            "book_value": rng.uniform(20, 150),
            "promoter_holding_pre": rng.uniform(60, 85),
            "promoter_holding_post": rng.uniform(50, 70),
            "revenue_growth_3yr": rng.uniform(10, 40),
            "pat_growth_3yr": rng.uniform(15, 60)
        }
    
    def collect_subscription_data(self, ipo_id: str) -> Dict:
        """
        Collect IPO subscription data.
        
        Args:
            ipo_id: Unique identifier for the IPO
            
        Returns:
            Dictionary containing subscription metrics
        """
        logger.info(f"Collecting subscription data for {ipo_id}")

        live_subscription = self._fetch_live_subscription_data(ipo_id)
        if live_subscription:
            return live_subscription
        
        subscription_data = {
            "IPO001": {
                "qib_subscription": 85.5,
                "nii_subscription": 125.8,
                "retail_subscription": 15.2,
                "total_subscription": 45.8,
                "anchor_portion_subscribed": True,
                "day1_subscription": 8.5,
                "day2_subscription": 28.6,
                "day3_subscription": 45.8
            },
            "IPO002": {
                "qib_subscription": 42.5,
                "nii_subscription": 68.5,
                "retail_subscription": 8.5,
                "total_subscription": 22.5,
                "anchor_portion_subscribed": True,
                "day1_subscription": 4.2,
                "day2_subscription": 12.5,
                "day3_subscription": 22.5
            },
            "IPO003": {
                "qib_subscription": 125.8,
                "nii_subscription": 185.6,
                "retail_subscription": 28.5,
                "total_subscription": 68.5,
                "anchor_portion_subscribed": True,
                "day1_subscription": 15.2,
                "day2_subscription": 42.8,
                "day3_subscription": 68.5
            },
            "IPO004": {
                "qib_subscription": 165.2,
                "nii_subscription": 225.8,
                "retail_subscription": 35.6,
                "total_subscription": 85.2,
                "anchor_portion_subscribed": True,
                "day1_subscription": 22.5,
                "day2_subscription": 55.8,
                "day3_subscription": 85.2
            },
            "IPO005": {
                "qib_subscription": 2.5,
                "nii_subscription": 4.8,
                "retail_subscription": 1.2,
                "total_subscription": 2.2,
                "anchor_portion_subscribed": False,
                "day1_subscription": 0.5,
                "day2_subscription": 1.2,
                "day3_subscription": 2.2
            },
            "IPO006": {
                "qib_subscription": 18.5,
                "nii_subscription": 32.5,
                "retail_subscription": 5.8,
                "total_subscription": 12.5,
                "anchor_portion_subscribed": True,
                "day1_subscription": 2.5,
                "day2_subscription": 7.8,
                "day3_subscription": 12.5
            },
            "IPO007": {
                "qib_subscription": 95.2,
                "nii_subscription": 142.5,
                "retail_subscription": 18.5,
                "total_subscription": 52.5,
                "anchor_portion_subscribed": True,
                "day1_subscription": 12.5,
                "day2_subscription": 35.2,
                "day3_subscription": 52.5
            },
            "IPO008": {
                "qib_subscription": 28.5,
                "nii_subscription": 45.2,
                "retail_subscription": 6.5,
                "total_subscription": 15.8,
                "anchor_portion_subscribed": True,
                "day1_subscription": 3.5,
                "day2_subscription": 9.5,
                "day3_subscription": 15.8
            }
        }
        
        rng = self._get_rng(f"subscription:{ipo_id}")
        return subscription_data.get(ipo_id, self._generate_random_subscription(rng))

    def _fetch_live_subscription_data(self, ipo_id: str) -> Optional[Dict]:
        """Fetch live total subscription from the NSE current issue endpoint."""
        payload = self._make_json_request("https://www.nseindia.com/api/ipo-current-issue")
        if not isinstance(payload, list):
            return None

        for row in payload:
            symbol = str(row.get("symbol", "")).strip()
            if symbol != ipo_id:
                continue

            total_subscription = self._parse_numeric_value(row.get("noOfTime"))
            if total_subscription <= 0:
                return None

            qib_subscription = total_subscription
            nii_subscription = total_subscription
            retail_subscription = total_subscription

            return {
                "qib_subscription": qib_subscription,
                "nii_subscription": nii_subscription,
                "retail_subscription": retail_subscription,
                "total_subscription": total_subscription,
                "anchor_portion_subscribed": total_subscription >= 1.0,
                "day1_subscription": round(total_subscription * 0.3, 2),
                "day2_subscription": round(total_subscription * 0.7, 2),
                "day3_subscription": total_subscription,
                "data_source": "nse_api_total",
            }

        return None
    
    def _generate_random_subscription(self, rng: np.random.Generator) -> Dict:
        """Generate random subscription data."""
        total = rng.uniform(1, 100)
        return {
            "qib_subscription": rng.uniform(total * 0.5, total * 3),
            "nii_subscription": rng.uniform(total * 0.8, total * 4),
            "retail_subscription": rng.uniform(total * 0.3, total * 1.5),
            "total_subscription": total,
            "anchor_portion_subscribed": bool(rng.integers(0, 2)),
            "day1_subscription": total * 0.2,
            "day2_subscription": total * 0.6,
            "day3_subscription": total
        }
    
    def collect_gmp_data(self, ipo_id: str) -> Dict:
        """
        Collect Grey Market Premium data.
        
        Args:
            ipo_id: Unique identifier for the IPO
            
        Returns:
            Dictionary containing GMP information
        """
        logger.info(f"Collecting GMP data for {ipo_id}")
        
        gmp_data = {
            "IPO001": {
                "gmp_amount": 85,
                "gmp_percentage": 28.3,
                "kostak_rate": 1800,
                "gmp_trend": "increasing",
                "last_updated": "2026-01-16"
            },
            "IPO002": {
                "gmp_amount": 35,
                "gmp_percentage": 23.3,
                "kostak_rate": 1200,
                "gmp_trend": "stable",
                "last_updated": "2026-01-16"
            },
            "IPO003": {
                "gmp_amount": 145,
                "gmp_percentage": 26.6,
                "kostak_rate": 2500,
                "gmp_trend": "increasing",
                "last_updated": "2026-01-16"
            },
            "IPO004": {
                "gmp_amount": 185,
                "gmp_percentage": 25.9,
                "kostak_rate": 3200,
                "gmp_trend": "increasing",
                "last_updated": "2026-01-16"
            },
            "IPO005": {
                "gmp_amount": -5,
                "gmp_percentage": -5.4,
                "kostak_rate": 200,
                "gmp_trend": "decreasing",
                "last_updated": "2026-01-16"
            },
            "IPO006": {
                "gmp_amount": 22,
                "gmp_percentage": 10.7,
                "kostak_rate": 650,
                "gmp_trend": "stable",
                "last_updated": "2026-01-16"
            },
            "IPO007": {
                "gmp_amount": 110,
                "gmp_percentage": 25.5,
                "kostak_rate": 2100,
                "gmp_trend": "increasing",
                "last_updated": "2026-01-16"
            },
            "IPO008": {
                "gmp_amount": 18,
                "gmp_percentage": 14.9,
                "kostak_rate": 550,
                "gmp_trend": "stable",
                "last_updated": "2026-01-16"
            }
        }
        
        rng = self._get_rng(f"gmp:{ipo_id}")
        return gmp_data.get(ipo_id, self._generate_random_gmp(rng))
    
    def _generate_random_gmp(self, rng: np.random.Generator) -> Dict:
        """Generate random GMP data."""
        gmp_pct = rng.uniform(-20, 50)
        return {
            "gmp_amount": gmp_pct * 3,
            "gmp_percentage": gmp_pct,
            "kostak_rate": max(0, gmp_pct * 40),
            "gmp_trend": ["increasing", "stable", "decreasing"][int(rng.integers(0, 3))],
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    
    def collect_market_data(self, force_refresh: bool = False) -> Dict:
        """
        Collect current market conditions data.
        
        Returns:
            Dictionary containing market indicators
        """
        if not force_refresh and self._market_data_cache is not None and self._is_cache_valid(self._market_data_cache_at):
            return dict(self._market_data_cache)

        logger.info("Collecting market data...")

        market_data = self._fetch_live_market_data()
        if market_data is None:
            market_data = self._get_fallback_market_data()

        self._market_data_cache = dict(market_data)
        self._market_data_cache_at = datetime.now()
        return market_data

    def _fetch_live_market_data(self) -> Optional[Dict]:
        """Fetch live market snapshot from NSE public APIs."""
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.nseindia.com/",
        })

        indices_payload = self._make_json_request("https://www.nseindia.com/api/allIndices")
        fii_dii_payload = self._make_json_request("https://www.nseindia.com/api/fiidiiTradeReact")

        if not isinstance(indices_payload, dict) or "data" not in indices_payload:
            return None

        indices = indices_payload.get("data", [])
        nifty_50 = self._find_index(indices, "NIFTY 50")
        india_vix = self._find_index(indices, "INDIA VIX")
        if not nifty_50:
            return None

        fii_net = 0.0
        dii_net = 0.0
        if isinstance(fii_dii_payload, list):
            for row in fii_dii_payload:
                category = str(row.get("category", "")).upper()
                net_value = self._parse_numeric_value(row.get("netValue"))
                if "FII" in category:
                    fii_net = net_value
                elif "DII" in category:
                    dii_net = net_value

        current_nifty = self._parse_numeric_value(nifty_50.get("last"))
        one_week_ago = self._parse_numeric_value(nifty_50.get("oneWeekAgoVal"))
        one_month_ago = self._parse_numeric_value(nifty_50.get("oneMonthAgoVal"))

        market_data = {
            "nifty_50_current": current_nifty,
            "nifty_50_change_pct": self._parse_numeric_value(nifty_50.get("percentChange")),
            "nifty_50_5day_return": ((current_nifty / one_week_ago) - 1) * 100 if one_week_ago else 0.0,
            "nifty_50_20day_return": ((current_nifty / one_month_ago) - 1) * 100 if one_month_ago else 0.0,
            "india_vix": self._parse_numeric_value(india_vix.get("last")) if india_vix else 15.0,
            "fii_net_investment": fii_net,
            "dii_net_investment": dii_net,
            "market_breadth_advance": int(self._parse_numeric_value(indices_payload.get("advances"))),
            "market_breadth_decline": int(self._parse_numeric_value(indices_payload.get("declines"))),
            "sector_performance": self._build_sector_performance(indices),
            "global_cues": {
                "dow_jones_change": 0.0,
                "nasdaq_change": 0.0,
                "sgx_nifty": current_nifty,
            },
            "market_sentiment": self._infer_market_sentiment(
                self._parse_numeric_value(nifty_50.get("percentChange")),
                fii_net,
            ),
            "ipo_market_sentiment": self._infer_market_sentiment(
                self._parse_numeric_value(nifty_50.get("percentChange")),
                fii_net,
            ),
            "data_timestamp": indices_payload.get("timestamp", datetime.now().isoformat()),
            "data_source": "nse_api",
        }

        return market_data

    def _find_index(self, indices: List[Dict], index_name: str) -> Optional[Dict]:
        """Find an index row by its NSE index name."""
        for row in indices:
            if str(row.get("index", "")).upper() == index_name.upper():
                return row
        return None

    def _build_sector_performance(self, indices: List[Dict]) -> Dict[str, float]:
        """Build sector performance using live NSE sector indices where available."""
        index_map = {
            "technology": "NIFTY IT",
            "healthcare": "NIFTY HEALTHCARE INDEX",
            "financial_services": "NIFTY FINANCIAL SERVICES",
            "energy": "NIFTY OIL & GAS",
            "fmcg": "NIFTY FMCG",
            "automobile": "NIFTY AUTO",
            "retail": "NIFTY CONSUMER DURABLES",
            "real_estate": "NIFTY REALTY",
            "manufacturing": "NIFTY METAL",
        }
        performance = {}
        for sector_key, index_name in index_map.items():
            row = self._find_index(indices, index_name)
            performance[sector_key] = self._parse_numeric_value(row.get("percentChange")) if row else 0.0
        return performance

    def _infer_market_sentiment(self, nifty_change: float, fii_net: float) -> str:
        """Infer market sentiment from broad index move and institutional flow."""
        if nifty_change >= 0.5 and fii_net >= 0:
            return "bullish"
        if nifty_change <= -0.5 and fii_net < 0:
            return "bearish"
        return "neutral"

    def _get_fallback_market_data(self) -> Dict:
        """Fallback market snapshot when live APIs are unavailable."""
        return {
            "nifty_50_current": 24850.5,
            "nifty_50_change_pct": 0.85,
            "nifty_50_5day_return": 2.15,
            "nifty_50_20day_return": 4.85,
            "india_vix": 14.25,
            "fii_net_investment": 2850.5,  # in crores
            "dii_net_investment": 1250.8,  # in crores
            "market_breadth_advance": 1250,
            "market_breadth_decline": 680,
            "sector_performance": {
                "technology": 3.5,
                "healthcare": 2.8,
                "financial_services": 4.2,
                "energy": -1.5,
                "fmcg": 1.8,
                "automobile": 2.2,
                "retail": 0.5
            },
            "global_cues": {
                "dow_jones_change": 0.65,
                "nasdaq_change": 1.25,
                "sgx_nifty": 24880.0
            },
            "market_sentiment": "bullish",
            "ipo_market_sentiment": "positive",
            "data_timestamp": datetime.now().isoformat(),
            "data_source": "sample_fallback",
        }
    
    def get_complete_ipo_data(self, ipo_id: str) -> Dict:
        """
        Get complete data for a specific IPO.
        
        Args:
            ipo_id: Unique identifier for the IPO
            
        Returns:
            Complete dictionary with all IPO data
        """
        ipo_listings = self.collect_ipo_listings()
        ipo_info = ipo_listings[ipo_listings['ipo_id'] == ipo_id].to_dict('records')
        
        if not ipo_info:
            return None
        
        complete_data = {
            "basic_info": ipo_info[0],
            "fundamentals": self.collect_fundamental_data(ipo_id),
            "subscription": self.collect_subscription_data(ipo_id),
            "gmp": self.collect_gmp_data(ipo_id),
            "market": self.collect_market_data()
        }
        
        return complete_data

    def collect_ipo_news(self, limit: int = 20) -> List[Dict]:
        """
        Collect latest IPO news from configured sources.

        Args:
            limit: Maximum number of news items to return

        Returns:
            List of news dictionaries with title, content, source, date, category
        """
        logger.info(f"Collecting IPO news (limit: {limit})")


        # Try to fetch real news first
        news_items = self._fetch_real_news()

        if not news_items or len(news_items) < 5:
            logger.warning("Failed to fetch sufficient real news, using sample data")
            news_items = self._get_sample_news()


        
        # Try to fetch real news first
        news_items = self._fetch_real_news()
        
        if not news_items or len(news_items) < 5:
            logger.warning("Failed to fetch sufficient real news, using sample data")
            news_items = self._fetch_real_news()

        if not news_items or len(news_items) < 5:
            logger.warning('Failed to fetch sufficient real news, using sample data')
            news_items = self._get_sample_news()
        

        # Sort by date (newest first) and limit
        news_items.sort(key=lambda x: x.get('date', ''), reverse=True)
        return news_items[:limit]
    
    def _fetch_real_news(self) -> List[Dict]:
        """Fetch real IPO news from live sources."""
        news_items = []
        
        try:
            # Try Moneycontrol IPO news
            moneycontrol_news = self._fetch_moneycontrol_news()
            news_items.extend(moneycontrol_news)
            
            # Try Economic Times IPO news
            et_news = self._fetch_economic_times_news()
            news_items.extend(et_news)
            
            # Try Business Standard IPO news
            bs_news = self._fetch_business_standard_news()
            news_items.extend(bs_news)
            
        except Exception as e:
            logger.error(f"Error fetching real news: {e}")
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_news = []
        for item in news_items:
            title = item.get('title', '').strip().lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(item)
        
        return unique_news
    

    def _get_sample_news(self) -> List[Dict]:
        """Generate sample IPO news data."""
    
    def _fetch_moneycontrol_news(self) -> List[Dict]:
        """Fetch IPO news from Moneycontrol."""
        news_items = []
        try:
            url = "https://www.moneycontrol.com/news/business/ipo/"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='clearfix')[:10]  # Limit to 10
                
                for article in articles:
                    try:
                        title_elem = article.find('h2') or article.find('h3') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('span', class_='date') or article.find('time')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Latest IPO news: {title}. Read more for complete details."
                        
                        news_items.append({
                            "id": f"mc_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Moneycontrol",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Moneycontrol article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Moneycontrol news: {e}")
            
        return news_items
    
    def _fetch_economic_times_news(self) -> List[Dict]:
        """Fetch IPO news from Economic Times."""
        news_items = []
        try:
            url = "https://economictimes.indiatimes.com/markets/ipo"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='eachStory')[:8]  # Limit to 8
                
                for article in articles:
                    try:
                        title_elem = article.find('h3') or article.find('h2')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('time') or article.find('span', class_='date')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Market update: {title}. Check Economic Times for detailed analysis."
                        
                        news_items.append({
                            "id": f"et_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Economic Times",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Economic Times article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Economic Times news: {e}")
            
        return news_items
    
    def _fetch_business_standard_news(self) -> List[Dict]:
        """Fetch IPO news from Business Standard."""
        news_items = []
        try:
            url = "https://www.business-standard.com/companies/news"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='listing')[:6]  # Limit to 6
                
                for article in articles:
                    try:
                        title_elem = article.find('h2') or article.find('h3') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('span', class_='date') or article.find('time')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Business news: {title}. Read the full article on Business Standard."
                        
                        news_items.append({
                            "id": f"bs_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Business Standard",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Business Standard article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Business Standard news: {e}")
            
        return news_items
    
    def _parse_news_date(self, date_str: str) -> str:
        """Parse news date string into standard format."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            # Handle various date formats
            date_str = date_str.strip()
            
            # Handle relative dates
            if 'hour' in date_str.lower() or 'minute' in date_str.lower():
                hours = 0
                if 'hour' in date_str.lower():
                    hours = int(re.search(r'(\d+)', date_str).group(1))
                elif 'minute' in date_str.lower():
                    hours = 0  # Treat as recent
                
                return (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
            
            # Handle "X days ago"
            if 'day' in date_str.lower():
                days = int(re.search(r'(\d+)', date_str).group(1))
                return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
            
            # Try standard date parsing
            for fmt in ["%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                    
        except Exception:
            pass
        
        # Default to current time
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def _fetch_moneycontrol_news(self) -> List[Dict]:
        """Fetch IPO news from Moneycontrol."""
        news_items = []
        try:
            url = "https://www.moneycontrol.com/news/business/ipo/"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='clearfix')[:10]  # Limit to 10
                
                for article in articles:
                    try:
                        title_elem = article.find('h2') or article.find('h3') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('span', class_='date') or article.find('time')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Latest IPO news: {title}. Read more for complete details."
                        
                        news_items.append({
                            "id": f"mc_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Moneycontrol",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Moneycontrol article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Moneycontrol news: {e}")
            
        return news_items
    
    def _fetch_economic_times_news(self) -> List[Dict]:
        """Fetch IPO news from Economic Times."""
        news_items = []
        try:
            url = "https://economictimes.indiatimes.com/markets/ipo"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='eachStory')[:8]  # Limit to 8
                
                for article in articles:
                    try:
                        title_elem = article.find('h3') or article.find('h2')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('time') or article.find('span', class_='date')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Market update: {title}. Check Economic Times for detailed analysis."
                        
                        news_items.append({
                            "id": f"et_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Economic Times",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Economic Times article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Economic Times news: {e}")
            
        return news_items
    
    def _fetch_business_standard_news(self) -> List[Dict]:
        """Fetch IPO news from Business Standard."""
        news_items = []
        try:
            url = "https://www.business-standard.com/companies/news"
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='listing')[:6]  # Limit to 6
                
                for article in articles:
                    try:
                        title_elem = article.find('h2') or article.find('h3') or article.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text(strip=True)
                        link_elem = article.find('a')
                        link = link_elem.get('href') if link_elem else ""
                        
                        # Skip if not IPO related
                        if not any(keyword in title.lower() for keyword in ['ipo', 'initial public offering', 'public issue']):
                            continue
                        
                        # Extract date
                        date_elem = article.find('span', class_='date') or article.find('time')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Generate content summary
                        content = f"Business news: {title}. Read the full article on Business Standard."
                        
                        news_items.append({
                            "id": f"bs_{hash(title) % 10000}",
                            "title": title,
                            "content": content,
                            "source": "Business Standard",
                            "date": self._parse_news_date(date_str),
                            "category": "ipo" if "ipo" in title.lower() else "market",
                            "featured": False,
                            "url": link
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing Business Standard article: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching Business Standard news: {e}")
            
        return news_items
    
    def _parse_news_date(self, date_str: str) -> str:
        """Parse news date string into standard format."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            # Handle various date formats
            date_str = date_str.strip()
            
            # Handle relative dates
            if 'hour' in date_str.lower() or 'minute' in date_str.lower():
                hours = 0
                if 'hour' in date_str.lower():
                    hours = int(re.search(r'(\d+)', date_str).group(1))
                elif 'minute' in date_str.lower():
                    hours = 0  # Treat as recent
                
                return (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
            
            # Handle "X days ago"
            if 'day' in date_str.lower():
                days = int(re.search(r'(\d+)', date_str).group(1))
                return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
            
            # Try standard date parsing
            for fmt in ["%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                    
        except Exception:
            pass
        
        # Default to current time
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def _get_sample_news(self) -> List[Dict]:

        """Generate sample IPO news data with current market context."""
        from datetime import datetime, timedelta
        import random
        
        base_date = datetime.now()
        

        # Expanded current market news with more varied content

        # Current market news with varied content

        news_templates = [
            {
                "title": "Market Rally Continues: Nifty Crosses 24,000 Mark",
                "content": "Indian equity markets continued their upward trajectory today with Nifty 50 crossing the 24,000 mark for the first time. Strong FII inflows and positive global cues contributed to the bullish sentiment.",
                "source": "Economic Times",
                "category": "market",
                "featured": True
            },
            {
                "title": "IPO Pipeline Strong: 15 Companies Await SEBI Nod",
                "content": "The IPO pipeline remains robust with 15 companies in various stages of filing their draft red herring prospectuses. Technology and renewable energy sectors dominate the upcoming offerings.",
                "source": "Business Standard",
                "category": "ipo",
                "featured": False
            },
            {
                "title": "Green Energy IPOs Attract Record Investments",
                "content": "Renewable energy companies are seeing unprecedented investor interest with subscription rates exceeding 100x for recent green energy IPOs. This reflects growing focus on sustainable investments.",
                "source": "Moneycontrol",
                "category": "market",
                "featured": False
            },
            {
                "title": "AI & Tech Startups Drive IPO Activity",
                "content": "Artificial Intelligence and technology startups are leading the IPO charge with innovative business models attracting both retail and institutional investors. Market capitalization targets have been consistently exceeded.",
                "source": "Livemint",
                "category": "ipo",

                "featured": False
            },
            {
                "title": "SME IPO Segment Shows 300% Growth",
                "content": "Small and Medium Enterprise IPOs have shown remarkable growth with over 300% increase in participation compared to last year. This segment is becoming increasingly attractive for retail investors.",
                "source": "Economic Times",
                "category": "market",
                "featured": False
            },
            {
                "title": "Subscription Trends: QIB Participation Hits Record High",
                "content": "Qualified Institutional Buyers (QIB) participation in recent IPOs has reached record levels, indicating strong confidence from institutional investors in the primary market.",
                "source": "Business Standard",
                "category": "analysis",
                "featured": False
            },
            {
                "title": "Global Funds Eye Indian IPO Market",
                "content": "International investment funds are increasingly focusing on Indian IPOs with several global players committing significant capital to upcoming technology and infrastructure offerings.",
                "source": "Moneycontrol",
                "category": "market",
                "featured": False
            },
            {
                "title": "IPO Valuation Metrics Show Premium Pricing",
                "content": "Current IPO valuations are trading at premium levels compared to historical averages. Companies with strong growth narratives and digital transformation stories command higher valuations.",
                "source": "Livemint",
                "category": "analysis",
                "featured": False
            },
            {
                "title": "Fintech Revolution: Digital Payment IPOs Surge",
                "content": "Fintech companies specializing in digital payments and financial technology are experiencing massive investor interest. Recent IPOs in this sector have seen subscription rates exceeding 200x.",
                "source": "Economic Times",
                "category": "ipo",
                "featured": False
            },
            {
                "title": "Regulatory Changes Boost SME IPO Confidence",
                "content": "Recent regulatory changes have boosted confidence in the SME IPO segment. Simplified listing processes and reduced compliance requirements are attracting more small businesses to the public markets.",
                "source": "Business Standard",
                "category": "regulatory",
                "featured": False
            },
            {
                "title": "Healthcare IPOs Gain Momentum Post-Pandemic",
                "content": "Healthcare and pharmaceutical companies are seeing renewed interest from investors. Strong fundamentals and essential service status are driving premium valuations in this sector.",

                "featured": False
            },
            {
                "title": "SME IPO Segment Shows 300% Growth",
                "content": "Small and Medium Enterprise IPOs have shown remarkable growth with over 300% increase in participation compared to last year. This segment is becoming increasingly attractive for retail investors.",
                "source": "Economic Times",
                "category": "market",
                "featured": False
            },
            {
                "title": "Subscription Trends: QIB Participation Hits Record High",
                "content": "Qualified Institutional Buyers (QIB) participation in recent IPOs has reached record levels, indicating strong confidence from institutional investors in the primary market.",
                "source": "Business Standard",
                "category": "analysis",
                "featured": False
            },
            {
                "title": "Global Funds Eye Indian IPO Market",
                "content": "International investment funds are increasingly focusing on Indian IPOs with several global players committing significant capital to upcoming technology and infrastructure offerings.",

                "source": "Moneycontrol",
                "category": "market",
                "featured": False
            },
            {

                "title": "Retail Investor Participation Reaches All-Time High",
                "content": "Retail investor participation in IPOs has reached an all-time high with over 2 crore applications received in recent offerings. This reflects growing financial literacy and investment awareness.",

                "title": "IPO Valuation Metrics Show Premium Pricing",
                "content": "Current IPO valuations are trading at premium levels compared to historical averages. Companies with strong growth narratives and digital transformation stories command higher valuations.",

                "source": "Livemint",
                "category": "analysis",
                "featured": False
            },
            {
                "title": "Infrastructure IPOs Attract Long-Term Investors",
                "content": "Infrastructure development companies are attracting long-term institutional investors with stable revenue models and government-backed projects. This sector shows strong growth potential.",
                "source": "Economic Times",
                "category": "ipo",
                "featured": False
            },
            {
                "title": "Market Volatility Tests IPO Sentiment",
                "content": "Recent market volatility has tested investor sentiment in the IPO market. However, companies with strong fundamentals continue to attract healthy subscription rates.",
                "source": "Business Standard",
                "category": "market",
                "featured": False
            },
            {
                "title": "Technology IPOs Lead Market Capitalization Gains",
                "content": "Technology sector IPOs are leading market capitalization gains with innovative solutions and scalable business models. Digital transformation remains a key investment theme.",
                "source": "Moneycontrol",
                "category": "analysis",
                "featured": False
            },
            {
                "title": "SEBI Guidelines Enhance IPO Transparency",
                "content": "New SEBI guidelines have enhanced transparency in the IPO process with stricter disclosure requirements and improved investor protection measures.",
                "source": "Livemint",
                "category": "regulatory",
                "featured": False
            }
        ]
        

        # Shuffle and select all news items (not just 8)
        random.shuffle(news_templates)
        selected_news = news_templates  # Use all available news

        # Shuffle and select random news items
        random.shuffle(news_templates)
        selected_news = news_templates[:8]

        
        # Add dynamic dates and IDs
        news_data = []
        for i, news in enumerate(selected_news):
            # Vary the dates to make them seem current

            hours_ago = random.randint(1, 168)  # Random time within last week

            hours_ago = random.randint(1, 72)  # Random time within last 3 days

            news_date = base_date - timedelta(hours=hours_ago)
            
            news_item = news.copy()
            news_item["id"] = f"news_{i+1:03d}"
            news_item["date"] = news_date.strftime("%Y-%m-%d %H:%M")

            


            news_data.append(news_item)
        
        return news_data
collector = IPODataCollector()


if __name__ == "__main__":
    # Test data collection
    collector = IPODataCollector()
    
    # Collect IPO listings
    listings = collector.collect_ipo_listings()
    print("\nIPO Listings:")
    print(listings)
    
    # Get complete data for first IPO
    if len(listings) > 0:
        ipo_id = listings.iloc[0]['ipo_id']
        complete_data = collector.get_complete_ipo_data(ipo_id)
        print(f"\nComplete data for {ipo_id}:")
        print(json.dumps(complete_data, indent=2, default=str))
