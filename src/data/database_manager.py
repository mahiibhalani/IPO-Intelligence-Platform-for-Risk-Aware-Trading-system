"""
Database Manager for IPO Intelligence Platform
==============================================
Handles all database operations using SQLite.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import DATABASE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLite database manager for IPO data persistence.
    """
    
    def __init__(self):
        self.db_path = DATABASE['path']
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _initialize_database(self):
        """Initialize database with required tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # IPO Master Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_master (
                ipo_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                sector TEXT,
                issue_size_cr REAL,
                price_band_low REAL,
                price_band_high REAL,
                lot_size INTEGER,
                issue_open_date TEXT,
                issue_close_date TEXT,
                listing_date TEXT,
                face_value REAL,
                ipo_type TEXT,
                listing_exchange TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Fundamental Data Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_fundamentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                revenue_fy24 REAL,
                revenue_fy23 REAL,
                revenue_fy22 REAL,
                pat_fy24 REAL,
                pat_fy23 REAL,
                pat_fy22 REAL,
                ebitda_margin REAL,
                pat_margin REAL,
                roe REAL,
                roce REAL,
                debt_to_equity REAL,
                current_ratio REAL,
                pe_ratio REAL,
                eps REAL,
                book_value REAL,
                promoter_holding_pre REAL,
                promoter_holding_post REAL,
                revenue_growth_3yr REAL,
                pat_growth_3yr REAL,
                created_at TEXT,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        # Subscription Data Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_subscription (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                qib_subscription REAL,
                nii_subscription REAL,
                retail_subscription REAL,
                total_subscription REAL,
                anchor_portion_subscribed INTEGER,
                day1_subscription REAL,
                day2_subscription REAL,
                day3_subscription REAL,
                recorded_at TEXT,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        # GMP Data Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_gmp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                gmp_amount REAL,
                gmp_percentage REAL,
                kostak_rate REAL,
                gmp_trend TEXT,
                recorded_at TEXT,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        # Market Data Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nifty_50_current REAL,
                nifty_50_change_pct REAL,
                nifty_50_5day_return REAL,
                nifty_50_20day_return REAL,
                india_vix REAL,
                fii_net_investment REAL,
                dii_net_investment REAL,
                market_sentiment TEXT,
                recorded_at TEXT
            )
        ''')
        
        # Sentiment Analysis Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                sentiment_score REAL,
                sentiment_label TEXT,
                news_count INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                key_topics TEXT,
                analyzed_at TEXT,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        # Analysis Results Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ipo_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                fundamental_score REAL,
                sentiment_score REAL,
                market_score REAL,
                subscription_score REAL,
                gmp_score REAL,
                composite_score REAL,
                risk_level TEXT,
                recommendation TEXT,
                confidence REAL,
                analysis_details TEXT,
                created_at TEXT,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        # Listing Performance Table (for model training)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listing_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_id TEXT NOT NULL,
                listing_price REAL,
                listing_gain_pct REAL,
                day1_high REAL,
                day1_low REAL,
                day1_close REAL,
                week1_return REAL,
                month1_return REAL,
                is_profitable INTEGER,
                FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_ipo_master(self, ipo_data: pd.DataFrame):
        """Save IPO master data."""
        conn = self._get_connection()
        now = datetime.now().isoformat()
        
        for _, row in ipo_data.iterrows():
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ipo_master 
                (ipo_id, company_name, sector, issue_size_cr, price_band_low, 
                price_band_high, lot_size, issue_open_date, issue_close_date, 
                listing_date, face_value, ipo_type, listing_exchange, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['ipo_id'], row['company_name'], row['sector'], 
                row['issue_size_cr'], row['price_band_low'], row['price_band_high'],
                row['lot_size'], row['issue_open_date'], row['issue_close_date'],
                row['listing_date'], row['face_value'], row['ipo_type'],
                row['listing_exchange'], now, now
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {len(ipo_data)} IPOs to database")
    
    def save_fundamentals(self, ipo_id: str, fundamentals: Dict):
        """Save fundamental data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ipo_fundamentals 
            (ipo_id, revenue_fy24, revenue_fy23, revenue_fy22, pat_fy24, pat_fy23, 
            pat_fy22, ebitda_margin, pat_margin, roe, roce, debt_to_equity, 
            current_ratio, pe_ratio, eps, book_value, promoter_holding_pre, 
            promoter_holding_post, revenue_growth_3yr, pat_growth_3yr, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ipo_id,
            fundamentals.get('revenue_fy24'),
            fundamentals.get('revenue_fy23'),
            fundamentals.get('revenue_fy22'),
            fundamentals.get('pat_fy24'),
            fundamentals.get('pat_fy23'),
            fundamentals.get('pat_fy22'),
            fundamentals.get('ebitda_margin'),
            fundamentals.get('pat_margin'),
            fundamentals.get('roe'),
            fundamentals.get('roce'),
            fundamentals.get('debt_to_equity'),
            fundamentals.get('current_ratio'),
            fundamentals.get('pe_ratio'),
            fundamentals.get('eps'),
            fundamentals.get('book_value'),
            fundamentals.get('promoter_holding_pre'),
            fundamentals.get('promoter_holding_post'),
            fundamentals.get('revenue_growth_3yr'),
            fundamentals.get('pat_growth_3yr'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_subscription(self, ipo_id: str, subscription: Dict):
        """Save subscription data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ipo_subscription 
            (ipo_id, qib_subscription, nii_subscription, retail_subscription, 
            total_subscription, anchor_portion_subscribed, day1_subscription, 
            day2_subscription, day3_subscription, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ipo_id,
            subscription.get('qib_subscription'),
            subscription.get('nii_subscription'),
            subscription.get('retail_subscription'),
            subscription.get('total_subscription'),
            1 if subscription.get('anchor_portion_subscribed') else 0,
            subscription.get('day1_subscription'),
            subscription.get('day2_subscription'),
            subscription.get('day3_subscription'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_gmp(self, ipo_id: str, gmp: Dict):
        """Save GMP data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ipo_gmp 
            (ipo_id, gmp_amount, gmp_percentage, kostak_rate, gmp_trend, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            ipo_id,
            gmp.get('gmp_amount'),
            gmp.get('gmp_percentage'),
            gmp.get('kostak_rate'),
            gmp.get('gmp_trend'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_analysis(self, ipo_id: str, analysis: Dict):
        """Save analysis results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ipo_analysis 
            (ipo_id, fundamental_score, sentiment_score, market_score, 
            subscription_score, gmp_score, composite_score, risk_level, 
            recommendation, confidence, analysis_details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ipo_id,
            analysis.get('fundamental_score'),
            analysis.get('sentiment_score'),
            analysis.get('market_score'),
            analysis.get('subscription_score'),
            analysis.get('gmp_score'),
            analysis.get('composite_score'),
            analysis.get('risk_level'),
            analysis.get('recommendation'),
            analysis.get('confidence'),
            json.dumps(analysis.get('details', {})),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_ipos(self) -> pd.DataFrame:
        """Get all IPOs from database."""
        conn = self._get_connection()
        df = pd.read_sql_query("SELECT * FROM ipo_master ORDER BY listing_date DESC", conn)
        conn.close()
        return df
    
    def get_ipo_by_id(self, ipo_id: str) -> Optional[Dict]:
        """Get IPO details by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ipo_master WHERE ipo_id = ?", (ipo_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['ipo_id', 'company_name', 'sector', 'issue_size_cr', 
                      'price_band_low', 'price_band_high', 'lot_size', 
                      'issue_open_date', 'issue_close_date', 'listing_date',
                      'face_value', 'ipo_type', 'listing_exchange', 
                      'created_at', 'updated_at']
            return dict(zip(columns, row))
        return None
    
    def get_latest_analysis(self, ipo_id: str) -> Optional[Dict]:
        """Get latest analysis for an IPO."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM ipo_analysis 
            WHERE ipo_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (ipo_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'ipo_id', 'fundamental_score', 'sentiment_score',
                      'market_score', 'subscription_score', 'gmp_score',
                      'composite_score', 'risk_level', 'recommendation',
                      'confidence', 'analysis_details', 'created_at']
            result = dict(zip(columns, row))
            result['analysis_details'] = json.loads(result['analysis_details'])
            return result
        return None


# Module-level instance
db_manager = DatabaseManager()


if __name__ == "__main__":
    # Test database operations
    db = DatabaseManager()
    print(f"Database initialized at: {db.db_path}")
    
    # Get all IPOs
    ipos = db.get_all_ipos()
    print(f"IPOs in database: {len(ipos)}")
