"""
Sentiment Analysis Engine
=========================
NLP-based sentiment analysis for IPO-related news and social media.
Uses VADER sentiment analyzer and custom IPO-specific lexicon.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
import re
from datetime import datetime, timedelta
from collections import Counter

# NLP imports
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import SENTIMENT_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
def download_nltk_data():
    """Download required NLTK data."""
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    try:
        nltk.data.find('punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)
    try:
        nltk.data.find('stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

download_nltk_data()


class SentimentAnalyzer:
    """
    IPO-specific sentiment analysis engine.
    
    Features:
    - VADER-based sentiment scoring
    - Custom IPO financial lexicon
    - News aggregation and analysis
    - Trend detection
    - Key topic extraction
    """
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self._add_custom_lexicon()
        self.config = SENTIMENT_CONFIG
        
    def _add_custom_lexicon(self):
        """Add IPO-specific terms to VADER lexicon."""
        # Positive IPO terms
        positive_terms = {
            'oversubscribed': 3.0,
            'blockbuster': 3.5,
            'stellar': 3.0,
            'robust': 2.5,
            'strong demand': 3.0,
            'premium listing': 2.5,
            'bumper': 3.0,
            'bullish': 2.5,
            'upbeat': 2.0,
            'healthy': 2.0,
            'growth': 2.0,
            'profitable': 2.5,
            'market leader': 2.5,
            'qib': 1.5,  # QIB participation is positive
            'anchor investors': 2.0,
            'expansion': 1.5,
            'innovation': 1.5,
            'subscribe': 1.0
        }
        
        # Negative IPO terms
        negative_terms = {
            'undersubscribed': -3.0,
            'tepid': -2.0,
            'weak': -2.5,
            'concern': -2.0,
            'overvalued': -2.5,
            'expensive': -2.0,
            'debt-laden': -3.0,
            'loss-making': -3.5,
            'avoid': -2.5,
            'skip': -2.0,
            'risky': -2.0,
            'volatile': -1.5,
            'crash': -3.5,
            'plunge': -3.0,
            'slump': -2.5,
            'bearish': -2.5,
            'cautious': -1.5,
            'downgrade': -2.5,
            'withdrawal': -2.0,
            'grey market negative': -2.5
        }
        
        # Neutral/context terms
        neutral_terms = {
            'ipo': 0.0,
            'listing': 0.0,
            'shares': 0.0,
            'equity': 0.0,
            'offer': 0.0,
            'price band': 0.0
        }
        
        # Add all terms to VADER lexicon
        for term, score in {**positive_terms, **negative_terms, **neutral_terms}.items():
            self.vader.lexicon[term] = score
    
    def analyze(self, ipo_id: str, company_name: str) -> Dict:
        """
        Perform comprehensive sentiment analysis for an IPO.
        
        Args:
            ipo_id: Unique identifier for the IPO
            company_name: Company name for news search
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        logger.info(f"Analyzing sentiment for {company_name}")
        
        # Get news articles (simulated for demo)
        articles = self._get_news_articles(ipo_id, company_name)
        
        if not articles:
            return self._get_neutral_result()
        
        # Analyze each article
        article_sentiments = []
        for article in articles:
            sentiment = self._analyze_article(article)
            article_sentiments.append(sentiment)
        
        # Aggregate results
        aggregated = self._aggregate_sentiments(article_sentiments)
        
        # Extract key topics
        all_text = " ".join([a['content'] for a in articles])
        key_topics = self._extract_key_topics(all_text)
        
        # Detect sentiment trend
        trend = self._detect_trend(article_sentiments)
        
        return {
            "composite_score": aggregated["average_score"],
            "sentiment_label": aggregated["overall_label"],
            "confidence": aggregated["confidence"],
            "article_count": len(articles),
            "positive_count": aggregated["positive_count"],
            "negative_count": aggregated["negative_count"],
            "neutral_count": aggregated["neutral_count"],
            "key_topics": key_topics,
            "trend": trend,
            "articles_analyzed": article_sentiments[:5],  # Top 5 for display
            "assessment": self._get_sentiment_assessment(aggregated)
        }
    
    def _get_news_articles(self, ipo_id: str, company_name: str) -> List[Dict]:
        """
        Get news articles for analysis.
        In production, this would scrape real news sources.
        """
        # Simulated news data for different IPOs
        news_data = {
            "IPO001": [
                {
                    "title": "TechVision AI IPO sees strong anchor investor interest",
                    "content": "TechVision AI Ltd's IPO has received overwhelming response from anchor investors, with marquee names like Goldman Sachs and Morgan Stanley participating. The AI-focused company has seen robust demand with the anchor portion being fully subscribed. Analysts are bullish on the company's growth prospects in the rapidly expanding AI sector.",
                    "source": "Economic Times",
                    "date": "2026-01-15"
                },
                {
                    "title": "TechVision AI: Strong fundamentals justify premium valuation",
                    "content": "Despite premium pricing, analysts believe TechVision AI's IPO offers good value given its market leadership and consistent profitability. The company has shown stellar revenue growth of 40% CAGR over last 3 years. Subscribe for long-term gains, say experts.",
                    "source": "Moneycontrol",
                    "date": "2026-01-16"
                },
                {
                    "title": "Grey market premium for TechVision AI rises to Rs 85",
                    "content": "The grey market premium for TechVision AI IPO has surged to Rs 85, indicating potential listing gains of over 28%. Strong subscription numbers and positive sentiment are driving the premium higher. Market participants expect bumper listing.",
                    "source": "Livemint",
                    "date": "2026-01-16"
                }
            ],
            "IPO002": [
                {
                    "title": "GreenEnergy Solutions IPO: Moderate interest from institutions",
                    "content": "GreenEnergy Solutions Ltd's IPO has seen moderate demand from institutional investors. While the renewable energy sector is growing, concerns about execution and competition remain. The subscription is expected to be decent but not spectacular.",
                    "source": "Business Standard",
                    "date": "2026-01-17"
                },
                {
                    "title": "Should you subscribe to GreenEnergy Solutions IPO?",
                    "content": "Analysts have mixed views on GreenEnergy IPO. While growth prospects are good, the valuation at P/E of 35x is slightly expensive compared to peers. Investors with high risk appetite may consider with caution.",
                    "source": "Economic Times",
                    "date": "2026-01-18"
                }
            ],
            "IPO003": [
                {
                    "title": "HealthCare Plus IPO: Blockbuster response expected",
                    "content": "HealthCare Plus Ltd's IPO is generating tremendous interest among all investor categories. The healthcare sector leader has strong fundamentals with consistent growth. QIB portion is already heavily oversubscribed. This is a must-subscribe IPO for long-term investors.",
                    "source": "Moneycontrol",
                    "date": "2026-01-14"
                },
                {
                    "title": "HealthCare Plus: Market leader at reasonable valuation",
                    "content": "With a P/E of 24.5x, HealthCare Plus offers attractive valuation for a market leader. The company's robust margins and debt-free status make it a compelling investment. Analysts unanimously recommend subscribe with a bullish outlook.",
                    "source": "CNBC TV18",
                    "date": "2026-01-15"
                },
                {
                    "title": "HealthCare Plus GMP indicates 25%+ listing gains",
                    "content": "Grey market premium for HealthCare Plus has touched Rs 145, suggesting potential listing gains of over 26%. Stellar subscription of 68x across categories. Experts predict premium listing and recommend holding for long term.",
                    "source": "Economic Times",
                    "date": "2026-01-16"
                }
            ],
            "IPO004": [
                {
                    "title": "FinServe Digital IPO: Fintech star gets stellar response",
                    "content": "FinServe Digital's IPO has been a blockbuster with 85x overall subscription. The digital financial services company has demonstrated exceptional growth and profitability. Strong balance sheet with low debt makes it a quality investment.",
                    "source": "Livemint",
                    "date": "2026-01-23"
                },
                {
                    "title": "FinServe Digital: The next multibagger in fintech?",
                    "content": "Analysts are extremely bullish on FinServe Digital. The company's innovative platform and market share expansion strategy position it well for continued growth. Premium valuation is justified by superior execution.",
                    "source": "Business Today",
                    "date": "2026-01-24"
                }
            ],
            "IPO005": [
                {
                    "title": "RetailMart IPO: Weak response raises concerns",
                    "content": "RetailMart India's IPO has received tepid response with total subscription at just 2.2x. High debt levels and thin margins are keeping investors away. The retail sector headwinds add to concerns about future growth.",
                    "source": "Economic Times",
                    "date": "2026-01-26"
                },
                {
                    "title": "Avoid RetailMart IPO: Analysts cite expensive valuation",
                    "content": "Most analysts recommend avoiding RetailMart IPO citing overvalued pricing at P/E of 42x for a loss-making company. Negative GMP and weak subscription indicate poor listing performance likely. Skip this one, say experts.",
                    "source": "Moneycontrol",
                    "date": "2026-01-27"
                }
            ],
            "IPO006": [
                {
                    "title": "AutoParts Manufacturing IPO: Decent subscription expected",
                    "content": "AutoParts Manufacturing Ltd's IPO is seeing reasonable interest with subscription at 12.5x. The automobile ancillary company has steady business with stable margins. Valuation is fair but not cheap.",
                    "source": "Business Standard",
                    "date": "2026-01-29"
                }
            ],
            "IPO007": [
                {
                    "title": "CloudTech Infrastructure IPO: Tech investors show strong interest",
                    "content": "CloudTech Infrastructure's IPO is witnessing robust demand from technology-focused investors. The cloud infrastructure company has shown stellar growth with 32% CAGR. QIB subscription at 95x indicates institutional confidence.",
                    "source": "CNBC TV18",
                    "date": "2026-02-02"
                },
                {
                    "title": "CloudTech: Strong growth story at reasonable valuation",
                    "content": "With expanding cloud adoption, CloudTech is well positioned for continued growth. Analysts are bullish on the IPO citing strong fundamentals and market opportunity. Subscribe for long term wealth creation.",
                    "source": "Economic Times",
                    "date": "2026-02-03"
                }
            ],
            "IPO008": [
                {
                    "title": "FoodProcessing Industries IPO: Steady performer",
                    "content": "FoodProcessing Industries' IPO is getting moderate response. The FMCG sector company has stable growth but nothing exceptional. Valuation is fair. Suitable for conservative investors looking for stable returns.",
                    "source": "Livemint",
                    "date": "2026-02-06"
                }
            ]
        }
        
        return news_data.get(ipo_id, [])
    
    def _analyze_article(self, article: Dict) -> Dict:
        """Analyze sentiment of a single article."""
        content = article.get('content', '')
        title = article.get('title', '')
        
        # Combine title and content (title has higher weight)
        full_text = f"{title} {title} {content}"
        
        # Get VADER scores
        scores = self.vader.polarity_scores(full_text)
        
        # Determine label
        compound = scores['compound']
        if compound >= self.config['vader_threshold_positive']:
            label = 'positive'
        elif compound <= self.config['vader_threshold_negative']:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            "title": title,
            "source": article.get('source', 'Unknown'),
            "date": article.get('date', ''),
            "compound_score": compound,
            "positive": scores['pos'],
            "negative": scores['neg'],
            "neutral": scores['neu'],
            "label": label
        }
    
    def _aggregate_sentiments(self, sentiments: List[Dict]) -> Dict:
        """Aggregate sentiment scores from multiple articles."""
        if not sentiments:
            return {
                "average_score": 0.0,
                "overall_label": "neutral",
                "confidence": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            }
        
        # Calculate average compound score
        avg_score = np.mean([s['compound_score'] for s in sentiments])
        
        # Count labels
        labels = [s['label'] for s in sentiments]
        positive_count = labels.count('positive')
        negative_count = labels.count('negative')
        neutral_count = labels.count('neutral')
        
        # Determine overall label
        if positive_count > negative_count and positive_count > neutral_count:
            overall_label = 'positive'
        elif negative_count > positive_count and negative_count > neutral_count:
            overall_label = 'negative'
        else:
            overall_label = 'neutral'
        
        # Calculate confidence based on agreement
        total = len(sentiments)
        max_count = max(positive_count, negative_count, neutral_count)
        confidence = max_count / total if total > 0 else 0.0
        
        # Normalize score to 0-1 range
        normalized_score = (avg_score + 1) / 2
        
        return {
            "average_score": normalized_score,
            "raw_score": avg_score,
            "overall_label": overall_label,
            "confidence": confidence,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count
        }
    
    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        # Financial keywords to look for
        keywords = {
            'subscription', 'oversubscribed', 'gmp', 'premium', 'valuation',
            'growth', 'profit', 'revenue', 'margin', 'debt', 'expansion',
            'market', 'sector', 'listing', 'institutional', 'retail',
            'anchor', 'qib', 'bullish', 'bearish', 'risk', 'opportunity'
        }
        
        # Tokenize and find matches
        words = word_tokenize(text.lower())
        found = [w for w in words if w in keywords]
        
        # Get most common
        counter = Counter(found)
        top_topics = [word for word, count in counter.most_common(5)]
        
        return top_topics
    
    def _detect_trend(self, sentiments: List[Dict]) -> str:
        """Detect sentiment trend over time."""
        if len(sentiments) < 2:
            return "stable"
        
        # Sort by date
        sorted_sentiments = sorted(sentiments, key=lambda x: x.get('date', ''))
        
        # Compare first half vs second half
        mid = len(sorted_sentiments) // 2
        first_half_avg = np.mean([s['compound_score'] for s in sorted_sentiments[:mid]])
        second_half_avg = np.mean([s['compound_score'] for s in sorted_sentiments[mid:]])
        
        diff = second_half_avg - first_half_avg
        
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _get_sentiment_assessment(self, aggregated: Dict) -> str:
        """Generate sentiment assessment text."""
        score = aggregated["average_score"]
        label = aggregated["overall_label"]
        trend = aggregated.get("trend", "stable")
        
        if label == "positive":
            if score >= 0.7:
                base = "Highly positive sentiment - Strong market confidence"
            else:
                base = "Positive sentiment - Generally favorable outlook"
        elif label == "negative":
            if score <= 0.3:
                base = "Strongly negative sentiment - Significant concerns"
            else:
                base = "Negative sentiment - Market has reservations"
        else:
            base = "Neutral sentiment - Mixed or limited coverage"
        
        return base
    
    def _get_neutral_result(self) -> Dict:
        """Return neutral result when no data available."""
        return {
            "composite_score": 0.5,
            "sentiment_label": "neutral",
            "confidence": 0.0,
            "article_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "key_topics": [],
            "trend": "unknown",
            "articles_analyzed": [],
            "assessment": "No news data available for sentiment analysis"
        }
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis result
        """
        scores = self.vader.polarity_scores(text)
        
        compound = scores['compound']
        if compound >= self.config['vader_threshold_positive']:
            label = 'positive'
        elif compound <= self.config['vader_threshold_negative']:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            "compound_score": compound,
            "normalized_score": (compound + 1) / 2,
            "label": label,
            "positive": scores['pos'],
            "negative": scores['neg'],
            "neutral": scores['neu']
        }


# Module-level instance
sentiment_analyzer = SentimentAnalyzer()


if __name__ == "__main__":
    # Test sentiment analysis
    analyzer = SentimentAnalyzer()
    
    # Test with sample IPO
    result = analyzer.analyze("IPO001", "TechVision AI Ltd")
    
    print("\nSentiment Analysis Results:")
    print(f"Composite Score: {result['composite_score']:.3f}")
    print(f"Sentiment Label: {result['sentiment_label']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Articles Analyzed: {result['article_count']}")
    print(f"Positive: {result['positive_count']}, Negative: {result['negative_count']}, Neutral: {result['neutral_count']}")
    print(f"Key Topics: {result['key_topics']}")
    print(f"Trend: {result['trend']}")
    print(f"Assessment: {result['assessment']}")
