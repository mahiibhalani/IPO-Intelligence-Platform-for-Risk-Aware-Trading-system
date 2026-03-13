"""
AI-Driven IPO Intelligence Platform - Streamlit Dashboard
==========================================================
Interactive web dashboard for IPO analysis and trading recommendations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.ipo_data_collector import IPODataCollector
from src.data.fundamental_analyzer import FundamentalAnalyzer
from src.intelligence.sentiment_analyzer import SentimentAnalyzer
from src.intelligence.market_analyzer import MarketAnalyzer
from src.intelligence.ml_predictor import IPOPredictionModel
from src.decision.decision_engine import DecisionEngine

# Page configuration
st.set_page_config(
    page_title="AI-Driven IPO Intelligence Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .recommendation-strong-apply {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .recommendation-apply {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .recommendation-hold {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .recommendation-avoid {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .insight-positive {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
    .insight-negative {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
    .risk-low {
        color: #28a745;
        font-weight: bold;
    }
    .risk-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .risk-high {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_components():
    """Initialize all analysis components."""
    data_collector = IPODataCollector()
    fundamental_analyzer = FundamentalAnalyzer()
    sentiment_analyzer = SentimentAnalyzer()
    market_analyzer = MarketAnalyzer()
    ml_predictor = IPOPredictionModel()
    decision_engine = DecisionEngine()
    
    # Train ML model
    ml_predictor.train()
    
    return {
        'data_collector': data_collector,
        'fundamental_analyzer': fundamental_analyzer,
        'sentiment_analyzer': sentiment_analyzer,
        'market_analyzer': market_analyzer,
        'ml_predictor': ml_predictor,
        'decision_engine': decision_engine
    }


@st.cache_data(ttl=300)
def get_ipo_data():
    """Get IPO data with caching."""
    components = initialize_components()
    return components['data_collector'].collect_ipo_listings()


def render_data_source_notice(ipo_df: pd.DataFrame):
    """Render the active dataset source and coverage note."""
    if ipo_df.empty or 'data_source' not in ipo_df.columns:
        return

    source = str(ipo_df['data_source'].mode().iat[0])
    if source == 'nse_api':
        st.info(
            "Live IPO listings, market data, and active total subscription are sourced from NSE. "
            "Fundamentals, sentiment, GMP, and category-wise subscription still use model proxies when no public live feed is available."
        )
    elif source == 'sample_fallback':
        st.warning("Live IPO feed is unavailable, so the dashboard is currently showing fallback sample data.")


def analyze_ipo(ipo_id: str, components: dict) -> dict:
    """Run complete analysis for an IPO."""
    data_collector = components['data_collector']
    fundamental_analyzer = components['fundamental_analyzer']
    sentiment_analyzer = components['sentiment_analyzer']
    market_analyzer = components['market_analyzer']
    ml_predictor = components['ml_predictor']
    decision_engine = components['decision_engine']
    
    # Collect data
    complete_data = data_collector.get_complete_ipo_data(ipo_id)
    if not complete_data:
        return None
    
    basic_info = complete_data['basic_info']
    fundamentals = complete_data['fundamentals']
    subscription = complete_data['subscription']
    gmp = complete_data['gmp']
    market = complete_data['market']
    
    # Run analyses
    fundamental_result = fundamental_analyzer.analyze(fundamentals, basic_info)
    sentiment_result = sentiment_analyzer.analyze(ipo_id, basic_info['company_name'])
    market_result = market_analyzer.analyze(market, basic_info['sector'])
    
    # ML prediction
    ml_input = {
        "basic_info": basic_info,
        "fundamentals": fundamentals,
        "subscription": subscription,
        "gmp": gmp,
        "market": market,
        "sentiment": sentiment_result
    }
    ml_prediction = ml_predictor.predict(ml_input)
    
    # Decision
    decision_result = decision_engine.analyze_ipo(
        basic_info=basic_info,
        fundamental_analysis=fundamental_result,
        sentiment_analysis=sentiment_result,
        market_analysis=market_result,
        subscription_data=subscription,
        gmp_data=gmp,
        ml_prediction=ml_prediction
    )
    
    return {
        "basic_info": basic_info,
        "fundamentals": fundamentals,
        "subscription": subscription,
        "gmp": gmp,
        "market": market,
        "fundamental_analysis": fundamental_result,
        "sentiment_analysis": sentiment_result,
        "market_analysis": market_result,
        "ml_prediction": ml_prediction,
        "decision": decision_result
    }


def create_score_gauge(score: float, title: str) -> go.Figure:
    """Create a gauge chart for scores."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "#ff6b6b"},
                {'range': [30, 50], 'color': "#feca57"},
                {'range': [50, 70], 'color': "#48dbfb"},
                {'range': [70, 100], 'color': "#1dd1a1"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score * 100
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def create_radar_chart(scores: dict) -> go.Figure:
    """Create a radar chart for multi-dimensional scores."""
    categories = list(scores.keys())
    values = [scores[k] * 100 for k in categories]
    values.append(values[0])  # Close the polygon
    categories.append(categories[0])
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=[c.replace('_', ' ').title() for c in categories],
        fill='toself',
        line_color='#667eea'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        height=350
    )
    return fig


def create_subscription_chart(subscription: dict) -> go.Figure:
    """Create subscription breakdown chart."""
    categories = ['QIB', 'NII', 'Retail']
    values = [
        subscription.get('qib_subscription', 0),
        subscription.get('nii_subscription', 0),
        subscription.get('retail_subscription', 0)
    ]
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=['#667eea', '#764ba2', '#f093fb'],
            text=[f'{v:.1f}x' for v in values],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Subscription by Category",
        yaxis_title="Subscription (times)",
        height=300
    )
    return fig


def render_recommendation_card(decision: dict):
    """Render the main recommendation card."""
    rec = decision['pre_listing_recommendation']
    recommendation = rec['decision']
    confidence = rec['confidence']
    
    # Determine CSS class based on recommendation
    if 'Strong Apply' in recommendation:
        css_class = 'recommendation-strong-apply'
    elif 'Apply' in recommendation:
        css_class = 'recommendation-apply'
    elif 'Hold' in recommendation:
        css_class = 'recommendation-hold'
    else:
        css_class = 'recommendation-avoid'
    
    st.markdown(f"""
    <div class="{css_class}">
        <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">AI RECOMMENDATION</div>
        <div>{recommendation}</div>
        <div style="font-size: 1rem; margin-top: 0.5rem;">Confidence: {confidence:.0%}</div>
    </div>
    """, unsafe_allow_html=True)


def render_risk_badge(risk_level: str):
    """Render risk level badge."""
    risk_colors = {
        'Low': '#28a745',
        'Medium': '#ffc107',
        'High': '#dc3545',
        'Very High': '#721c24'
    }
    color = risk_colors.get(risk_level, '#6c757d')
    
    st.markdown(f"""
    <div style="
        background-color: {color};
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: bold;
    ">
        Risk Level: {risk_level}
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    # Header
    st.markdown('<h1 class="main-header">📈 AI-Driven IPO Intelligence Platform</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Risk-Aware Trading Decisions Powered by Machine Learning</p>', unsafe_allow_html=True)
    
    # Initialize components
    with st.spinner("Initializing AI models..."):
        components = initialize_components()
    
    # Sidebar
    st.sidebar.image("https://img.icons8.com/fluency/96/000000/bullish.png", width=80)
    st.sidebar.title("Navigation")
    if st.sidebar.button("Refresh Live Data", use_container_width=True):
        components['data_collector'].clear_cache()
        get_ipo_data.clear()
        st.rerun()
    
    page = st.sidebar.radio(
        "Select View",
        ["🏠 Dashboard", "🔍 IPO Analysis", "📊 Market Overview", "🤖 Model Insights", "ℹ️ About"]
    )
    
    # Get IPO data
    ipo_df = get_ipo_data()
    source_label = "Live NSE" if not ipo_df.empty and 'data_source' in ipo_df.columns and ipo_df['data_source'].eq('nse_api').any() else "Fallback Sample"
    st.sidebar.caption(f"Dataset: {source_label}")
    
    if page == "🏠 Dashboard":
        render_dashboard(ipo_df, components)
    elif page == "🔍 IPO Analysis":
        render_ipo_analysis(ipo_df, components)
    elif page == "📊 Market Overview":
        render_market_overview(components)
    elif page == "🤖 Model Insights":
        render_model_insights(components)
    else:
        render_about()


def render_dashboard(ipo_df: pd.DataFrame, components: dict):
    """Render main dashboard."""
    st.header("IPO Dashboard")
    render_data_source_notice(ipo_df)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total IPOs", len(ipo_df), delta="Active")
    
    with col2:
        upcoming = len(ipo_df[ipo_df['listing_date'] > datetime.now().strftime('%Y-%m-%d')])
        st.metric("Upcoming Listings", upcoming)
    
    with col3:
        avg_size = ipo_df['issue_size_cr'].mean()
        st.metric("Avg Issue Size", f"₹{avg_size:.0f} Cr")
    
    with col4:
        st.metric("AI Models Active", "3", delta="Trained")
    
    st.markdown("---")
    
    # Quick analysis table
    st.subheader("📋 IPO Quick Analysis")
    
    # Create summary for each IPO
    summaries = []
    for _, ipo in ipo_df.iterrows():
        result = analyze_ipo(ipo['ipo_id'], components)
        if result:
            decision = result['decision']
            summaries.append({
                'Company': ipo['company_name'],
                'Sector': ipo['sector'],
                'Price Band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'Issue Size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'GMP': f"{result['gmp']['gmp_percentage']:.1f}%",
                'Subscription': f"{result['subscription']['total_subscription']:.1f}x",
                'Score': f"{decision['composite_score']:.2f}",
                'Risk': decision['risk_analysis']['risk_level'],
                'Recommendation': decision['pre_listing_recommendation']['decision']
            })
    
    summary_df = pd.DataFrame(summaries)
    
    # Style the dataframe
    def color_recommendation(val):
        if 'Strong Apply' in str(val):
            return 'background-color: #d4edda; color: #155724'
        elif 'Apply' in str(val):
            return 'background-color: #d1ecf1; color: #0c5460'
        elif 'Hold' in str(val):
            return 'background-color: #fff3cd; color: #856404'
        else:
            return 'background-color: #f8d7da; color: #721c24'
    
    def color_risk(val):
        if val == 'Low':
            return 'color: #28a745; font-weight: bold'
        elif val == 'Medium':
            return 'color: #ffc107; font-weight: bold'
        else:
            return 'color: #dc3545; font-weight: bold'
    
    styled_df = summary_df.style.map(
        color_recommendation, subset=['Recommendation']
    ).map(
        color_risk, subset=['Risk']
    )
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Score Distribution")
        scores = [float(s['Score']) for s in summaries]
        fig = px.histogram(
            x=scores,
            nbins=10,
            labels={'x': 'Composite Score', 'y': 'Count'},
            color_discrete_sequence=['#667eea']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏢 Sector Breakdown")
        sector_counts = summary_df['Sector'].value_counts()
        fig = px.pie(
            values=sector_counts.values,
            names=sector_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)


def render_ipo_analysis(ipo_df: pd.DataFrame, components: dict):
    """Render detailed IPO analysis page."""
    st.header("🔍 Detailed IPO Analysis")
    render_data_source_notice(ipo_df)
    
    # IPO selector
    ipo_options = {f"{row['company_name']} ({row['ipo_id']})": row['ipo_id'] 
                   for _, row in ipo_df.iterrows()}
    
    selected = st.selectbox("Select IPO", list(ipo_options.keys()))
    ipo_id = ipo_options[selected]
    
    # Analyze
    with st.spinner("Analyzing IPO..."):
        result = analyze_ipo(ipo_id, components)
    
    if not result:
        st.error("Failed to analyze IPO")
        return
    
    decision = result['decision']
    basic = result['basic_info']
    
    # Header section
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(basic['company_name'])
        st.write(f"**Sector:** {basic['sector']}")
        st.write(f"**Exchange:** {basic['listing_exchange']}")
        st.write(f"**Listing Date:** {basic['listing_date']}")
    
    with col2:
        st.write("**Price Band**")
        st.write(f"₹{basic['price_band_low']} - ₹{basic['price_band_high']}")
        st.write("**Lot Size**")
        st.write(f"{basic['lot_size']} shares")
    
    with col3:
        st.write("**Issue Size**")
        st.write(f"₹{basic['issue_size_cr']:.0f} Crores")
        st.write("**Issue Type**")
        st.write(basic['ipo_type'])
    
    st.markdown("---")
    
    # Recommendation section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_recommendation_card(decision)
        st.write("")
        render_risk_badge(decision['risk_analysis']['risk_level'])
    
    with col2:
        st.subheader("AI Confidence Scores")
        scores = decision['scores']
        fig = create_radar_chart(scores)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tabs for detailed analysis
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Fundamentals", "💬 Sentiment", "📈 Market", "🎯 ML Prediction", "📋 Strategy"
    ])
    
    with tab1:
        render_fundamentals_tab(result['fundamental_analysis'], result['fundamentals'])
    
    with tab2:
        render_sentiment_tab(result['sentiment_analysis'])
    
    with tab3:
        render_market_tab(result['market_analysis'], result['market'])
    
    with tab4:
        render_ml_tab(result['ml_prediction'])
    
    with tab5:
        render_strategy_tab(decision, result['subscription'], result['gmp'])


def render_fundamentals_tab(analysis: dict, raw: dict):
    """Render fundamentals analysis tab."""
    st.subheader("Fundamental Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = create_score_gauge(
            analysis['profitability_analysis']['composite_score'],
            "Profitability"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_score_gauge(
            analysis['growth_analysis']['composite_score'],
            "Growth"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = create_score_gauge(
            analysis['valuation_analysis']['composite_score'],
            "Valuation"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Key metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Profitability Metrics**")
        metrics_df = pd.DataFrame({
            'Metric': ['ROE', 'ROCE', 'EBITDA Margin', 'PAT Margin'],
            'Value': [
                f"{raw.get('roe', 0):.1f}%",
                f"{raw.get('roce', 0):.1f}%",
                f"{raw.get('ebitda_margin', 0):.1f}%",
                f"{raw.get('pat_margin', 0):.1f}%"
            ]
        })
        st.dataframe(metrics_df, hide_index=True)
    
    with col2:
        st.write("**Financial Health**")
        health_df = pd.DataFrame({
            'Metric': ['Debt/Equity', 'Current Ratio', 'P/E Ratio', 'EPS'],
            'Value': [
                f"{raw.get('debt_to_equity', 0):.2f}",
                f"{raw.get('current_ratio', 0):.2f}",
                f"{raw.get('pe_ratio', 0):.1f}x",
                f"₹{raw.get('eps', 0):.2f}"
            ]
        })
        st.dataframe(health_df, hide_index=True)
    
    # Insights
    st.write("**Key Insights**")
    for insight in analysis.get('key_insights', []):
        if insight.startswith('✓'):
            st.markdown(f'<div class="insight-positive">{insight}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="insight-negative">{insight}</div>', unsafe_allow_html=True)


def render_sentiment_tab(analysis: dict):
    """Render sentiment analysis tab."""
    st.subheader("Sentiment Analysis")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        fig = create_score_gauge(analysis['composite_score'], "Sentiment Score")
        st.plotly_chart(fig, use_container_width=True)
        
        st.metric("Sentiment", analysis['sentiment_label'].upper())
        st.metric("Trend", analysis.get('trend', 'N/A').title())
    
    with col2:
        # Sentiment distribution
        if analysis['article_count'] > 0:
            sentiment_data = {
                'Category': ['Positive', 'Negative', 'Neutral'],
                'Count': [
                    analysis['positive_count'],
                    analysis['negative_count'],
                    analysis['neutral_count']
                ]
            }
            
            fig = px.bar(
                sentiment_data,
                x='Category',
                y='Count',
                color='Category',
                color_discrete_map={
                    'Positive': '#28a745',
                    'Negative': '#dc3545',
                    'Neutral': '#6c757d'
                }
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No news articles available for sentiment analysis")
    
    # Key topics
    if analysis.get('key_topics'):
        st.write("**Key Topics Identified**")
        st.write(", ".join([f"#{topic}" for topic in analysis['key_topics']]))
    
    # Sample articles
    if analysis.get('articles_analyzed'):
        st.write("**Recent News Analyzed**")
        for article in analysis['articles_analyzed'][:3]:
            with st.expander(article['title']):
                st.write(f"**Source:** {article['source']}")
                st.write(f"**Date:** {article['date']}")
                st.write(f"**Sentiment:** {article['label'].title()} ({article['compound_score']:.2f})")


def render_market_tab(analysis: dict, raw: dict):
    """Render market analysis tab."""
    st.subheader("Market Conditions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Nifty 50",
            f"{raw.get('nifty_50_current', 0):,.0f}",
            delta=f"{raw.get('nifty_50_change_pct', 0):+.2f}%"
        )
    
    with col2:
        st.metric(
            "India VIX",
            f"{raw.get('india_vix', 0):.2f}",
            delta=analysis.get('volatility_analysis', {}).get('level', 'N/A')
        )
    
    with col3:
        st.metric(
            "Market Condition",
            analysis.get('market_condition', 'N/A')
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Market Trend**")
        trend = analysis.get('trend_analysis', {})
        
        trend_df = pd.DataFrame({
            'Period': ['Short Term', 'Medium Term', 'Long Term'],
            'Trend': [
                trend.get('short_term', {}).get('trend', 'N/A').title(),
                trend.get('medium_term', {}).get('trend', 'N/A').title(),
                trend.get('long_term', {}).get('trend', 'N/A').title()
            ],
            'Return': [
                f"{trend.get('short_term', {}).get('change', 0):+.2f}%",
                f"{trend.get('medium_term', {}).get('return_5d', 0):+.2f}%",
                f"{trend.get('long_term', {}).get('return_20d', 0):+.2f}%"
            ]
        })
        st.dataframe(trend_df, hide_index=True)
    
    with col2:
        st.write("**Institutional Flow**")
        flow = analysis.get('institutional_flow', {})
        
        flow_df = pd.DataFrame({
            'Category': ['FII', 'DII', 'Net'],
            'Investment (Cr)': [
                f"₹{flow.get('fii_net', 0):,.0f}",
                f"₹{flow.get('dii_net', 0):,.0f}",
                f"₹{flow.get('net_flow', 0):,.0f}"
            ]
        })
        st.dataframe(flow_df, hide_index=True)
    
    # IPO Timing
    timing = analysis.get('ipo_timing_assessment', {})
    st.write("**IPO Timing Assessment**")
    st.info(f"**{timing.get('timing', 'N/A')}**: {timing.get('recommendation', 'N/A')}")


def render_ml_tab(prediction: dict):
    """Render ML prediction tab."""
    st.subheader("Machine Learning Prediction")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("ML Prediction", prediction['prediction'])
        st.metric("Confidence", f"{prediction['confidence']:.1%}")
        st.metric("Strength", prediction['recommendation_strength'])
    
    with col2:
        # Probability distribution
        probs = prediction['probabilities']
        
        fig = px.bar(
            x=list(probs.keys()),
            y=[v * 100 for v in probs.values()],
            labels={'x': 'Category', 'y': 'Probability (%)'},
            color=list(probs.keys()),
            color_discrete_sequence=['#28a745', '#17a2b8', '#ffc107', '#dc3545']
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Feature importance
    st.write("**Top Features Influencing Prediction**")
    
    importance = prediction.get('feature_importance', [])[:10]
    if importance:
        imp_df = pd.DataFrame(importance)
        
        fig = px.bar(
            imp_df,
            x='importance',
            y='feature',
            orientation='h',
            labels={'importance': 'Importance', 'feature': 'Feature'},
            color='importance',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_strategy_tab(decision: dict, subscription: dict, gmp: dict):
    """Render trading strategy tab."""
    st.subheader("Trading Strategy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Subscription Data**")
        fig = create_subscription_chart(subscription)
        st.plotly_chart(fig, use_container_width=True)
        
        st.metric("Total Subscription", f"{subscription.get('total_subscription', 0):.1f}x")
        
    with col2:
        st.write("**GMP Analysis**")
        gmp_pct = gmp.get('gmp_percentage', 0)
        
        fig = go.Figure(go.Indicator(
            mode="number+delta",
            value=gmp_pct,
            delta={'reference': 0, 'relative': False},
            title={'text': "Grey Market Premium (%)"},
            number={'suffix': '%'}
        ))
        fig.update_layout(height=200)
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"**GMP Amount:** ₹{gmp.get('gmp_amount', 0)}")
        st.write(f"**Trend:** {gmp.get('gmp_trend', 'N/A').title()}")
        st.write(f"**Kostak Rate:** ₹{gmp.get('kostak_rate', 0)}")
    
    st.markdown("---")
    
    # Listing strategy
    strategy = decision.get('listing_day_strategy', {})
    
    st.write("**Listing Day Strategy**")
    st.info(f"**Expected Listing:** {strategy.get('expected_listing', 'N/A')}")
    st.info(f"**Expected Gain Range:** {strategy.get('expected_gain_range', 'N/A')}")
    
    st.write("**Recommended Actions**")
    for strat in strategy.get('strategies', []):
        with st.expander(f"📌 {strat['action']}"):
            st.write(f"**Reasoning:** {strat['reasoning']}")
            st.write(f"**Target:** {strat['target']}")
    
    # Risk factors
    st.markdown("---")
    st.write("**Risk Factors**")
    
    risk_factors = decision.get('risk_analysis', {}).get('risk_factors', [])
    if risk_factors:
        for factor in risk_factors:
            st.warning(f"⚠️ {factor}")
    else:
        st.success("✅ No major risk factors identified")
    
    # Mitigation
    mitigations = decision.get('risk_analysis', {}).get('mitigation_suggestions', [])
    if mitigations:
        st.write("**Risk Mitigation Suggestions**")
        for mitigation in mitigations:
            st.write(f"• {mitigation}")


def render_market_overview(components: dict):
    """Render market overview page."""
    st.header("📊 Market Overview")
    
    market_analyzer = components['market_analyzer']
    data_collector = components['data_collector']
    
    market_data = data_collector.collect_market_data()
    analysis = market_analyzer.analyze(market_data)
    if market_data.get('data_source') == 'nse_api':
        st.info("Market snapshot is live from NSE public market APIs.")
    else:
        st.warning("Live market feed is unavailable, so this view is using fallback sample market data.")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Nifty 50",
            f"{market_data.get('nifty_50_current', 0):,.0f}",
            delta=f"{market_data.get('nifty_50_change_pct', 0):+.2f}%"
        )
    
    with col2:
        st.metric(
            "India VIX",
            f"{market_data.get('india_vix', 0):.2f}",
            delta=analysis.get('volatility_analysis', {}).get('level', '')
        )
    
    with col3:
        fii = market_data.get('fii_net_investment', 0)
        st.metric(
            "FII Net",
            f"₹{fii:,.0f} Cr",
            delta="Buying" if fii > 0 else "Selling"
        )
    
    with col4:
        st.metric(
            "Market Sentiment",
            market_data.get('market_sentiment', 'N/A').title()
        )
    
    st.markdown("---")
    
    # Market score
    col1, col2 = st.columns(2)
    
    with col1:
        fig = create_score_gauge(analysis['composite_score'], "Market Score")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Market Condition")
        st.info(f"**{analysis['market_condition']}**")
        
        timing = analysis.get('ipo_timing_assessment', {})
        st.write(f"**IPO Timing:** {timing.get('timing', 'N/A')}")
        st.write(timing.get('recommendation', ''))
    
    # Sector performance
    st.markdown("---")
    st.subheader("Sector Performance")
    
    sector_perf = market_data.get('sector_performance', {})
    
    fig = px.bar(
        x=list(sector_perf.keys()),
        y=list(sector_perf.values()),
        labels={'x': 'Sector', 'y': 'Return (%)'},
        color=list(sector_perf.values()),
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_model_insights(components: dict):
    """Render model insights page."""
    st.header("🤖 Model Insights")
    
    ml_predictor = components['ml_predictor']
    
    st.subheader("Ensemble Model Architecture")
    
    st.write("""
    The platform uses an ensemble of three machine learning models to generate predictions:
    
    1. **Random Forest Classifier** - Robust tree-based ensemble method
    2. **Gradient Boosting Classifier** - Sequential boosting for improved accuracy
    3. **Logistic Regression** - Interpretable linear model
    
    Final predictions are made through weighted majority voting with confidence aggregation.
    """)
    
    # Model configuration
    st.subheader("Model Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Random Forest**")
        st.json({
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5
        })
    
    with col2:
        st.write("**Gradient Boosting**")
        st.json({
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1
        })
    
    with col3:
        st.write("**Logistic Regression**")
        st.json({
            "C": 1.0,
            "max_iter": 1000,
            "multi_class": "multinomial"
        })
    
    st.markdown("---")
    
    # Feature engineering
    st.subheader("Feature Categories")
    
    features = {
        "Fundamental Features": [
            "ROE", "ROCE", "EBITDA Margin", "PAT Margin",
            "Debt/Equity", "Current Ratio", "P/E Ratio",
            "Revenue Growth", "PAT Growth", "Promoter Holding"
        ],
        "Subscription Features": [
            "QIB Subscription", "NII Subscription",
            "Retail Subscription", "Total Subscription", "Anchor Subscribed"
        ],
        "GMP Features": [
            "GMP Percentage", "GMP Trend Score"
        ],
        "Market Features": [
            "Nifty Change", "5-Day Return", "India VIX",
            "FII Net", "Market Sentiment Score"
        ],
        "Other Features": [
            "Sentiment Score", "Issue Size", "Lot Size"
        ]
    }
    
    for category, feature_list in features.items():
        with st.expander(category):
            st.write(", ".join(feature_list))
    
    st.markdown("---")
    
    # Decision thresholds
    st.subheader("Decision Thresholds")
    
    thresholds_df = pd.DataFrame({
        'Decision': ['Strong Apply', 'Apply', 'Hold', 'Avoid', 'Strong Avoid'],
        'Score Range': ['≥ 0.75', '0.60 - 0.75', '0.45 - 0.60', '0.30 - 0.45', '< 0.30'],
        'Description': [
            'Highly recommended investment',
            'Recommended with good risk-reward',
            'Wait for more clarity',
            'Not recommended at current levels',
            'Strong sell / Do not invest'
        ]
    })
    
    st.dataframe(thresholds_df, hide_index=True, use_container_width=True)


def render_about():
    """Render about page."""
    st.header("ℹ️ About the Platform")
    
    st.write("""
    ## AI-Driven IPO Intelligence Platform for Risk-Aware Trading
    
    ### Overview
    This platform provides comprehensive AI-powered analysis for IPO investments,
    focusing on risk-aware decision making rather than blind profit prediction.
    
    ### Key Features
    
    - **Multi-dimensional Analysis**: Combines fundamental, sentiment, and market analysis
    - **Machine Learning Predictions**: Ensemble of Random Forest, Gradient Boosting, and Logistic Regression
    - **Risk Assessment**: Comprehensive risk scoring and categorization
    - **Trading Strategies**: Pre-listing recommendations and listing day strategies
    - **Real-time Updates**: Market data integration and dynamic analysis
    
    ### Technology Stack
    
    - **Backend**: Python, Pandas, NumPy, Scikit-learn
    - **NLP**: NLTK, VADER Sentiment Analysis
    - **Frontend**: Streamlit
    - **Visualization**: Plotly
    - **Database**: SQLite
    
    ### Decision Framework
    
    The platform generates recommendations based on a weighted composite score:
    - Fundamental Score (30%)
    - Sentiment Score (20%)
    - Market Condition Score (20%)
    - Subscription Score (15%)
    - GMP Score (15%)
    
    ### Disclaimer
    
    ⚠️ This platform is for educational and informational purposes only.
    Investment decisions should be made after consulting with financial advisors.
    Past performance does not guarantee future results.
    """)
    
    st.markdown("---")
    
    st.write("**Version:** 1.0.0")
    st.write("**Last Updated:** January 2026")


if __name__ == "__main__":
    main()
