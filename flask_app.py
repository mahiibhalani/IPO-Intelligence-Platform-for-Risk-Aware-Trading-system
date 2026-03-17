"""
AI-Driven IPO Intelligence Platform - Flask Web Application
==========================================================
Interactive web dashboard for IPO analysis and trading recommendations.
"""

from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import numpy as np
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.ipo_data_collector import IPODataCollector
from src.data.fundamental_analyzer import FundamentalAnalyzer
from src.intelligence.sentiment_analyzer import SentimentAnalyzer
from src.intelligence.market_analyzer import MarketAnalyzer
from src.intelligence.ml_predictor import IPOPredictionModel
from src.decision.decision_engine import DecisionEngine

app = Flask(__name__)
app.secret_key = 'ipo-intelligence-platform-secret-key'

# Global components cache
components_cache = None

def get_components():
    """Get cached components or initialize them."""
    global components_cache
    if components_cache is None:
        components_cache = {
            'data_collector': IPODataCollector(),
            'fundamental_analyzer': FundamentalAnalyzer(),
            'sentiment_analyzer': SentimentAnalyzer(),
            'market_analyzer': MarketAnalyzer(),
            'ml_predictor': IPOPredictionModel(),
            'decision_engine': DecisionEngine()
        }
        # Train ML model
        components_cache['ml_predictor'].train()
    return components_cache

def get_ipo_data():
    """Get IPO data."""
    components = get_components()
    return components['data_collector'].collect_ipo_listings()

def analyze_ipo(ipo_id: str):
    """Run complete analysis for an IPO."""
    components = get_components()
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

def create_score_gauge(score: float, title: str):
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
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_radar_chart(scores: dict):
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
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_subscription_chart(subscription: dict):
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
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def dashboard():
    """Main dashboard page."""
    ipo_df = get_ipo_data()
    components = get_components()

    # Create summary for each IPO
    summaries = []
    for _, ipo in ipo_df.iterrows():
        result = analyze_ipo(ipo['ipo_id'])
        if result:
            decision = result['decision']
            summaries.append({
                'company': ipo['company_name'],
                'sector': ipo['sector'],
                'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'gmp': f"{result['gmp']['gmp_percentage']:.1f}%",
                'subscription': f"{result['subscription']['total_subscription']:.1f}x",
                'score': f"{decision['composite_score']:.2f}",
                'risk': decision['risk_analysis']['risk_level'],
                'recommendation': decision['pre_listing_recommendation']['decision']
            })

    # Charts data
    scores = [float(s['score']) for s in summaries]
    score_chart = json.dumps(px.histogram(x=scores, nbins=10).to_dict(), cls=plotly.utils.PlotlyJSONEncoder)

    sector_counts = pd.Series([s['sector'] for s in summaries]).value_counts()
    sector_chart = json.dumps(px.pie(values=sector_counts.values, names=sector_counts.index).to_dict(), cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('dashboard.html',
                         summaries=summaries,
                         score_chart=score_chart,
                         sector_chart=sector_chart,
                         total_ipos=len(ipo_df),
                         upcoming=len(ipo_df[ipo_df['listing_date'] > datetime.now().strftime('%Y-%m-%d')]),
                         avg_size=ipo_df['issue_size_cr'].mean())

@app.route('/ipo-analysis', methods=['GET', 'POST'])
def ipo_analysis():
    """IPO analysis page."""
    ipo_df = get_ipo_data()

    if request.method == 'POST':
        ipo_id = request.form.get('ipo_id')
        result = analyze_ipo(ipo_id)

        if result:
            decision = result['decision']
            basic = result['basic_info']

            # Create charts
            scores = decision['scores']
            radar_chart = create_radar_chart(scores)

            return render_template('ipo_analysis.html',
                                 ipo_df=ipo_df,
                                 result=result,
                                 decision=decision,
                                 basic=basic,
                                 radar_chart=radar_chart,
                                 selected_ipo=ipo_id)
        else:
            return render_template('ipo_analysis.html', ipo_df=ipo_df, error="Failed to analyze IPO")

    return render_template('ipo_analysis.html', ipo_df=ipo_df)

@app.route('/market-overview')
def market_overview():
    """Market overview page."""
    components = get_components()
    market_analyzer = components['market_analyzer']
    data_collector = components['data_collector']

    market_data = data_collector.collect_market_data()
    analysis = market_analyzer.analyze(market_data)

    # Market score gauge
    market_score_chart = create_score_gauge(analysis['composite_score'], "Market Score")

    # Sector performance chart
    sector_perf = market_data.get('sector_performance', {})
    sector_chart = json.dumps(px.bar(
        x=list(sector_perf.keys()),
        y=list(sector_perf.values()),
        labels={'x': 'Sector', 'y': 'Return (%)'},
        color=list(sector_perf.values()),
        color_continuous_scale='RdYlGn'
    ).to_dict(), cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('market_overview.html',
                         market_data=market_data,
                         analysis=analysis,
                         market_score_chart=market_score_chart,
                         sector_chart=sector_chart)

@app.route('/model-insights')
def model_insights():
    """Model insights page."""
    return render_template('model_insights.html')

@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@app.route('/api/refresh-data')
def refresh_data():
    """API endpoint to refresh data."""
    components = get_components()
    components['data_collector'].clear_cache()
    return jsonify({'status': 'success', 'message': 'Data cache cleared'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)