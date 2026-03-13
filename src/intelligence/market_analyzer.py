"""
Market Analyzer Module
======================
Analyzes market conditions and volatility for IPO risk assessment.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import IPO_THRESHOLDS, MARKET_INDICATORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """
    Market conditions and volatility analyzer.
    
    Analyzes:
    - Market trend (bullish/bearish/neutral)
    - Volatility levels (VIX analysis)
    - FII/DII flows
    - Sector-specific conditions
    - Global market cues
    """
    
    def __init__(self):
        self.thresholds = IPO_THRESHOLDS
        self.indicators = MARKET_INDICATORS
    
    def analyze(self, market_data: Dict, sector: str = None) -> Dict:
        """
        Perform comprehensive market analysis.
        
        Args:
            market_data: Dictionary containing market indicators
            sector: Sector of the IPO for sector-specific analysis
            
        Returns:
            Market analysis results
        """
        logger.info("Analyzing market conditions...")
        
        analysis = {
            "trend_analysis": self._analyze_trend(market_data),
            "volatility_analysis": self._analyze_volatility(market_data),
            "institutional_flow": self._analyze_fii_dii(market_data),
            "market_breadth": self._analyze_breadth(market_data),
            "global_cues": self._analyze_global_cues(market_data),
        }
        
        if sector:
            analysis["sector_analysis"] = self._analyze_sector(market_data, sector)
        
        # Calculate composite market score
        analysis["composite_score"] = self._calculate_composite_score(analysis)
        analysis["market_condition"] = self._get_market_condition(analysis["composite_score"])
        analysis["ipo_timing_assessment"] = self._assess_ipo_timing(analysis)
        
        return analysis
    
    def _analyze_trend(self, market_data: Dict) -> Dict:
        """Analyze market trend."""
        nifty_change = market_data.get('nifty_50_change_pct', 0)
        nifty_5d = market_data.get('nifty_50_5day_return', 0)
        nifty_20d = market_data.get('nifty_50_20day_return', 0)
        
        # Determine short-term trend
        if nifty_change > 0.5:
            short_term = "bullish"
            short_score = min(1.0, 0.6 + nifty_change * 0.1)
        elif nifty_change < -0.5:
            short_term = "bearish"
            short_score = max(0.0, 0.4 + nifty_change * 0.1)
        else:
            short_term = "neutral"
            short_score = 0.5
        
        # Determine medium-term trend
        if nifty_5d > self.indicators['nifty_50_threshold_bullish'] * 100:
            medium_term = "bullish"
            medium_score = min(1.0, 0.6 + nifty_5d * 0.05)
        elif nifty_5d < self.indicators['nifty_50_threshold_bearish'] * 100:
            medium_term = "bearish"
            medium_score = max(0.0, 0.4 + nifty_5d * 0.05)
        else:
            medium_term = "neutral"
            medium_score = 0.5
        
        # Determine longer-term trend
        if nifty_20d > 3:
            long_term = "bullish"
            long_score = min(1.0, 0.6 + nifty_20d * 0.02)
        elif nifty_20d < -3:
            long_term = "bearish"
            long_score = max(0.0, 0.4 + nifty_20d * 0.02)
        else:
            long_term = "neutral"
            long_score = 0.5
        
        # Overall trend score (weighted average)
        composite_score = short_score * 0.3 + medium_score * 0.4 + long_score * 0.3
        
        return {
            "short_term": {"trend": short_term, "score": short_score, "change": nifty_change},
            "medium_term": {"trend": medium_term, "score": medium_score, "return_5d": nifty_5d},
            "long_term": {"trend": long_term, "score": long_score, "return_20d": nifty_20d},
            "composite_score": composite_score,
            "overall_trend": self._determine_overall_trend(composite_score)
        }
    
    def _determine_overall_trend(self, score: float) -> str:
        """Determine overall trend from score."""
        if score >= 0.65:
            return "bullish"
        elif score <= 0.35:
            return "bearish"
        else:
            return "neutral"
    
    def _analyze_volatility(self, market_data: Dict) -> Dict:
        """Analyze market volatility using VIX."""
        vix = market_data.get('india_vix', 15)
        
        # Determine volatility level
        if vix < self.thresholds['volatility_low']:
            level = "Low"
            score = 0.85
            risk_factor = 0.2
        elif vix < self.thresholds['volatility_moderate']:
            level = "Moderate"
            score = 0.6
            risk_factor = 0.5
        elif vix < self.thresholds['volatility_high']:
            level = "High"
            score = 0.35
            risk_factor = 0.75
        else:
            level = "Very High"
            score = 0.15
            risk_factor = 1.0
        
        return {
            "vix": vix,
            "level": level,
            "composite_score": score,
            "risk_factor": risk_factor,
            "assessment": self._get_volatility_assessment(level, vix)
        }
    
    def _get_volatility_assessment(self, level: str, vix: float) -> str:
        """Get volatility assessment text."""
        if level == "Low":
            return f"Low volatility (VIX: {vix:.1f}) - Favorable for IPO listings"
        elif level == "Moderate":
            return f"Moderate volatility (VIX: {vix:.1f}) - Normal market conditions"
        elif level == "High":
            return f"High volatility (VIX: {vix:.1f}) - IPO listing may be volatile"
        else:
            return f"Very high volatility (VIX: {vix:.1f}) - Risky time for IPO listing"
    
    def _analyze_fii_dii(self, market_data: Dict) -> Dict:
        """Analyze FII/DII flows."""
        fii = market_data.get('fii_net_investment', 0)
        dii = market_data.get('dii_net_investment', 0)
        net_flow = fii + dii
        
        # Determine flow sentiment
        if fii > self.indicators['fii_dii_bullish']:
            fii_sentiment = "strongly_bullish"
            fii_score = 0.9
        elif fii > 0:
            fii_sentiment = "mildly_bullish"
            fii_score = 0.65
        elif fii > self.indicators['fii_dii_bearish']:
            fii_sentiment = "mildly_bearish"
            fii_score = 0.4
        else:
            fii_sentiment = "strongly_bearish"
            fii_score = 0.2
        
        # DII typically provides support when FII sells
        if dii > 0:
            dii_sentiment = "supportive"
            dii_score = 0.7
        else:
            dii_sentiment = "selling"
            dii_score = 0.4
        
        # Net flow analysis
        if net_flow > 2000:
            net_sentiment = "strong_inflow"
        elif net_flow > 0:
            net_sentiment = "net_inflow"
        elif net_flow > -2000:
            net_sentiment = "net_outflow"
        else:
            net_sentiment = "strong_outflow"
        
        composite_score = fii_score * 0.6 + dii_score * 0.4
        
        return {
            "fii_net": fii,
            "dii_net": dii,
            "net_flow": net_flow,
            "fii_sentiment": fii_sentiment,
            "dii_sentiment": dii_sentiment,
            "net_sentiment": net_sentiment,
            "composite_score": composite_score,
            "assessment": f"FII: ₹{fii:,.0f}Cr ({fii_sentiment}), DII: ₹{dii:,.0f}Cr ({dii_sentiment})"
        }
    
    def _analyze_breadth(self, market_data: Dict) -> Dict:
        """Analyze market breadth."""
        advances = market_data.get('market_breadth_advance', 0)
        declines = market_data.get('market_breadth_decline', 0)
        
        total = advances + declines
        if total == 0:
            ratio = 1.0
        else:
            ratio = advances / total
        
        # Determine breadth
        if ratio > 0.65:
            breadth = "strongly_positive"
            score = 0.85
        elif ratio > 0.55:
            breadth = "positive"
            score = 0.7
        elif ratio > 0.45:
            breadth = "neutral"
            score = 0.5
        elif ratio > 0.35:
            breadth = "negative"
            score = 0.35
        else:
            breadth = "strongly_negative"
            score = 0.2
        
        return {
            "advances": advances,
            "declines": declines,
            "ratio": ratio,
            "breadth": breadth,
            "composite_score": score,
            "assessment": f"Market breadth: {advances} advances vs {declines} declines"
        }
    
    def _analyze_global_cues(self, market_data: Dict) -> Dict:
        """Analyze global market cues."""
        global_data = market_data.get('global_cues', {})
        
        dow = global_data.get('dow_jones_change', 0)
        nasdaq = global_data.get('nasdaq_change', 0)
        sgx = global_data.get('sgx_nifty', 0)
        
        # Average global sentiment
        avg_change = (dow + nasdaq) / 2
        
        if avg_change > 1:
            global_sentiment = "positive"
            score = 0.75
        elif avg_change > 0:
            global_sentiment = "mildly_positive"
            score = 0.6
        elif avg_change > -1:
            global_sentiment = "mildly_negative"
            score = 0.45
        else:
            global_sentiment = "negative"
            score = 0.3
        
        return {
            "dow_jones": dow,
            "nasdaq": nasdaq,
            "sgx_nifty": sgx,
            "global_sentiment": global_sentiment,
            "composite_score": score,
            "assessment": f"Global cues: {'Positive' if avg_change > 0 else 'Negative'} (Dow: {dow:+.1f}%, Nasdaq: {nasdaq:+.1f}%)"
        }
    
    def _analyze_sector(self, market_data: Dict, sector: str) -> Dict:
        """Analyze sector-specific conditions."""
        sector_perf = market_data.get('sector_performance', {})
        
        # Normalize sector name
        sector_key = sector.lower().replace(" ", "_")
        perf = sector_perf.get(sector_key, 0)
        
        # Determine sector momentum
        if perf > 3:
            momentum = "strong_positive"
            score = 0.85
        elif perf > 1:
            momentum = "positive"
            score = 0.7
        elif perf > -1:
            momentum = "neutral"
            score = 0.5
        elif perf > -3:
            momentum = "negative"
            score = 0.35
        else:
            momentum = "strong_negative"
            score = 0.2
        
        return {
            "sector": sector,
            "performance": perf,
            "momentum": momentum,
            "composite_score": score,
            "assessment": f"{sector} sector: {perf:+.1f}% ({momentum.replace('_', ' ')})"
        }
    
    def _calculate_composite_score(self, analysis: Dict) -> float:
        """Calculate weighted composite market score."""
        weights = {
            "trend_analysis": 0.30,
            "volatility_analysis": 0.25,
            "institutional_flow": 0.20,
            "market_breadth": 0.10,
            "global_cues": 0.10,
            "sector_analysis": 0.05
        }
        
        composite = 0.0
        total_weight = 0.0
        
        for key, weight in weights.items():
            if key in analysis and "composite_score" in analysis[key]:
                composite += analysis[key]["composite_score"] * weight
                total_weight += weight
        
        # Normalize by actual weights used
        if total_weight > 0:
            composite = composite / total_weight
        
        return round(composite, 3)
    
    def _get_market_condition(self, score: float) -> str:
        """Get market condition label."""
        if score >= 0.7:
            return "Highly Favorable"
        elif score >= 0.55:
            return "Favorable"
        elif score >= 0.45:
            return "Neutral"
        elif score >= 0.3:
            return "Unfavorable"
        else:
            return "Highly Unfavorable"
    
    def _assess_ipo_timing(self, analysis: Dict) -> Dict:
        """Assess IPO timing based on market conditions."""
        score = analysis["composite_score"]
        volatility = analysis.get("volatility_analysis", {}).get("level", "Moderate")
        trend = analysis.get("trend_analysis", {}).get("overall_trend", "neutral")
        
        # Determine timing recommendation
        if score >= 0.65 and volatility in ["Low", "Moderate"]:
            timing = "Excellent"
            recommendation = "Market conditions are highly favorable for IPO listing"
        elif score >= 0.5 and volatility != "Very High":
            timing = "Good"
            recommendation = "Reasonably good time for IPO listing"
        elif score >= 0.4:
            timing = "Neutral"
            recommendation = "Market conditions are average; proceed with caution"
        else:
            timing = "Poor"
            recommendation = "Market conditions are unfavorable; higher listing risk"
        
        return {
            "timing": timing,
            "recommendation": recommendation,
            "key_factors": self._get_key_factors(analysis)
        }
    
    def _get_key_factors(self, analysis: Dict) -> List[str]:
        """Extract key market factors."""
        factors = []
        
        # Trend factor
        trend = analysis.get("trend_analysis", {}).get("overall_trend", "neutral")
        factors.append(f"Market trend: {trend.capitalize()}")
        
        # Volatility factor
        vol_level = analysis.get("volatility_analysis", {}).get("level", "Moderate")
        factors.append(f"Volatility: {vol_level}")
        
        # FII/DII factor
        fii_sent = analysis.get("institutional_flow", {}).get("fii_sentiment", "neutral")
        factors.append(f"FII sentiment: {fii_sent.replace('_', ' ').capitalize()}")
        
        return factors


# Module-level instance
market_analyzer = MarketAnalyzer()


if __name__ == "__main__":
    # Test market analysis
    sample_market_data = {
        "nifty_50_current": 24850.5,
        "nifty_50_change_pct": 0.85,
        "nifty_50_5day_return": 2.15,
        "nifty_50_20day_return": 4.85,
        "india_vix": 14.25,
        "fii_net_investment": 2850.5,
        "dii_net_investment": 1250.8,
        "market_breadth_advance": 1250,
        "market_breadth_decline": 680,
        "sector_performance": {
            "technology": 3.5,
            "healthcare": 2.8,
            "financial_services": 4.2
        },
        "global_cues": {
            "dow_jones_change": 0.65,
            "nasdaq_change": 1.25,
            "sgx_nifty": 24880.0
        }
    }
    
    analyzer = MarketAnalyzer()
    result = analyzer.analyze(sample_market_data, "Technology")
    
    print("\nMarket Analysis Results:")
    print(f"Composite Score: {result['composite_score']:.3f}")
    print(f"Market Condition: {result['market_condition']}")
    print(f"\nIPO Timing: {result['ipo_timing_assessment']['timing']}")
    print(f"Recommendation: {result['ipo_timing_assessment']['recommendation']}")
