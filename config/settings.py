"""
Configuration Settings for AI-Driven IPO Intelligence Platform
===============================================================
Central configuration file for all system parameters, thresholds, and API settings.
"""

import os
from pathlib import Path

# ==================== PROJECT PATHS ====================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models" / "saved"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ==================== DATABASE SETTINGS ====================
DATABASE = {
    "type": "sqlite",
    "name": "ipo_intelligence.db",
    "path": DATA_DIR / "ipo_intelligence.db"
}

# ==================== IPO ANALYSIS THRESHOLDS ====================
IPO_THRESHOLDS = {
    # Subscription ratio thresholds
    "subscription_excellent": 50.0,      # >50x is excellent
    "subscription_good": 10.0,           # 10-50x is good
    "subscription_moderate": 3.0,        # 3-10x is moderate
    "subscription_weak": 1.0,            # 1-3x is weak
    
    # GMP (Grey Market Premium) thresholds
    "gmp_strong_positive": 50.0,         # >50% GMP is strong
    "gmp_moderate_positive": 20.0,       # 20-50% is moderate positive
    "gmp_weak_positive": 5.0,            # 5-20% is weak positive
    "gmp_neutral_lower": -5.0,           # -5% to 5% is neutral
    "gmp_negative": -20.0,               # Below -20% is strongly negative
    
    # Price-to-Earnings thresholds
    "pe_undervalued": 15.0,
    "pe_fairly_valued": 25.0,
    "pe_overvalued": 40.0,
    
    # Debt-to-Equity thresholds
    "de_low_risk": 0.5,
    "de_moderate_risk": 1.0,
    "de_high_risk": 2.0,
    
    # Market volatility (VIX-like index)
    "volatility_low": 15.0,
    "volatility_moderate": 25.0,
    "volatility_high": 35.0
}

# ==================== RISK SCORING WEIGHTS ====================
RISK_WEIGHTS = {
    "fundamental_score": 0.30,           # 30% weight to fundamentals
    "sentiment_score": 0.20,             # 20% weight to sentiment
    "market_condition_score": 0.20,      # 20% weight to market conditions
    "subscription_score": 0.15,          # 15% weight to subscription data
    "gmp_score": 0.15                    # 15% weight to GMP
}

# ==================== DECISION THRESHOLDS ====================
DECISION_THRESHOLDS = {
    # Composite score thresholds for decisions
    "strong_apply": 0.75,                # Score >= 0.75: Strong Apply
    "apply": 0.60,                       # Score 0.60-0.75: Apply
    "hold": 0.45,                        # Score 0.45-0.60: Hold
    "avoid": 0.30,                       # Score 0.30-0.45: Avoid
    # Below 0.30: Strong Avoid
    
    # Risk level thresholds
    "low_risk": 0.35,
    "medium_risk": 0.60,
    # Above 0.60: High risk
    
    # Listing day sell thresholds
    "sell_profit_target": 0.20,          # 20% profit target
    "sell_stop_loss": -0.10,             # 10% stop loss
    "sell_time_limit_hours": 2           # Decision within 2 hours of listing
}

# ==================== ML MODEL SETTINGS ====================
ML_CONFIG = {
    "random_forest": {
        "n_estimators": 100,
        "max_depth": 10,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "random_state": 42
    },
    "xgboost": {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42
    },
    "logistic_regression": {
        "C": 1.0,
        "max_iter": 1000,
        "random_state": 42
    },
    "test_size": 0.2,
    "cross_validation_folds": 5
}

# ==================== SENTIMENT ANALYSIS SETTINGS ====================
SENTIMENT_CONFIG = {
    "vader_threshold_positive": 0.05,
    "vader_threshold_negative": -0.05,
    "news_sources": [
        "moneycontrol",
        "economictimes",
        "livemint",
        "businesstoday"
    ],
    "max_articles_per_ipo": 20,
    "lookback_days": 7
}

# ==================== DATA COLLECTION SETTINGS ====================
DATA_COLLECTION = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "request_timeout": 30,
    "retry_attempts": 3,
    "delay_between_requests": 2,  # seconds
    
    # Data sources
    "sources": {
        "chittorgarh": "https://www.chittorgarh.com/ipo/ipo_list.asp",
        "moneycontrol": "https://www.moneycontrol.com/ipo/",
        "nse": "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"
    }
}

# ==================== MARKET INDICATORS ====================
MARKET_INDICATORS = {
    "nifty_50_threshold_bullish": 0.02,      # 2% positive return
    "nifty_50_threshold_bearish": -0.02,     # 2% negative return
    "fii_dii_bullish": 1000,                 # Net positive in crores
    "fii_dii_bearish": -1000,                # Net negative in crores
    "sector_momentum_period": 5              # Days for sector analysis
}

# ==================== LOGGING CONFIGURATION ====================
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file_name": LOGS_DIR / "ipo_platform.log"
}

# ==================== DASHBOARD SETTINGS ====================
DASHBOARD_CONFIG = {
    "page_title": "AI-Driven IPO Intelligence Platform",
    "page_icon": "📈",
    "layout": "wide",
    "refresh_interval": 300,  # 5 minutes
    "max_displayed_ipos": 20
}
