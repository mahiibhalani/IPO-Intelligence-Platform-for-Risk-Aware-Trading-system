"""
AI-Driven IPO Intelligence Platform - Flask Web Application
==========================================================
Interactive web dashboard for IPO analysis and trading recommendations.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import current_user
import pandas as pd
import numpy as np
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import json
import logging
import os
from pathlib import Path
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.ipo_data_collector import IPODataCollector
from src.data.fundamental_analyzer import FundamentalAnalyzer
from src.intelligence.sentiment_analyzer import SentimentAnalyzer
from src.intelligence.market_analyzer import MarketAnalyzer
from src.intelligence.ml_predictor import IPOPredictionModel
from src.decision.decision_engine import DecisionEngine
from src.models import db, User, SavedIPO, AppliedIPO, Watchlist, UserPreferences
from src.auth import auth_bp, init_login_manager
from src.user_api import user_api_bp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'ipo-intelligence-platform-secret-key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ipo_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = init_login_manager(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_api_bp)

def ensure_saved_ipos_columns():
    """Add any missing columns in the saved_ipos table for compatibility with older SQLite files."""
    engine = db.engine
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(saved_ipos)"))
        existing = {row[1] for row in result.fetchall()}

        columns = {
            'price_band': 'TEXT',
            'issue_size': 'REAL',
            'lot_size': 'TEXT',
            'subscription': 'TEXT',
            'gmp': 'TEXT',
            'ai_score': 'REAL',
            'recommendation': 'TEXT',
            'risk_level': 'TEXT',
            'status': 'TEXT',
            'open_date': 'TEXT',
            'close_date': 'TEXT',
            'saved_at': 'DATETIME',
            'notes': 'TEXT'
        }

        for column, column_type in columns.items():
            if column not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE saved_ipos ADD COLUMN {column} {column_type}"))
                    logger.info(f"Added missing column '{column}' to saved_ipos")
                except Exception as exc:
                    logger.warning(f"Could not add saved_ipos column '{column}': {exc}")

# Create database tables
with app.app_context():
    db.create_all()
    ensure_saved_ipos_columns()
    logger.info("Database initialized")
    
    # Create test user if doesn't exist
    try:
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User'
            )
            test_user.set_password('Test@1234')
            db.session.add(test_user)
            db.session.flush()
            
            # Create preferences for test user
            prefs = UserPreferences(user_id=test_user.id)
            db.session.add(prefs)
            db.session.commit()
            logger.info("Test user created: testuser/Test@1234")
    except Exception as e:
        logger.error(f"Error creating test user: {e}")
        db.session.rollback()

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
    return components_cache

def get_ipo_data():
    """Get IPO data."""
    components = get_components()
    return components['data_collector'].collect_ipo_listings()


def get_heatmap_ipo_data():
    """Get IPO data for the heatmap, padding with sample rows if needed."""
    components = get_components()
    ipo_df = components['data_collector'].collect_ipo_listings()

    if ipo_df is None or ipo_df.empty:
        ipo_df = components['data_collector']._generate_sample_ipo_data()

    if ipo_df is not None and len(ipo_df) < 8:
        sample_df = components['data_collector']._generate_sample_ipo_data()
        if sample_df is not None and not sample_df.empty:
            ipo_df = pd.concat([ipo_df, sample_df], ignore_index=True, sort=False)
            ipo_df = ipo_df.drop_duplicates(subset=['ipo_id', 'company_name']).reset_index(drop=True)

    return ipo_df

def normalize_ipo_status(raw_status):
    """Normalize IPO status string for UI filtering and display."""
    status = str(raw_status or '').strip().lower()
    if status in ['live', 'active', 'open', 'listing now']:
        return 'Live'
    if status in ['upcoming', 'pending', 'coming soon', 'scheduled']:
        return 'Upcoming'
    if status in ['closed', 'completed', 'finished', 'delisted']:
        return 'Closed'
    return 'Upcoming'


def parse_numeric_value(value):
    """Parse a numeric value from mixed types and return a float or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    try:
        text = str(value).strip().replace(',', '').replace('%', '').replace('₹', '').replace('+', '')
        if text == '':
            return None
        return float(text)
    except Exception:
        return None

def format_date_label(date_str: str):
    if not date_str or date_str in ['TBD', 'Unknown', '']:
        return 'TBD'
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %b %Y')
    except Exception:
        return date_str


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
        try:
            result = analyze_ipo(ipo['ipo_id'])
            if result:
                decision = result['decision']
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': f"{result['gmp']['gmp_percentage']:.1f}%",
                    'subscription': f"{result['subscription']['total_subscription']:.1f}x",
                    'score': f"{decision['composite_score']:.2f}",
                    'risk': decision['risk_analysis']['risk_level'],
                    'recommendation': decision['pre_listing_recommendation']['decision'],
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
            else:
                # Fallback for IPOs that can't be analyzed
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': 'N/A',
                    'subscription': 'N/A',
                    'score': '5.00',
                    'risk': 'Medium',
                    'recommendation': 'Apply',
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
        except Exception as e:
            logger.error(f"Error analyzing IPO {ipo['ipo_id']}: {e}")
            # Still add the IPO with default values
            summaries.append({
                'ipo_id': ipo['ipo_id'],
                'company': ipo['company_name'],
                'sector': ipo['sector'],
                'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'gmp': 'N/A',
                'subscription': 'N/A',
                'score': '5.00',
                'risk': 'Medium',
                'recommendation': 'Apply',
                'status': ipo.get('status', 'Upcoming'),
                'lot_size': ipo.get('lot_size', 'N/A'),
                'open_date': ipo.get('issue_open_date', 'TBD'),
                'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
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

@app.route('/upcoming')
def upcoming():
    """Upcoming IPOs page."""
    ipo_df = get_ipo_data()
    components = get_components()
    
    # Filter for upcoming IPOs only
    today = datetime.now().strftime('%Y-%m-%d')
    upcoming_df = ipo_df[ipo_df['listing_date'] > today]
    upcoming_df = upcoming_df.sort_values('listing_date', ascending=True)
    
    # Create summary for each upcoming IPO
    summaries = []
    for _, ipo in upcoming_df.iterrows():
        try:
            result = analyze_ipo(ipo['ipo_id'])
            if result:
                decision = result['decision']
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': f"{result['gmp']['gmp_percentage']:.1f}%",
                    'subscription': f"{result['subscription']['total_subscription']:.1f}x",
                    'score': f"{decision['composite_score']:.2f}",
                    'risk': decision['risk_analysis']['risk_level'],
                    'recommendation': decision['pre_listing_recommendation']['decision'],
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
            else:
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': 'N/A',
                    'subscription': 'N/A',
                    'score': '5.00',
                    'risk': 'Medium',
                    'recommendation': 'Apply',
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
        except Exception as e:
            logger.error(f"Error analyzing upcoming IPO {ipo['ipo_id']}: {e}")
            summaries.append({
                'ipo_id': ipo['ipo_id'],
                'company': ipo['company_name'],
                'sector': ipo['sector'],
                'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'gmp': 'N/A',
                'subscription': 'N/A',
                'score': '5.00',
                'risk': 'Medium',
                'recommendation': 'Apply',
                'status': ipo.get('status', 'Upcoming'),
                'lot_size': ipo.get('lot_size', 'N/A'),
                'open_date': ipo.get('issue_open_date', 'TBD'),
                'close_date': ipo.get('issue_close_date', 'TBD'),
                'listing_date': ipo.get('listing_date', 'TBD')
            })
    
    # Build calendar events from IPO open/close/listing dates
    calendar_events = []
    def add_calendar_event(date_value, description, event_type='IPO', ipo_id=None):
        if date_value and date_value != 'TBD':
            event = {
                'date': date_value,
                'description': description,
                'type': event_type
            }
            if ipo_id:
                event['ipo_id'] = ipo_id
            calendar_events.append(event)

    for s in summaries:
        if s['open_date'] != 'TBD':
            add_calendar_event(
                s['open_date'],
                f"{s['company']} IPO Opens on {datetime.strptime(s['open_date'], '%Y-%m-%d').strftime('%b %d, %Y')}",
                event_type='IPO',
                ipo_id=s['ipo_id']
            )
        if s['close_date'] != 'TBD':
            add_calendar_event(
                s['close_date'],
                f"{s['company']} IPO Closes on {datetime.strptime(s['close_date'], '%Y-%m-%d').strftime('%b %d, %Y')}",
                event_type='IPO',
                ipo_id=s['ipo_id']
            )
        if s['listing_date'] != 'TBD' and s['listing_date'] not in [s['open_date'], s['close_date']]:
            add_calendar_event(
                s['listing_date'],
                f"{s['company']} IPO Lists on {datetime.strptime(s['listing_date'], '%Y-%m-%d').strftime('%b %d, %Y')}",
                event_type='IPO',
                ipo_id=s['ipo_id']
            )

    # Add public holidays for the displayed year
    holiday_events = [
        {'date': '2026-01-01', 'description': 'New Year’s Day', 'type': 'Holiday'},
        {'date': '2026-01-14', 'description': 'Makar Sankranti / Pongal', 'type': 'Holiday'},
        {'date': '2026-01-26', 'description': 'Republic Day', 'type': 'Holiday'},
        {'date': '2026-02-17', 'description': 'Maha Shivratri', 'type': 'Holiday'},
        {'date': '2026-03-25', 'description': 'Good Friday', 'type': 'Holiday'},
        {'date': '2026-04-14', 'description': 'Dr. Babasaheb Ambedkar Jayanti', 'type': 'Holiday'},
        {'date': '2026-04-21', 'description': 'Eid al-Fitr', 'type': 'Holiday'},
        {'date': '2026-05-01', 'description': 'Labour Day', 'type': 'Holiday'},
        {'date': '2026-06-16', 'description': 'Bakrid / Eid al-Adha', 'type': 'Holiday'},
        {'date': '2026-07-17', 'description': 'Muharram', 'type': 'Holiday'},
        {'date': '2026-08-15', 'description': 'Independence Day', 'type': 'Holiday'},
        {'date': '2026-09-02', 'description': 'Ganesh Chaturthi', 'type': 'Holiday'},
        {'date': '2026-10-02', 'description': 'Gandhi Jayanti', 'type': 'Holiday'},
        {'date': '2026-10-13', 'description': 'Dussehra', 'type': 'Holiday'},
        {'date': '2026-10-31', 'description': 'Diwali / Deepavali', 'type': 'Holiday'},
        {'date': '2026-11-11', 'description': 'Guru Nanak Jayanti', 'type': 'Holiday'},
        {'date': '2026-12-25', 'description': 'Christmas Day', 'type': 'Holiday'}
    ]
    calendar_events.extend(holiday_events)

    # Create charts
    scores = [float(s['score']) for s in summaries] if summaries else [5.0]
    score_chart = json.dumps(px.histogram(x=scores, nbins=10).to_dict(), cls=plotly.utils.PlotlyJSONEncoder)
    
    sector_counts = pd.Series([s['sector'] for s in summaries]).value_counts() if summaries else pd.Series()
    sector_chart = json.dumps(px.pie(values=sector_counts.values, names=sector_counts.index).to_dict() if not sector_counts.empty else {}, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('upcoming.html',
                         summaries=summaries,
                         score_chart=score_chart,
                         sector_chart=sector_chart,
                         calendar_events=calendar_events,
                         total_ipos=len(upcoming_df),
                         avg_size=upcoming_df['issue_size_cr'].mean() if len(upcoming_df) > 0 else 0)

@app.route('/mainboard')
def mainboard():
    """Mainboard IPOs page - shows all IPOs."""
    return dashboard()

@app.route('/sme')
def sme():
    """SME IPOs page."""
    ipo_df = get_ipo_data()
    components = get_components()

    # Filter for SME IPOs (NSE SME listings or series marked SME)
    sme_df = ipo_df[ipo_df['listing_exchange'].str.contains('SME', case=False, na=False) | ipo_df['series'].str.contains('SME', case=False, na=False)]
    sme_df = sme_df.sort_values('listing_date', ascending=True)

    # If the live source doesn't expose SME listings, fall back to cached/sample data
    if sme_df.empty:
        cached = components['data_collector']._load_cached_ipo_data()
        if cached is not None and not cached.empty:
            ipo_df = cached
            sme_df = ipo_df[ipo_df['listing_exchange'].str.contains('SME', case=False, na=False) | ipo_df['series'].str.contains('SME', case=False, na=False)]
            sme_df = sme_df.sort_values('listing_date', ascending=True)

    # Provide a small KPI for live GMP tracking
    live_df = sme_df[sme_df['status'].str.contains('Active|Live', case=False, na=False)]

    # Create summary for each SME IPO
    summaries = []
    for _, ipo in sme_df.iterrows():
        try:
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
                    'recommendation': decision['pre_listing_recommendation']['decision'],
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
            else:
                summaries.append({
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': 'N/A',
                    'subscription': 'N/A',
                    'score': '5.00',
                    'risk': 'Medium',
                    'recommendation': 'Apply',
                    'status': ipo.get('status', 'Upcoming'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
        except Exception as e:
            logger.error(f"Error analyzing SME IPO {ipo['ipo_id']}: {e}")
            summaries.append({
                'company': ipo['company_name'],
                'sector': ipo['sector'],
                'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'gmp': 'N/A',
                'subscription': 'N/A',
                'score': '5.00',
                'risk': 'Medium',
                'recommendation': 'Apply',
                'status': ipo.get('status', 'Upcoming'),
                'lot_size': ipo.get('lot_size', 'N/A'),
                'open_date': ipo.get('issue_open_date', 'TBD'),
                'close_date': ipo.get('issue_close_date', 'TBD'),
                'listing_date': ipo.get('listing_date', 'TBD')
            })

    # Create charts
    # Extract numeric scores only
    scores = []
    for s in summaries:
        try:
            score_val = float(s['score']) if isinstance(s['score'], str) else s['score']
            scores.append(score_val)
        except (ValueError, TypeError):
            scores.append(5.0)  # Default to 5.0 if conversion fails
    
    # Build score distribution histogram
    if scores:
        score_buckets = {'0–2': 0, '2–4': 0, '4–6': 0, '6–8': 0, '8–10': 0}
        for score in scores:
            if score < 2:
                score_buckets['0–2'] += 1
            elif score < 4:
                score_buckets['2–4'] += 1
            elif score < 6:
                score_buckets['4–6'] += 1
            elif score < 8:
                score_buckets['6–8'] += 1
            else:
                score_buckets['8–10'] += 1
        
        bucket_labels = list(score_buckets.keys())
        bucket_values = list(score_buckets.values())
        bucket_colors = ['#ff6b6b', '#fa709a', '#ffd700', '#43e97b', '#00ff88']
        
        score_chart_data = [{
            'type': 'bar',
            'x': bucket_labels,
            'y': bucket_values,
            'marker': {
                'color': bucket_colors,
                'opacity': 0.9,
                'line': {'color': 'rgba(0,0,0,0.3)', 'width': 1.5}
            },
            'text': [f'{v} IPO{"s" if v != 1 else ""}' if v > 0 else '' for v in bucket_values],
            'textposition': 'outside',
            'textfont': {'color': '#e0e0e0', 'size': 12},
            'hovertemplate': '<b>Score %{x}</b><br>%{y} IPO(s)<extra></extra>'
        }]
        score_chart_layout = {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(255,255,255,0.03)',
            'font': {'color': '#e0e0e0', 'family': 'Segoe UI, sans-serif'},
            'xaxis': {
                'title': {'text': 'AI Score Range', 'font': {'color': '#aaa', 'size': 12}},
                'gridcolor': '#2a2a4a',
                'zerolinecolor': '#444',
                'tickfont': {'color': '#e0e0e0', 'size': 12}
            },
            'yaxis': {
                'title': {'text': 'Number of IPOs', 'font': {'color': '#aaa', 'size': 12}},
                'gridcolor': '#2a2a4a',
                'zerolinecolor': '#444',
                'dtick': 1,
                'rangemode': 'tozero'
            },
            'margin': {'t': 30, 'b': 55, 'l': 50, 'r': 20}
        }
        score_chart = json.dumps({'data': score_chart_data, 'layout': score_chart_layout}, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        score_chart = json.dumps({'data': [], 'layout': {}}, cls=plotly.utils.PlotlyJSONEncoder)

    # Build sector breakdown pie chart
    sector_counts = pd.Series([s['sector'] for s in summaries]).value_counts() if summaries else pd.Series()
    if not sector_counts.empty:
        sector_colors = [
            '#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a',
            '#fee140', '#a18cd1', '#ffecd2', '#96fbc4', '#f6d365'
        ]
        sector_chart_data = [{
            'type': 'pie',
            'hole': 0.55,
            'values': sector_counts.values.tolist(),
            'labels': sector_counts.index.tolist(),
            'marker': {
                'colors': sector_colors[:len(sector_counts)],
                'line': {'color': 'rgba(0,0,0,0.3)', 'width': 1.5}
            },
            'textposition': 'inside',
            'textfont': {'color': '#fff', 'size': 12},
            'hovertemplate': '<b>%{label}</b><br>%{value} IPO(s)<extra></extra>'
        }]
        sector_chart_layout = {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': '#e0e0e0', 'family': 'Segoe UI, sans-serif'},
            'showlegend': True,
            'legend': {'x': 1, 'y': 0.5, 'font': {'color': '#e0e0e0'}},
            'margin': {'t': 20, 'b': 20, 'l': 20, 'r': 100}
        }
        sector_chart = json.dumps({'data': sector_chart_data, 'layout': sector_chart_layout}, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        sector_chart = json.dumps({'data': [], 'layout': {}}, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('sme.html',
                         summaries=summaries,
                         score_chart=score_chart,
                         sector_chart=sector_chart,
                         total_ipos=len(sme_df),
                         avg_size=sme_df['issue_size_cr'].mean() if len(sme_df) > 0 else 0,
                         live_count=len(live_df))

@app.route('/live')
def live():
    """Live IPOs page - shows IPOs currently in trading."""
    ipo_df = get_ipo_data()
    components = get_components()
    
    # Filter for live IPOs
    today = datetime.now().strftime('%Y-%m-%d')
    live_df = ipo_df[ipo_df['status'].str.contains('Active|Live', case=False, na=False)]
    live_df = live_df.sort_values('listing_date', ascending=False)
    
    # Create summary for each live IPO
    summaries = []
    for _, ipo in live_df.iterrows():
        try:
            result = analyze_ipo(ipo['ipo_id'])
            if result:
                decision = result['decision']
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': f"{result['gmp']['gmp_percentage']:.1f}%",
                    'subscription': f"{result['subscription']['total_subscription']:.1f}x",
                    'score': f"{decision['composite_score']:.2f}",
                    'risk': decision['risk_analysis']['risk_level'],
                    'recommendation': decision['pre_listing_recommendation']['decision'],
                    'status': ipo.get('status', 'Live'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
            else:
                summaries.append({
                    'ipo_id': ipo['ipo_id'],
                    'company': ipo['company_name'],
                    'sector': ipo['sector'],
                    'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                    'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                    'gmp': 'N/A',
                    'subscription': 'N/A',
                    'score': '5.00',
                    'risk': 'Medium',
                    'recommendation': 'Apply',
                    'status': ipo.get('status', 'Live'),
                    'lot_size': ipo.get('lot_size', 'N/A'),
                    'open_date': ipo.get('issue_open_date', 'TBD'),
                    'close_date': ipo.get('issue_close_date', 'TBD'),
                    'listing_date': ipo.get('listing_date', 'TBD')
                })
        except Exception as e:
            logger.error(f"Error analyzing live IPO {ipo['ipo_id']}: {e}")
            summaries.append({
                'ipo_id': ipo['ipo_id'],
                'company': ipo['company_name'],
                'sector': ipo['sector'],
                'price_band': f"₹{ipo['price_band_low']}-{ipo['price_band_high']}",
                'issue_size': f"₹{ipo['issue_size_cr']:.0f}Cr",
                'gmp': 'N/A',
                'subscription': 'N/A',
                'score': '5.00',
                'risk': 'Medium',
                'recommendation': 'Apply',
                'status': ipo.get('status', 'Live'),
                'lot_size': ipo.get('lot_size', 'N/A'),
                'open_date': ipo.get('issue_open_date', 'TBD'),
                'close_date': ipo.get('issue_close_date', 'TBD'),
                'listing_date': ipo.get('listing_date', 'TBD')
            })
    
    scores = [float(s['score']) for s in summaries] if summaries else [5.0]
    score_chart = json.dumps(px.histogram(x=scores, nbins=10).to_dict(), cls=plotly.utils.PlotlyJSONEncoder)
    
    sector_counts = pd.Series([s['sector'] for s in summaries]).value_counts() if summaries else pd.Series()
    sector_chart = json.dumps(px.pie(values=sector_counts.values, names=sector_counts.index).to_dict() if not sector_counts.empty else {}, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('live.html',
                         summaries=summaries,
                         score_chart=score_chart,
                         sector_chart=sector_chart,
                         total_ipos=len(live_df),
                         avg_size=live_df['issue_size_cr'].mean() if len(live_df) > 0 else 0)

@app.route('/heatmap')
def heatmap():
    """IPO Heatmap page - sector and performance overview."""
    ipo_df = get_heatmap_ipo_data()
    
    # Transform DataFrame to list of dicts for template
    ipo_data = []
    categories = set()
    sectors = set()
    months = set()
    statuses = set()
    performance_options = set()

    for _, row in ipo_df.iterrows():
        # Create abbreviation from company name
        abbr = ''.join(word[0] for word in str(row.get('company_name', '')).split()[:3]).upper() or 'IPO'

        # Normalize status
        status = normalize_ipo_status(row.get('status', 'Upcoming'))

        if status == 'Live':
            color = 'gold'
        elif status == 'Upcoming':
            color = 'deepskyblue'
        elif status == 'Closed':
            color = 'gray'
        elif status == 'Allotted':
            color = 'gold'
        else:
            color = 'lightsalmon'

        sector = row.get('sector', 'Others') or 'Others'
        listing_exchange = str(row.get('listing_exchange', '') or '')
        series = str(row.get('series', '') or '')
        category = 'SME' if 'SME' in listing_exchange.upper() or 'SME' in series.upper() else 'Mainboard'

        month_source = row.get('issue_open_date') or row.get('listing_date') or row.get('issue_close_date')
        month = 'Unknown Month'
        if pd.notna(month_source) and str(month_source).strip():
            try:
                month = datetime.strptime(str(month_source), '%Y-%m-%d').strftime('%B %Y')
            except Exception:
                month = str(month_source)

        gmp_value = parse_numeric_value(row.get('gmp'))

        perf = 'N/A'
        performance = 'Neutral'
        live_subscription = parse_numeric_value(row.get('live_total_subscription'))
        if live_subscription is not None and live_subscription != 0:
            perf = f"{live_subscription:+.2f}%"
            performance = 'Positive' if live_subscription > 0 else 'Negative'
        elif gmp_value is not None:
            perf = f"{gmp_value:+.2f}"
            performance = 'Positive' if gmp_value > 0 else ('Negative' if gmp_value < 0 else 'Neutral')

        if perf == 'N/A':
            performance = 'Neutral'

        price = 'N/A'

        price = 'N/A'
        if pd.notna(row.get('price_band_low')) and pd.notna(row.get('price_band_high')):
            try:
                price = f"₹{int(row['price_band_low'])}-{int(row['price_band_high'])}"
            except Exception:
                price = f"₹{row['price_band_low']}-{row['price_band_high']}"

        size = 'N/A'
        if pd.notna(row.get('issue_size_cr')):
            size = f"₹{row['issue_size_cr']}Cr"

        sub = 'N/A'
        if live_subscription is not None and live_subscription > 0:
            sub = f"{live_subscription}x"

        score = row.get('score', 'N/A')
        if pd.isna(score):
            score = 'N/A'

        ipo_data.append({
            'name': row.get('company_name', 'Unknown IPO'),
            'abbr': abbr,
            'status': status,
            'perf': perf,
            'sector': sector,
            'category': category,
            'month': month,
            'performance': performance,
            'color': color,
            'gmp': row.get('gmp', 'N/A'),
            'score': score,
            'price': price,
            'size': size,
            'sub': sub
        })

        categories.add(category)
        sectors.add(sector)
        months.add(month)
        statuses.add(status)
        performance_options.add(performance)

    return render_template(
        'heatmap.html',
        ipo_data=ipo_data,
        total_ipos=len(ipo_data),
        categories=sorted(categories),
        sectors=sorted(sectors),
        months=sorted(months),
        statuses=sorted(statuses),
        performance_options=sorted(performance_options)
    )

@app.route('/news')
def news():
    """IPO News page - latest IPO news and updates."""
    try:
        components = get_components()
        news_items = components['data_collector'].collect_ipo_news(limit=20)
        return render_template('news.html', news_items=news_items)
    except Exception as e:
        logger.error(f"Error loading news: {e}")
        # Fallback to empty news list
        return render_template('news.html', news_items=[])

@app.route('/news/<news_id>')
def news_detail(news_id):
    """Detailed view of a single news item."""
    try:
        components = get_components()
        news_items = components['data_collector'].collect_ipo_news(limit=50)
        news_item = next((n for n in news_items if n.get('id') == news_id), None)
        if not news_item:
            return render_template('news_detail.html', not_found=True, news_id=news_id)
        return render_template('news_detail.html', news_item=news_item)
    except Exception as e:
        logger.error(f"Error loading news details for {news_id}: {e}")
        return render_template('news_detail.html', not_found=True, news_id=news_id)

@app.route('/api/load-more-news', methods=['GET'])
def load_more_news():
    """API endpoint to load more news items."""
    try:
        components = get_components()
        limit = request.args.get('limit', 20, type=int)
        news_items = components['data_collector'].collect_ipo_news(limit=limit)
        
        # Return news items as JSON
        return jsonify({
            'status': 'success',
            'news_items': news_items if news_items else []
        })
    except Exception as e:
        logger.error(f"Error loading more news: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'news_items': []
        }), 500

@app.route('/ipo-analysis', methods=['GET', 'POST'])
def ipo_analysis():
    """IPO analysis page."""
    ipo_df = get_ipo_data()

    # Support both GET (?ipo_id=xxx) and POST form submissions
    ipo_id = None
    if request.method == 'POST':
        ipo_id = request.form.get('ipo_id')
    elif request.method == 'GET':
        ipo_id = request.args.get('ipo_id')

    if ipo_id:
        result = analyze_ipo(ipo_id)

        if result:
            decision = result['decision']
            basic = result['basic_info']

            # Create timeline labels from the same issuer dates shown in calendar events
            timeline_dates = {
                'open_date': format_date_label(basic.get('issue_open_date') or basic.get('open_date')),
                'close_date': format_date_label(basic.get('issue_close_date') or basic.get('close_date')),
                'allotment_date': format_date_label(basic.get('allotment_date')),
                'listing_date': format_date_label(basic.get('listing_date') or basic.get('list_date'))
            }

            # Create charts
            scores = decision['scores']
            radar_chart = create_radar_chart(scores)

            return render_template('ipo_analysis.html',
                                 ipo_df=ipo_df,
                                 result=result,
                                 decision=decision,
                                 basic=basic,
                                 timeline_dates=timeline_dates,
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