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
    
    # In-memory cache: {cache_key: (timestamp, articles)}
    _news_cache: Dict = {}
    _CACHE_TTL = 1800  # 30 minutes

    def _get_news_articles(self, ipo_id: str, company_name: str) -> List[Dict]:
        """
        Get news articles for analysis.
        First tries static data for known IPOs, then fetches live news
        from Google News RSS for unknown IPOs.
        """
        import time
        import requests
        import xml.etree.ElementTree as ET
        from datetime import datetime as dt

        # Static fallback for known demo IPOs
        static_data = {
            "IPO001": [
                {"title": "TechVision AI IPO sees strong anchor investor interest",
                 "content": "TechVision AI Ltd IPO received overwhelming response from anchor investors. The AI-focused company has seen robust demand. Analysts are bullish on growth prospects.",
                 "source": "Economic Times", "date": "2026-01-15"},
                {"title": "TechVision AI: Strong fundamentals justify premium valuation",
                 "content": "Despite premium pricing, analysts believe TechVision AI IPO offers good value. Stellar revenue growth of 40% CAGR. Subscribe for long-term gains.",
                 "source": "Moneycontrol", "date": "2026-01-16"},
            ],
            "IPO002": [
                {"title": "GreenEnergy Solutions IPO: Moderate interest",
                 "content": "GreenEnergy IPO has seen moderate demand. Concerns about execution and competition remain. Subscription expected to be decent.",
                 "source": "Business Standard", "date": "2026-01-17"},
            ],
            "IPO003": [
                {"title": "HealthCare Plus IPO: Blockbuster response",
                 "content": "HealthCare Plus IPO generating tremendous interest. QIB portion heavily oversubscribed. Must-subscribe for long-term investors.",
                 "source": "Moneycontrol", "date": "2026-01-14"},
                {"title": "HealthCare Plus: Market leader at reasonable valuation",
                 "content": "Robust margins and debt-free status make compelling investment. Analysts unanimously recommend subscribe with bullish outlook.",
                 "source": "CNBC TV18", "date": "2026-01-15"},
            ],
            "IPO004": [
                {"title": "FinServe Digital IPO: Stellar response",
                 "content": "FinServe Digital IPO blockbuster with 85x subscription. Exceptional growth and profitability. Strong balance sheet.",
                 "source": "Livemint", "date": "2026-01-23"},
            ],
            "IPO005": [
                {"title": "RetailMart IPO: Weak response raises concerns",
                 "content": "RetailMart IPO tepid response with 2.2x subscription. High debt and thin margins keeping investors away.",
                 "source": "Economic Times", "date": "2026-01-26"},
                {"title": "Avoid RetailMart IPO: Analysts cite expensive valuation",
                 "content": "Most analysts recommend avoiding RetailMart IPO. Loss-making company at P/E 42x. Skip this one.",
                 "source": "Moneycontrol", "date": "2026-01-27"},
            ],
        }

        if ipo_id in static_data:
            return static_data[ipo_id]

        # Try live Google News RSS feed
        cache_key = company_name.lower().strip()
        now = time.time()

        # Return cached result if fresh
        if cache_key in SentimentAnalyzer._news_cache:
            ts, cached_articles = SentimentAnalyzer._news_cache[cache_key]
            if now - ts < SentimentAnalyzer._CACHE_TTL:
                logger.info(f"Returning cached news for {company_name}")
                return cached_articles

        try:
            query = f"{company_name} IPO"
            rss_url = (
                f"https://news.google.com/rss/search"
                f"?q={requests.utils.quote(query)}"
                f"&hl=en-IN&gl=IN&ceid=IN:en"
            )
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(rss_url, headers=headers, timeout=8)
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            articles = []
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                description = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None else "Google News"

                # Clean HTML tags from description
                import re
                clean_desc = re.sub(r"<[^>]+>", " ", description).strip()

                if title:
                    # Parse date
                    try:
                        parsed_date = dt.strptime(pub_date[:16], "%a, %d %b %Y").strftime("%Y-%m-%d")
                    except Exception:
                        parsed_date = dt.now().strftime("%Y-%m-%d")

                    articles.append({
                        "title": title,
                        "content": f"{title}. {clean_desc}",
                        "source": source,
                        "date": parsed_date
                    })

            logger.info(f"Fetched {len(articles)} live news articles for {company_name}")

            # Cache the result
            SentimentAnalyzer._news_cache[cache_key] = (now, articles)
            return articles

        except Exception as e:
            logger.warning(f"Live news fetch failed for {company_name}: {e}")
            return []
    
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
