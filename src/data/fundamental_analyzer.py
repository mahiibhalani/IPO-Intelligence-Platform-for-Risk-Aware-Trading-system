"""
Fundamental Analysis Engine
===========================
Analyzes IPO company fundamentals and generates fundamental scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import IPO_THRESHOLDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """
    Comprehensive fundamental analysis for IPO companies.
    
    Analyzes:
    - Profitability metrics (ROE, ROCE, margins)
    - Growth metrics (revenue, PAT growth)
    - Valuation metrics (P/E, P/B ratios)
    - Financial health (debt, liquidity)
    - Promoter confidence (holding changes)
    """
    
    def __init__(self):
        self.thresholds = IPO_THRESHOLDS
        
    def analyze(self, fundamentals: Dict, basic_info: Dict) -> Dict:
        """
        Perform comprehensive fundamental analysis.
        
        Args:
            fundamentals: Dictionary of fundamental metrics
            basic_info: Basic IPO information
            
        Returns:
            Analysis results with scores and insights
        """
        logger.info(f"Analyzing fundamentals for {basic_info.get('company_name', 'Unknown')}")
        
        analysis = {
            "profitability_analysis": self._analyze_profitability(fundamentals),
            "growth_analysis": self._analyze_growth(fundamentals),
            "valuation_analysis": self._analyze_valuation(fundamentals, basic_info),
            "financial_health_analysis": self._analyze_financial_health(fundamentals),
            "promoter_analysis": self._analyze_promoter_holding(fundamentals),
            "sector_analysis": self._analyze_sector_context(basic_info.get('sector', '')),
        }
        
        # Calculate composite fundamental score
        analysis["composite_score"] = self._calculate_composite_score(analysis)
        analysis["fundamental_rating"] = self._get_rating(analysis["composite_score"])
        analysis["key_insights"] = self._generate_insights(analysis, fundamentals)
        
        return analysis
    
    def _analyze_profitability(self, fundamentals: Dict) -> Dict:
        """Analyze profitability metrics."""
        roe = fundamentals.get('roe', 0)
        roce = fundamentals.get('roce', 0)
        ebitda_margin = fundamentals.get('ebitda_margin', 0)
        pat_margin = fundamentals.get('pat_margin', 0)
        
        # Score each metric (0-1 scale)
        roe_score = min(1.0, roe / 25) if roe > 0 else 0
        roce_score = min(1.0, roce / 30) if roce > 0 else 0
        ebitda_score = min(1.0, ebitda_margin / 30) if ebitda_margin > 0 else 0
        pat_score = min(1.0, pat_margin / 20) if pat_margin > 0 else 0
        
        profitability_score = (roe_score * 0.3 + roce_score * 0.3 + 
                               ebitda_score * 0.2 + pat_score * 0.2)
        
        return {
            "roe": {"value": roe, "score": roe_score, "benchmark": 15},
            "roce": {"value": roce, "score": roce_score, "benchmark": 18},
            "ebitda_margin": {"value": ebitda_margin, "score": ebitda_score, "benchmark": 20},
            "pat_margin": {"value": pat_margin, "score": pat_score, "benchmark": 12},
            "composite_score": profitability_score,
            "assessment": self._get_profitability_assessment(profitability_score)
        }
    
    def _get_profitability_assessment(self, score: float) -> str:
        """Get profitability assessment text."""
        if score >= 0.8:
            return "Excellent profitability - Company shows strong earnings potential"
        elif score >= 0.6:
            return "Good profitability - Above average earning capability"
        elif score >= 0.4:
            return "Moderate profitability - Average performance expected"
        elif score >= 0.2:
            return "Below average profitability - Earnings concern"
        else:
            return "Poor profitability - High risk on earnings front"
    
    def _analyze_growth(self, fundamentals: Dict) -> Dict:
        """Analyze growth metrics."""
        revenue_growth = fundamentals.get('revenue_growth_3yr', 0)
        pat_growth = fundamentals.get('pat_growth_3yr', 0)
        
        # Calculate year-over-year metrics
        revenue_fy24 = fundamentals.get('revenue_fy24', 0)
        revenue_fy23 = fundamentals.get('revenue_fy23', 1)
        pat_fy24 = fundamentals.get('pat_fy24', 0)
        pat_fy23 = fundamentals.get('pat_fy23', 1)
        
        yoy_revenue_growth = ((revenue_fy24 - revenue_fy23) / revenue_fy23) * 100 if revenue_fy23 > 0 else 0
        yoy_pat_growth = ((pat_fy24 - pat_fy23) / pat_fy23) * 100 if pat_fy23 > 0 else 0
        
        # Score growth metrics
        revenue_growth_score = min(1.0, revenue_growth / 30) if revenue_growth > 0 else 0
        pat_growth_score = min(1.0, pat_growth / 40) if pat_growth > 0 else 0
        yoy_rev_score = min(1.0, yoy_revenue_growth / 25) if yoy_revenue_growth > 0 else 0
        yoy_pat_score = min(1.0, yoy_pat_growth / 30) if yoy_pat_growth > 0 else 0
        
        growth_score = (revenue_growth_score * 0.3 + pat_growth_score * 0.3 +
                        yoy_rev_score * 0.2 + yoy_pat_score * 0.2)
        
        # Check growth consistency
        is_consistent = self._check_growth_consistency(fundamentals)
        
        return {
            "revenue_growth_3yr": {"value": revenue_growth, "score": revenue_growth_score},
            "pat_growth_3yr": {"value": pat_growth, "score": pat_growth_score},
            "yoy_revenue_growth": {"value": yoy_revenue_growth, "score": yoy_rev_score},
            "yoy_pat_growth": {"value": yoy_pat_growth, "score": yoy_pat_score},
            "is_consistent": is_consistent,
            "composite_score": growth_score,
            "assessment": self._get_growth_assessment(growth_score, is_consistent)
        }
    
    def _check_growth_consistency(self, fundamentals: Dict) -> bool:
        """Check if growth has been consistent over years."""
        revenues = [
            fundamentals.get('revenue_fy22', 0),
            fundamentals.get('revenue_fy23', 0),
            fundamentals.get('revenue_fy24', 0)
        ]
        
        # Check if revenues are consistently increasing
        return all(revenues[i] < revenues[i+1] for i in range(len(revenues)-1))
    
    def _get_growth_assessment(self, score: float, is_consistent: bool) -> str:
        """Get growth assessment text."""
        consistency_text = " with consistent trajectory" if is_consistent else " but inconsistent pattern"
        
        if score >= 0.8:
            return f"High growth company{consistency_text}"
        elif score >= 0.6:
            return f"Good growth prospects{consistency_text}"
        elif score >= 0.4:
            return f"Moderate growth{consistency_text}"
        elif score >= 0.2:
            return f"Slow growth company{consistency_text}"
        else:
            return f"Limited growth visibility{consistency_text}"
    
    def _analyze_valuation(self, fundamentals: Dict, basic_info: Dict) -> Dict:
        """Analyze valuation metrics."""
        pe_ratio = fundamentals.get('pe_ratio', 0)
        eps = fundamentals.get('eps', 0)
        book_value = fundamentals.get('book_value', 0)
        
        # Get issue price
        issue_price = basic_info.get('price_band_high', 0)
        
        # Calculate P/B ratio
        pb_ratio = issue_price / book_value if book_value > 0 else 0
        
        # Score valuation (lower is better for P/E and P/B)
        pe_score = max(0, 1 - (pe_ratio / 60)) if pe_ratio > 0 else 0.5
        pb_score = max(0, 1 - (pb_ratio / 8)) if pb_ratio > 0 else 0.5
        
        # Get sector average P/E for comparison
        sector = basic_info.get('sector', 'Unknown')
        sector_pe = self._get_sector_pe(sector)
        
        pe_vs_sector = "undervalued" if pe_ratio < sector_pe * 0.9 else \
                       "overvalued" if pe_ratio > sector_pe * 1.2 else "fairly valued"
        
        valuation_score = pe_score * 0.6 + pb_score * 0.4
        
        return {
            "pe_ratio": {"value": pe_ratio, "score": pe_score, "sector_avg": sector_pe},
            "pb_ratio": {"value": pb_ratio, "score": pb_score},
            "eps": eps,
            "book_value": book_value,
            "issue_price": issue_price,
            "pe_vs_sector": pe_vs_sector,
            "composite_score": valuation_score,
            "assessment": self._get_valuation_assessment(valuation_score, pe_vs_sector)
        }
    
    def _get_sector_pe(self, sector: str) -> float:
        """Get average P/E ratio for sector."""
        sector_pe_map = {
            "Technology": 35,
            "Healthcare": 30,
            "Financial Services": 22,
            "Energy": 18,
            "FMCG": 40,
            "Automobile": 25,
            "Retail": 35,
            "Infrastructure": 20
        }
        return sector_pe_map.get(sector, 25)
    
    def _get_valuation_assessment(self, score: float, pe_vs_sector: str) -> str:
        """Get valuation assessment text."""
        if score >= 0.7:
            return f"Attractively valued - {pe_vs_sector} compared to sector"
        elif score >= 0.5:
            return f"Reasonably valued - {pe_vs_sector} compared to sector"
        elif score >= 0.3:
            return f"Slightly expensive - {pe_vs_sector} compared to sector"
        else:
            return f"Expensive valuation - {pe_vs_sector} compared to sector"
    
    def _analyze_financial_health(self, fundamentals: Dict) -> Dict:
        """Analyze financial health metrics."""
        debt_to_equity = fundamentals.get('debt_to_equity', 0)
        current_ratio = fundamentals.get('current_ratio', 0)
        
        # Score debt level (lower is better)
        if debt_to_equity <= self.thresholds['de_low_risk']:
            debt_score = 1.0
            debt_risk = "Low"
        elif debt_to_equity <= self.thresholds['de_moderate_risk']:
            debt_score = 0.7
            debt_risk = "Moderate"
        elif debt_to_equity <= self.thresholds['de_high_risk']:
            debt_score = 0.4
            debt_risk = "High"
        else:
            debt_score = 0.2
            debt_risk = "Very High"
        
        # Score liquidity (higher is better)
        liquidity_score = min(1.0, current_ratio / 2.5) if current_ratio > 0 else 0
        
        health_score = debt_score * 0.6 + liquidity_score * 0.4
        
        return {
            "debt_to_equity": {"value": debt_to_equity, "score": debt_score, "risk_level": debt_risk},
            "current_ratio": {"value": current_ratio, "score": liquidity_score},
            "composite_score": health_score,
            "assessment": self._get_health_assessment(health_score, debt_risk)
        }
    
    def _get_health_assessment(self, score: float, debt_risk: str) -> str:
        """Get financial health assessment text."""
        if score >= 0.8:
            return f"Strong balance sheet with {debt_risk.lower()} debt risk"
        elif score >= 0.6:
            return f"Healthy financials with {debt_risk.lower()} debt levels"
        elif score >= 0.4:
            return f"Moderate financial health, {debt_risk.lower()} debt concerns"
        else:
            return f"Weak financial health, {debt_risk.lower()} leverage risk"
    
    def _analyze_promoter_holding(self, fundamentals: Dict) -> Dict:
        """Analyze promoter holding and changes."""
        pre_ipo = fundamentals.get('promoter_holding_pre', 0)
        post_ipo = fundamentals.get('promoter_holding_post', 0)
        
        dilution = pre_ipo - post_ipo
        dilution_pct = (dilution / pre_ipo) * 100 if pre_ipo > 0 else 0
        
        # Score based on post-IPO holding and dilution
        holding_score = min(1.0, post_ipo / 70) if post_ipo > 0 else 0
        dilution_score = max(0, 1 - (dilution_pct / 30))
        
        promoter_score = holding_score * 0.6 + dilution_score * 0.4
        
        return {
            "pre_ipo_holding": pre_ipo,
            "post_ipo_holding": post_ipo,
            "dilution_pct": dilution_pct,
            "composite_score": promoter_score,
            "assessment": self._get_promoter_assessment(promoter_score, post_ipo, dilution_pct)
        }
    
    def _get_promoter_assessment(self, score: float, holding: float, dilution: float) -> str:
        """Get promoter analysis assessment."""
        if score >= 0.8:
            return f"Strong promoter confidence with {holding:.1f}% post-IPO stake"
        elif score >= 0.6:
            return f"Good promoter commitment, {dilution:.1f}% dilution is reasonable"
        elif score >= 0.4:
            return f"Moderate promoter stake, watch for future dilution"
        else:
            return f"Concern on promoter commitment - significant dilution observed"
    
    def _analyze_sector_context(self, sector: str) -> Dict:
        """Analyze sector-specific context."""
        sector_outlook = {
            "Technology": {"outlook": "Positive", "score": 0.8, "tailwind": True},
            "Healthcare": {"outlook": "Stable", "score": 0.7, "tailwind": True},
            "Financial Services": {"outlook": "Positive", "score": 0.75, "tailwind": True},
            "Energy": {"outlook": "Mixed", "score": 0.5, "tailwind": False},
            "FMCG": {"outlook": "Stable", "score": 0.65, "tailwind": False},
            "Automobile": {"outlook": "Recovering", "score": 0.6, "tailwind": True},
            "Retail": {"outlook": "Cautious", "score": 0.45, "tailwind": False}
        }
        
        sector_info = sector_outlook.get(sector, {"outlook": "Neutral", "score": 0.5, "tailwind": False})
        
        return {
            "sector": sector,
            "outlook": sector_info["outlook"],
            "composite_score": sector_info["score"],
            "has_tailwind": sector_info["tailwind"],
            "assessment": f"{sector} sector has {sector_info['outlook'].lower()} outlook"
        }
    
    def _calculate_composite_score(self, analysis: Dict) -> float:
        """Calculate weighted composite fundamental score."""
        weights = {
            "profitability_analysis": 0.25,
            "growth_analysis": 0.25,
            "valuation_analysis": 0.20,
            "financial_health_analysis": 0.15,
            "promoter_analysis": 0.10,
            "sector_analysis": 0.05
        }
        
        composite = 0.0
        for key, weight in weights.items():
            if key in analysis and "composite_score" in analysis[key]:
                composite += analysis[key]["composite_score"] * weight
        
        return round(composite, 3)
    
    def _get_rating(self, score: float) -> str:
        """Convert score to rating."""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.65:
            return "Good"
        elif score >= 0.5:
            return "Average"
        elif score >= 0.35:
            return "Below Average"
        else:
            return "Poor"
    
    def _generate_insights(self, analysis: Dict, fundamentals: Dict) -> List[str]:
        """Generate key insights from fundamental analysis."""
        insights = []
        
        # Profitability insights
        prof = analysis["profitability_analysis"]
        if prof["composite_score"] >= 0.7:
            insights.append(f"✓ Strong profitability with {fundamentals.get('roe', 0):.1f}% ROE")
        elif prof["composite_score"] < 0.4:
            insights.append(f"⚠ Weak profitability metrics - ROE at {fundamentals.get('roe', 0):.1f}%")
        
        # Growth insights
        growth = analysis["growth_analysis"]
        if growth["is_consistent"]:
            insights.append(f"✓ Consistent revenue growth over 3 years")
        else:
            insights.append(f"⚠ Inconsistent growth pattern observed")
        
        # Valuation insights
        val = analysis["valuation_analysis"]
        if val["pe_vs_sector"] == "undervalued":
            insights.append(f"✓ Attractively priced vs sector (P/E: {fundamentals.get('pe_ratio', 0):.1f}x)")
        elif val["pe_vs_sector"] == "overvalued":
            insights.append(f"⚠ Premium valuation (P/E: {fundamentals.get('pe_ratio', 0):.1f}x vs sector avg)")
        
        # Debt insights
        health = analysis["financial_health_analysis"]
        debt_risk = health["debt_to_equity"]["risk_level"]
        if debt_risk == "Low":
            insights.append(f"✓ Clean balance sheet with D/E of {fundamentals.get('debt_to_equity', 0):.2f}")
        elif debt_risk in ["High", "Very High"]:
            insights.append(f"⚠ High leverage concern - D/E ratio at {fundamentals.get('debt_to_equity', 0):.2f}")
        
        # Promoter insights
        promoter = analysis["promoter_analysis"]
        if promoter["post_ipo_holding"] >= 60:
            insights.append(f"✓ Strong promoter stake of {promoter['post_ipo_holding']:.1f}% post-IPO")
        
        return insights


# Create module-level instance
analyzer = FundamentalAnalyzer()


if __name__ == "__main__":
    # Test fundamental analysis
    sample_fundamentals = {
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
    }
    
    sample_basic_info = {
        "company_name": "TechVision AI Ltd",
        "sector": "Technology",
        "price_band_high": 300
    }
    
    analyzer = FundamentalAnalyzer()
    result = analyzer.analyze(sample_fundamentals, sample_basic_info)
    
    print("\nFundamental Analysis Results:")
    print(f"Composite Score: {result['composite_score']}")
    print(f"Rating: {result['fundamental_rating']}")
    print("\nKey Insights:")
    for insight in result['key_insights']:
        print(f"  {insight}")
