"""
Risk-Aware Decision Engine
==========================
Core decision-making engine that combines all analysis components
to generate risk-aware trading recommendations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import (
    RISK_WEIGHTS, DECISION_THRESHOLDS, IPO_THRESHOLDS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Decision(Enum):
    """IPO trading decision types."""
    STRONG_APPLY = "Strong Apply"
    APPLY = "Apply"
    HOLD = "Hold"
    AVOID = "Avoid"
    STRONG_AVOID = "Strong Avoid"
    SELL = "Sell"  # For listing day


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class DecisionEngine:
    """
    Risk-aware decision engine for IPO trading.
    
    Combines multiple analysis dimensions:
    - Fundamental analysis scores
    - Sentiment analysis scores
    - Market condition scores
    - Subscription data scores
    - GMP scores
    - ML predictions
    
    Generates:
    - Pre-listing recommendation (Apply/Hold/Avoid)
    - Risk assessment
    - Listing day strategy
    - Confidence levels
    """
    
    def __init__(self):
        self.weights = RISK_WEIGHTS
        self.thresholds = DECISION_THRESHOLDS
        self.ipo_thresholds = IPO_THRESHOLDS
    
    def analyze_ipo(
        self,
        basic_info: Dict,
        fundamental_analysis: Dict,
        sentiment_analysis: Dict,
        market_analysis: Dict,
        subscription_data: Dict,
        gmp_data: Dict,
        ml_prediction: Dict = None
    ) -> Dict:
        """
        Perform comprehensive IPO analysis and generate recommendations.
        
        Args:
            basic_info: Basic IPO information
            fundamental_analysis: Results from fundamental analyzer
            sentiment_analysis: Results from sentiment analyzer
            market_analysis: Results from market analyzer
            subscription_data: IPO subscription data
            gmp_data: Grey market premium data
            ml_prediction: Optional ML model prediction
            
        Returns:
            Complete analysis with recommendations
        """
        logger.info(f"Analyzing IPO: {basic_info.get('company_name', 'Unknown')}")
        
        # Calculate component scores
        scores = {
            "fundamental_score": self._calculate_fundamental_score(fundamental_analysis),
            "sentiment_score": self._calculate_sentiment_score(sentiment_analysis),
            "market_score": self._calculate_market_score(market_analysis),
            "subscription_score": self._calculate_subscription_score(subscription_data),
            "gmp_score": self._calculate_gmp_score(gmp_data)
        }
        
        # Calculate weighted composite score
        composite_score = self._calculate_composite_score(scores)
        
        # Calculate risk metrics
        risk_analysis = self._analyze_risk(
            fundamental_analysis, market_analysis, 
            subscription_data, gmp_data
        )
        
        # Generate pre-listing recommendation
        pre_listing_decision = self._generate_pre_listing_decision(
            composite_score, risk_analysis, ml_prediction
        )
        
        # Generate listing day strategy
        listing_strategy = self._generate_listing_strategy(
            composite_score, risk_analysis, gmp_data, market_analysis
        )
        
        # Generate insights and reasoning
        insights = self._generate_insights(
            scores, risk_analysis, fundamental_analysis,
            sentiment_analysis, market_analysis, subscription_data, gmp_data
        )
        
        return {
            "ipo_info": {
                "ipo_id": basic_info.get('ipo_id'),
                "company_name": basic_info.get('company_name'),
                "sector": basic_info.get('sector'),
                "issue_size": basic_info.get('issue_size_cr'),
                "price_band": f"₹{basic_info.get('price_band_low', 0)} - ₹{basic_info.get('price_band_high', 0)}",
                "listing_date": basic_info.get('listing_date')
            },
            "scores": scores,
            "composite_score": composite_score,
            "risk_analysis": risk_analysis,
            "pre_listing_recommendation": pre_listing_decision,
            "listing_day_strategy": listing_strategy,
            "ml_prediction": ml_prediction,
            "insights": insights,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _calculate_fundamental_score(self, analysis: Dict) -> float:
        """Extract normalized fundamental score."""
        return analysis.get('composite_score', 0.5)
    
    def _calculate_sentiment_score(self, analysis: Dict) -> float:
        """Extract normalized sentiment score."""
        return analysis.get('composite_score', 0.5)
    
    def _calculate_market_score(self, analysis: Dict) -> float:
        """Extract normalized market score."""
        return analysis.get('composite_score', 0.5)
    
    def _calculate_subscription_score(self, data: Dict) -> float:
        """Calculate score from subscription data."""
        total_sub = data.get('total_subscription', 1)
        qib_sub = data.get('qib_subscription', 0)
        anchor = data.get('anchor_portion_subscribed', False)
        
        # Score based on total subscription
        if total_sub >= self.ipo_thresholds['subscription_excellent']:
            base_score = 0.95
        elif total_sub >= self.ipo_thresholds['subscription_good']:
            base_score = 0.75
        elif total_sub >= self.ipo_thresholds['subscription_moderate']:
            base_score = 0.55
        elif total_sub >= self.ipo_thresholds['subscription_weak']:
            base_score = 0.35
        else:
            base_score = 0.15
        
        # Boost for QIB participation
        if qib_sub > 50:
            base_score = min(1.0, base_score + 0.1)
        
        # Boost for anchor investors
        if anchor:
            base_score = min(1.0, base_score + 0.05)
        
        return base_score
    
    def _calculate_gmp_score(self, data: Dict) -> float:
        """Calculate score from GMP data."""
        gmp_pct = data.get('gmp_percentage', 0)
        trend = data.get('gmp_trend', 'stable')
        
        # Score based on GMP percentage
        if gmp_pct >= self.ipo_thresholds['gmp_strong_positive']:
            base_score = 0.9
        elif gmp_pct >= self.ipo_thresholds['gmp_moderate_positive']:
            base_score = 0.7
        elif gmp_pct >= self.ipo_thresholds['gmp_weak_positive']:
            base_score = 0.55
        elif gmp_pct >= self.ipo_thresholds['gmp_neutral_lower']:
            base_score = 0.4
        elif gmp_pct >= self.ipo_thresholds['gmp_negative']:
            base_score = 0.25
        else:
            base_score = 0.1
        
        # Adjust for trend
        if trend == 'increasing':
            base_score = min(1.0, base_score + 0.1)
        elif trend == 'decreasing':
            base_score = max(0.0, base_score - 0.1)
        
        return base_score
    
    def _calculate_composite_score(self, scores: Dict) -> float:
        """Calculate weighted composite score."""
        composite = 0.0
        for key, weight in self.weights.items():
            if key in scores:
                composite += scores[key] * weight
        return round(composite, 3)
    
    def _analyze_risk(
        self,
        fundamental_analysis: Dict,
        market_analysis: Dict,
        subscription_data: Dict,
        gmp_data: Dict
    ) -> Dict:
        """Perform risk analysis."""
        risk_factors = []
        risk_score = 0.0
        
        # Fundamental risks
        health = fundamental_analysis.get('financial_health_analysis', {})
        debt_risk = health.get('debt_to_equity', {}).get('risk_level', 'Low')
        if debt_risk in ['High', 'Very High']:
            risk_factors.append(f"High debt levels (D/E risk: {debt_risk})")
            risk_score += 0.2
        
        valuation = fundamental_analysis.get('valuation_analysis', {})
        if valuation.get('pe_vs_sector') == 'overvalued':
            risk_factors.append("Overvalued compared to sector peers")
            risk_score += 0.15
        
        # Market risks
        volatility = market_analysis.get('volatility_analysis', {})
        vol_level = volatility.get('level', 'Moderate')
        if vol_level in ['High', 'Very High']:
            risk_factors.append(f"{vol_level} market volatility (VIX: {volatility.get('vix', 0):.1f})")
            risk_score += 0.2
        
        trend = market_analysis.get('trend_analysis', {}).get('overall_trend', 'neutral')
        if trend == 'bearish':
            risk_factors.append("Bearish market trend")
            risk_score += 0.15
        
        # Subscription risks
        total_sub = subscription_data.get('total_subscription', 0)
        if total_sub < 3:
            risk_factors.append(f"Weak subscription ({total_sub:.1f}x)")
            risk_score += 0.2
        
        # GMP risks
        gmp_pct = gmp_data.get('gmp_percentage', 0)
        if gmp_pct < 0:
            risk_factors.append(f"Negative GMP ({gmp_pct:.1f}%)")
            risk_score += 0.2
        
        gmp_trend = gmp_data.get('gmp_trend', 'stable')
        if gmp_trend == 'decreasing':
            risk_factors.append("Declining GMP trend")
            risk_score += 0.1
        
        # Determine risk level
        risk_score = min(1.0, risk_score)
        
        if risk_score <= self.thresholds['low_risk']:
            risk_level = RiskLevel.LOW
        elif risk_score <= self.thresholds['medium_risk']:
            risk_level = RiskLevel.MEDIUM
        elif risk_score <= 0.8:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.VERY_HIGH
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "mitigation_suggestions": self._get_risk_mitigation(risk_factors)
        }
    
    def _get_risk_mitigation(self, risk_factors: List[str]) -> List[str]:
        """Generate risk mitigation suggestions."""
        suggestions = []
        
        for factor in risk_factors:
            if 'debt' in factor.lower():
                suggestions.append("Consider reduced position size due to leverage risk")
            elif 'overvalued' in factor.lower():
                suggestions.append("Wait for price correction or avoid at current levels")
            elif 'volatility' in factor.lower():
                suggestions.append("Use tight stop-loss; consider partial exit on listing")
            elif 'bearish' in factor.lower():
                suggestions.append("Be cautious; market headwinds may affect listing performance")
            elif 'subscription' in factor.lower():
                suggestions.append("Low institutional interest is a warning sign")
            elif 'gmp' in factor.lower() and 'negative' in factor.lower():
                suggestions.append("Avoid or exit pre-listing if possible")
            elif 'declining' in factor.lower():
                suggestions.append("Monitor closely; sentiment may be deteriorating")
        
        if not suggestions:
            suggestions.append("Standard risk management practices apply")
        
        return suggestions
    
    def _generate_pre_listing_decision(
        self,
        composite_score: float,
        risk_analysis: Dict,
        ml_prediction: Dict = None
    ) -> Dict:
        """Generate pre-listing trading recommendation."""
        
        # Base decision from composite score
        if composite_score >= self.thresholds['strong_apply']:
            base_decision = Decision.STRONG_APPLY
            action_text = "Strongly recommended to apply"
        elif composite_score >= self.thresholds['apply']:
            base_decision = Decision.APPLY
            action_text = "Recommended to apply"
        elif composite_score >= self.thresholds['hold']:
            base_decision = Decision.HOLD
            action_text = "Hold - Wait for more clarity"
        elif composite_score >= self.thresholds['avoid']:
            base_decision = Decision.AVOID
            action_text = "Avoid applying"
        else:
            base_decision = Decision.STRONG_AVOID
            action_text = "Strongly avoid - High risk"
        
        # Adjust for risk level
        risk_level = risk_analysis.get('risk_level', 'Medium')
        if risk_level == 'Very High' and base_decision in [Decision.STRONG_APPLY, Decision.APPLY]:
            base_decision = Decision.HOLD
            action_text = "Hold due to high risk factors"
        elif risk_level == 'High' and base_decision == Decision.STRONG_APPLY:
            base_decision = Decision.APPLY
            action_text = "Apply with caution due to elevated risks"
        
        # Consider ML prediction if available
        ml_agreement = True
        if ml_prediction:
            ml_pred = ml_prediction.get('prediction', '')
            if 'Apply' in ml_pred and base_decision in [Decision.AVOID, Decision.STRONG_AVOID]:
                ml_agreement = False
            elif 'Avoid' in ml_pred and base_decision in [Decision.APPLY, Decision.STRONG_APPLY]:
                ml_agreement = False
        
        # Calculate confidence
        base_confidence = min(0.95, 0.5 + abs(composite_score - 0.5))
        if not ml_agreement:
            base_confidence *= 0.8
        
        return {
            "decision": base_decision.value,
            "action": action_text,
            "confidence": round(base_confidence, 2),
            "composite_score": composite_score,
            "risk_adjusted": risk_level in ['High', 'Very High'],
            "ml_agreement": ml_agreement if ml_prediction else None
        }
    
    def _generate_listing_strategy(
        self,
        composite_score: float,
        risk_analysis: Dict,
        gmp_data: Dict,
        market_analysis: Dict
    ) -> Dict:
        """Generate listing day trading strategy."""
        
        gmp_pct = gmp_data.get('gmp_percentage', 0)
        volatility = market_analysis.get('volatility_analysis', {}).get('level', 'Moderate')
        risk_level = risk_analysis.get('risk_level', 'Medium')
        
        # Determine expected listing behavior
        if gmp_pct >= 30:
            expected_listing = "Strong positive"
            listing_gain_range = f"{gmp_pct - 10:.0f}% - {gmp_pct + 20:.0f}%"
        elif gmp_pct >= 15:
            expected_listing = "Positive"
            listing_gain_range = f"{gmp_pct - 5:.0f}% - {gmp_pct + 10:.0f}%"
        elif gmp_pct >= 0:
            expected_listing = "Mild positive to flat"
            listing_gain_range = f"{max(-5, gmp_pct - 10):.0f}% - {gmp_pct + 5:.0f}%"
        elif gmp_pct >= -10:
            expected_listing = "Flat to negative"
            listing_gain_range = f"{gmp_pct - 5:.0f}% - {gmp_pct + 5:.0f}%"
        else:
            expected_listing = "Negative"
            listing_gain_range = f"{gmp_pct - 10:.0f}% - {gmp_pct + 5:.0f}%"
        
        # Generate strategy
        strategies = []
        
        if composite_score >= 0.7 and risk_level == 'Low':
            strategies.append({
                "action": "Hold for long term",
                "reasoning": "Strong fundamentals suggest long-term value creation",
                "target": "12-18 months holding"
            })
        
        if gmp_pct >= 20:
            profit_target = gmp_pct * 0.7  # 70% of GMP as realistic target
            strategies.append({
                "action": "Partial profit booking",
                "reasoning": f"Book 50% at {profit_target:.0f}% gain, hold rest",
                "target": f"Exit price: ₹{self._calculate_target_price(gmp_data, profit_target)}"
            })
        
        if volatility in ['High', 'Very High']:
            strategies.append({
                "action": "Set tight stop-loss",
                "reasoning": "High volatility may cause sharp swings",
                "target": "Stop-loss at 8-10% below listing price"
            })
        
        if gmp_pct < 5:
            strategies.append({
                "action": "Exit on listing",
                "reasoning": "Low or negative GMP suggests limited upside",
                "target": "Exit at any profit or small loss"
            })
        
        # Default strategy
        if not strategies:
            strategies.append({
                "action": "Monitor and decide",
                "reasoning": "Watch first 30 minutes of trading",
                "target": "Decide based on price action"
            })
        
        return {
            "expected_listing": expected_listing,
            "expected_gain_range": listing_gain_range,
            "strategies": strategies,
            "stop_loss_suggested": f"{self.thresholds['sell_stop_loss'] * 100:.0f}%",
            "profit_target_suggested": f"{self.thresholds['sell_profit_target'] * 100:.0f}%"
        }
    
    def _calculate_target_price(self, gmp_data: Dict, target_pct: float) -> str:
        """Calculate target exit price."""
        # This would use actual issue price in production
        return f"Issue + {target_pct:.0f}%"
    
    def _generate_insights(
        self,
        scores: Dict,
        risk_analysis: Dict,
        fundamental_analysis: Dict,
        sentiment_analysis: Dict,
        market_analysis: Dict,
        subscription_data: Dict,
        gmp_data: Dict
    ) -> Dict:
        """Generate actionable insights."""
        
        positives = []
        negatives = []
        key_metrics = []
        
        # Fundamental insights
        fund_score = scores['fundamental_score']
        if fund_score >= 0.7:
            positives.append("Strong fundamental profile with healthy financials")
        elif fund_score < 0.4:
            negatives.append("Weak fundamentals raise concerns about long-term prospects")
        
        # Add key fundamental insights
        if 'key_insights' in fundamental_analysis:
            for insight in fundamental_analysis['key_insights'][:3]:
                if insight.startswith('✓'):
                    positives.append(insight[2:])
                elif insight.startswith('⚠'):
                    negatives.append(insight[2:])
        
        # Sentiment insights
        sent_score = scores['sentiment_score']
        sent_label = sentiment_analysis.get('sentiment_label', 'neutral')
        if sent_label == 'positive':
            positives.append(f"Positive market sentiment with {sentiment_analysis.get('article_count', 0)} news articles analyzed")
        elif sent_label == 'negative':
            negatives.append("Negative sentiment in news coverage")
        
        # Market insights
        market_condition = market_analysis.get('market_condition', 'Neutral')
        if 'Favorable' in market_condition:
            positives.append(f"Market conditions are {market_condition.lower()} for IPO listing")
        elif 'Unfavorable' in market_condition:
            negatives.append(f"Market conditions are {market_condition.lower()} - timing concern")
        
        # Subscription insights
        total_sub = subscription_data.get('total_subscription', 0)
        if total_sub >= 50:
            positives.append(f"Excellent subscription of {total_sub:.1f}x indicates strong demand")
        elif total_sub >= 10:
            positives.append(f"Good subscription of {total_sub:.1f}x shows healthy interest")
        elif total_sub < 3:
            negatives.append(f"Weak subscription of {total_sub:.1f}x is a red flag")
        
        qib = subscription_data.get('qib_subscription', 0)
        if qib >= 50:
            positives.append(f"Strong QIB participation ({qib:.1f}x) shows institutional confidence")
        
        # GMP insights
        gmp_pct = gmp_data.get('gmp_percentage', 0)
        if gmp_pct >= 25:
            positives.append(f"Strong GMP of {gmp_pct:.1f}% indicates potential listing gains")
        elif gmp_pct < 0:
            negatives.append(f"Negative GMP of {gmp_pct:.1f}% - listing may disappoint")
        
        # Key metrics summary
        key_metrics = [
            {"label": "Subscription", "value": f"{total_sub:.1f}x", "status": "good" if total_sub >= 10 else "warning" if total_sub >= 3 else "bad"},
            {"label": "GMP", "value": f"{gmp_pct:.1f}%", "status": "good" if gmp_pct >= 15 else "warning" if gmp_pct >= 0 else "bad"},
            {"label": "Risk Level", "value": risk_analysis.get('risk_level', 'Medium'), "status": "good" if risk_analysis.get('risk_level') == 'Low' else "warning" if risk_analysis.get('risk_level') == 'Medium' else "bad"},
            {"label": "Market", "value": market_condition, "status": "good" if 'Favorable' in market_condition else "warning" if 'Neutral' in market_condition else "bad"}
        ]
        
        return {
            "positives": positives,
            "negatives": negatives,
            "key_metrics": key_metrics,
            "summary": self._generate_summary(positives, negatives, scores)
        }
    
    def _generate_summary(
        self,
        positives: List[str],
        negatives: List[str],
        scores: Dict
    ) -> str:
        """Generate executive summary."""
        composite = sum(scores.values()) / len(scores)
        
        if composite >= 0.7:
            tone = "This IPO presents a compelling investment opportunity"
        elif composite >= 0.55:
            tone = "This IPO shows promise but comes with some considerations"
        elif composite >= 0.4:
            tone = "This IPO requires careful evaluation of risks"
        else:
            tone = "This IPO carries significant risks that outweigh potential rewards"
        
        pos_count = len(positives)
        neg_count = len(negatives)
        
        if pos_count > neg_count + 2:
            balance = "with predominantly positive indicators"
        elif neg_count > pos_count + 2:
            balance = "with concerning negative factors"
        else:
            balance = "with a mixed bag of positives and concerns"
        
        return f"{tone} {balance}."


# Module-level instance
decision_engine = DecisionEngine()


if __name__ == "__main__":
    # Test the decision engine
    from src.data.ipo_data_collector import IPODataCollector
    from src.data.fundamental_analyzer import FundamentalAnalyzer
    from src.intelligence.sentiment_analyzer import SentimentAnalyzer
    from src.intelligence.market_analyzer import MarketAnalyzer
    
    # Collect data
    collector = IPODataCollector()
    ipo_id = "IPO001"
    complete_data = collector.get_complete_ipo_data(ipo_id)
    
    # Run analyzers
    fund_analyzer = FundamentalAnalyzer()
    fund_result = fund_analyzer.analyze(
        complete_data['fundamentals'],
        complete_data['basic_info']
    )
    
    sent_analyzer = SentimentAnalyzer()
    sent_result = sent_analyzer.analyze(ipo_id, complete_data['basic_info']['company_name'])
    
    market_analyzer = MarketAnalyzer()
    market_result = market_analyzer.analyze(
        complete_data['market'],
        complete_data['basic_info']['sector']
    )
    
    # Generate decision
    engine = DecisionEngine()
    result = engine.analyze_ipo(
        basic_info=complete_data['basic_info'],
        fundamental_analysis=fund_result,
        sentiment_analysis=sent_result,
        market_analysis=market_result,
        subscription_data=complete_data['subscription'],
        gmp_data=complete_data['gmp']
    )
    
    print("\n" + "="*60)
    print("IPO ANALYSIS REPORT")
    print("="*60)
    print(f"\nCompany: {result['ipo_info']['company_name']}")
    print(f"Sector: {result['ipo_info']['sector']}")
    print(f"Price Band: {result['ipo_info']['price_band']}")
    print(f"\nComposite Score: {result['composite_score']:.3f}")
    print(f"Risk Level: {result['risk_analysis']['risk_level']}")
    print(f"\n--- RECOMMENDATION ---")
    print(f"Decision: {result['pre_listing_recommendation']['decision']}")
    print(f"Action: {result['pre_listing_recommendation']['action']}")
    print(f"Confidence: {result['pre_listing_recommendation']['confidence']:.0%}")
    print(f"\n--- LISTING STRATEGY ---")
    print(f"Expected: {result['listing_day_strategy']['expected_listing']}")
    print(f"Range: {result['listing_day_strategy']['expected_gain_range']}")
