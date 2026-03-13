"""
Integrated IPO Analysis Pipeline
================================
Combines all modules into a single analysis pipeline.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.ipo_data_collector import IPODataCollector
from src.data.fundamental_analyzer import FundamentalAnalyzer
from src.data.database_manager import DatabaseManager
from src.intelligence.sentiment_analyzer import SentimentAnalyzer
from src.intelligence.market_analyzer import MarketAnalyzer
from src.intelligence.ml_predictor import IPOPredictionModel
from src.decision.decision_engine import DecisionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPOAnalysisPipeline:
    """
    End-to-end IPO analysis pipeline.
    
    Orchestrates data collection, analysis, and recommendation generation.
    """
    
    def __init__(self):
        self.data_collector = IPODataCollector()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.market_analyzer = MarketAnalyzer()
        self.ml_predictor = IPOPredictionModel()
        self.decision_engine = DecisionEngine()
        self.db_manager = DatabaseManager()
        
        # Train ML model
        logger.info("Initializing ML models...")
        self.ml_predictor.train()
    
    def get_all_ipos(self):
        """Get list of all IPOs."""
        return self.data_collector.collect_ipo_listings()
    
    def analyze_ipo(self, ipo_id: str) -> Dict:
        """
        Perform complete analysis for a single IPO.
        
        Args:
            ipo_id: Unique identifier for the IPO
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting analysis pipeline for {ipo_id}")
        
        # Step 1: Collect data
        complete_data = self.data_collector.get_complete_ipo_data(ipo_id)
        if not complete_data:
            return {"error": f"IPO {ipo_id} not found"}
        
        basic_info = complete_data['basic_info']
        fundamentals = complete_data['fundamentals']
        subscription = complete_data['subscription']
        gmp = complete_data['gmp']
        market = complete_data['market']
        
        # Step 2: Fundamental analysis
        fundamental_result = self.fundamental_analyzer.analyze(fundamentals, basic_info)
        
        # Step 3: Sentiment analysis
        sentiment_result = self.sentiment_analyzer.analyze(
            ipo_id, 
            basic_info['company_name']
        )
        
        # Step 4: Market analysis
        market_result = self.market_analyzer.analyze(
            market, 
            basic_info['sector']
        )
        
        # Step 5: ML prediction
        ml_input = {
            "basic_info": basic_info,
            "fundamentals": fundamentals,
            "subscription": subscription,
            "gmp": gmp,
            "market": market,
            "sentiment": sentiment_result
        }
        ml_prediction = self.ml_predictor.predict(ml_input)
        
        # Step 6: Generate decision
        decision_result = self.decision_engine.analyze_ipo(
            basic_info=basic_info,
            fundamental_analysis=fundamental_result,
            sentiment_analysis=sentiment_result,
            market_analysis=market_result,
            subscription_data=subscription,
            gmp_data=gmp,
            ml_prediction=ml_prediction
        )
        
        # Compile complete result
        result = {
            "ipo_id": ipo_id,
            "basic_info": basic_info,
            "raw_data": {
                "fundamentals": fundamentals,
                "subscription": subscription,
                "gmp": gmp
            },
            "analysis": {
                "fundamental": fundamental_result,
                "sentiment": sentiment_result,
                "market": market_result
            },
            "ml_prediction": ml_prediction,
            "decision": decision_result,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def analyze_all_ipos(self) -> List[Dict]:
        """Analyze all available IPOs."""
        ipos = self.get_all_ipos()
        results = []
        
        for _, ipo in ipos.iterrows():
            try:
                result = self.analyze_ipo(ipo['ipo_id'])
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {ipo['ipo_id']}: {e}")
                results.append({
                    "ipo_id": ipo['ipo_id'],
                    "error": str(e)
                })
        
        return results
    
    def get_ipo_summary(self, ipo_id: str) -> Dict:
        """Get a quick summary for an IPO."""
        result = self.analyze_ipo(ipo_id)
        
        if "error" in result:
            return result
        
        decision = result['decision']
        
        return {
            "ipo_id": ipo_id,
            "company_name": result['basic_info']['company_name'],
            "sector": result['basic_info']['sector'],
            "price_band": f"₹{result['basic_info']['price_band_low']} - ₹{result['basic_info']['price_band_high']}",
            "issue_size": f"₹{result['basic_info']['issue_size_cr']} Cr",
            "listing_date": result['basic_info']['listing_date'],
            "recommendation": decision['pre_listing_recommendation']['decision'],
            "confidence": decision['pre_listing_recommendation']['confidence'],
            "risk_level": decision['risk_analysis']['risk_level'],
            "composite_score": decision['composite_score'],
            "gmp": f"{result['raw_data']['gmp']['gmp_percentage']:.1f}%",
            "subscription": f"{result['raw_data']['subscription']['total_subscription']:.1f}x"
        }


# Create singleton instance
pipeline = IPOAnalysisPipeline()


if __name__ == "__main__":
    # Test the pipeline
    pipeline = IPOAnalysisPipeline()
    
    # Get all IPOs
    ipos = pipeline.get_all_ipos()
    print(f"Found {len(ipos)} IPOs\n")
    
    # Analyze first IPO
    ipo_id = ipos.iloc[0]['ipo_id']
    result = pipeline.analyze_ipo(ipo_id)
    
    print("="*60)
    print("COMPLETE IPO ANALYSIS")
    print("="*60)
    print(f"\nCompany: {result['basic_info']['company_name']}")
    print(f"Sector: {result['basic_info']['sector']}")
    print(f"\nDecision: {result['decision']['pre_listing_recommendation']['decision']}")
    print(f"Confidence: {result['decision']['pre_listing_recommendation']['confidence']:.0%}")
    print(f"Risk: {result['decision']['risk_analysis']['risk_level']}")
