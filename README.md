# 🚀 IPO Intelligence Platform for Risk-Aware Trading

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-2.3+-black?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Scikit--Learn-1.2+-orange?style=for-the-badge&logo=scikit-learn" alt="Scikit-Learn">
  <img src="https://img.shields.io/badge/Plotly-5.15+-3F4F75?style=for-the-badge&logo=plotly" alt="Plotly">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</p>

> An AI-powered, full-stack web platform that helps traders and investors make **risk-aware decisions** on Indian IPOs. It aggregates real-time IPO data, performs multi-dimensional ML-driven analysis, and delivers clear **BUY / AVOID** recommendations with detailed risk scoring.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the App](#running-the-app)
- [Module Breakdown](#-module-breakdown)
- [Pages & Routes](#-pages--routes)
- [API Endpoints](#-api-endpoints)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

The **IPO Intelligence Platform** is a comprehensive research and decision-support tool for the Indian IPO market. It combines:

- **Fundamental Analysis** — financial ratios, valuation metrics, promoter holding
- **Sentiment Analysis** — NLP-based scoring of IPO-related news and market buzz
- **Market Analysis** — sector performance, index trends, and macro signals
- **ML Prediction** — a trained machine-learning model that scores IPO listing potential
- **Decision Engine** — a composite scoring system that synthesises all signals into a final recommendation

All insights are surfaced through an elegant, dark-themed web dashboard built with Flask, Plotly, and Jinja2.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📊 **Live Dashboard** | Overview of all tracked IPOs with scores, risk levels & recommendations |
| 📅 **Upcoming IPOs** | Sorted list of upcoming IPOs with sector breakdown & score distribution charts |
| 🔴 **Live IPOs** | Real-time tracking of currently open IPOs |
| 🏦 **SME IPOs** | Dedicated page for NSE/BSE SME segment listings |
| 🔬 **Deep Analysis** | Per-IPO radar chart across 5 scoring dimensions + subscription bar chart |
| 🌍 **Market Overview** | Macro-level market sentiment & sector performance gauge |
| 📰 **IPO News Feed** | Latest IPO-related news with individual article views |
| 🔥 **IPO Heatmap** | Visual sector/performance heatmap |
| 🤖 **Model Insights** | Transparency page explaining ML model features and logic |
| 🔄 **Cache Refresh API** | Single endpoint to reset the data cache for fresh fetches |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask Web Application                     │
│  (flask_app.py — Routes, Chart Generation, Template Render) │
└─────────────────────┬───────────────────────────────────────┘
                      │ calls
          ┌───────────▼────────────┐
          │     src/ Pipeline      │
          │   (pipeline.py)        │
          └──┬────────┬────────┬───┘
             │        │        │
   ┌─────────▼──┐ ┌───▼────┐ ┌▼───────────┐
   │  src/data  │ │src/    │ │src/decision │
   │            │ │intelli-│ │             │
   │ IPO Data   │ │gence   │ │ Decision    │
   │ Collector  │ │        │ │ Engine      │
   │ Fundamental│ │Sentiment│ │             │
   │ Analyzer   │ │Market  │ └─────────────┘
   │ DB Manager │ │ML Model│
   └────────────┘ └────────┘
```

### Data Flow

```
Raw IPO Data → Fundamental Analysis
            → Sentiment Analysis   → Decision Engine → Recommendation
            → Market Analysis      
            → ML Prediction       
```

---

## 📁 Project Structure

```
IPO-Intelligence-Platform-for-Risk-Aware-Trading-system/
│
├── flask_app.py              # Main Flask application (routes & chart helpers)
├── app.py                    # Alternative/Streamlit entry point
├── requirements.txt          # Python dependencies
├── .gitignore
│
├── src/                      # Core logic modules
│   ├── pipeline.py           # End-to-end orchestration pipeline
│   ├── data/
│   │   ├── ipo_data_collector.py     # Scrapes & caches IPO listings + news
│   │   ├── fundamental_analyzer.py   # Financial ratio analysis
│   │   └── database_manager.py       # SQLite persistence layer
│   │
│   ├── intelligence/
│   │   ├── sentiment_analyzer.py     # NLP-based sentiment scoring (NLTK)
│   │   ├── market_analyzer.py        # Market trend & sector analysis
│   │   └── ml_predictor.py           # Scikit-Learn ML model for listing gain prediction
│   │
│   └── decision/
│       └── decision_engine.py        # Composite scoring & final recommendation logic
│
├── templates/                # Jinja2 HTML templates (dark glassmorphism theme)
│   ├── base.html             # Shared nav, styles, scripts
│   ├── dashboard.html        # Main IPO dashboard
│   ├── upcoming.html         # Upcoming IPOs
│   ├── live.html             # Live/open IPOs
│   ├── sme.html              # SME segment IPOs
│   ├── ipo_analysis.html     # Detailed per-IPO analysis
│   ├── market_overview.html  # Market macro view
│   ├── heatmap.html          # Sector heatmap
│   ├── news.html             # IPO news feed
│   ├── news_detail.html      # Single news article view
│   ├── model_insights.html   # ML model explainability
│   └── about.html            # About the platform
│
├── data/                     # Cached data files & model artifacts
├── models/                   # Saved ML model files
├── config/                   # Configuration files
├── logs/                     # Application log files
└── .streamlit/               # Streamlit config (for app.py)
```

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---|---|
| **Flask 2.3+** | Web framework, routing, templating |
| **Pandas / NumPy** | Data manipulation and numerical computation |
| **Scikit-Learn** | ML model training and prediction |
| **NLTK** | Natural Language Processing for sentiment analysis |
| **Requests / BeautifulSoup4** | Web scraping and HTTP data collection |
| **SQLite** (built-in) | Lightweight local database for caching |
| **Joblib** | Model serialisation and persistence |
| **Streamlit** | Alternative analytical dashboard interface |

### Frontend
| Technology | Purpose |
|---|---|
| **Jinja2** | Server-side HTML templating |
| **Plotly** | Interactive charts (gauges, radar, bar, pie, heatmap) |
| **Vanilla CSS** | Dark glassmorphism design system |
| **JavaScript** | Client-side chart rendering & interactivity |

---

## 🚀 Getting Started

### Prerequisites

- Python **3.9** or higher
- `pip` package manager
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mahiibhalani/IPO-Intelligence-Platform-for-Risk-Aware-Trading-system.git
   cd IPO-Intelligence-Platform-for-Risk-Aware-Trading-system
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download NLTK data** (required for sentiment analysis)
   ```python
   python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('punkt')"
   ```

### Running the App

#### Flask Web App (Recommended)
```bash
python flask_app.py
```
Open your browser at: **http://localhost:5000**

#### Streamlit Dashboard (Alternative)
```bash
streamlit run app.py
```
Open your browser at: **http://localhost:8501**

---

## 📦 Module Breakdown

### `src/data/ipo_data_collector.py`
- Scrapes current IPO listings, GMP (Grey Market Premium) data, and subscription figures
- Caches results in SQLite to avoid repeated requests
- Provides `collect_ipo_listings()`, `get_complete_ipo_data(ipo_id)`, and `collect_ipo_news()`

### `src/data/fundamental_analyzer.py`
- Parses financial metrics: P/E ratio, P/B ratio, RoE, debt levels, revenue growth
- Returns a normalised `fundamental_score` (0–1) and a set of flags/highlights

### `src/intelligence/sentiment_analyzer.py`
- Uses **NLTK VADER** to analyse IPO-related news headlines and text
- Aggregates scores across multiple articles into a single `sentiment_score`

### `src/intelligence/market_analyzer.py`
- Evaluates broader market conditions: index momentum, sector performance, FII/DII flows
- Returns a `market_score` and a market regime label (Bullish / Neutral / Bearish)

### `src/intelligence/ml_predictor.py`
- A **Scikit-Learn** classification/regression model trained on historical IPO data
- Features include subscription data, GMP, fundamentals, and market conditions
- Returns a `predicted_listing_gain` and a `confidence` score

### `src/decision/decision_engine.py`
- Combines all four scores (fundamental, sentiment, market, ML) into a **composite_score**
- Applies risk analysis logic to determine risk level (Low / Medium / High)
- Produces a final **recommendation**: `Strong Apply`, `Apply`, `Avoid`, or `Strong Avoid`

---

## 🌐 Pages & Routes

| Route | Page | Description |
|---|---|---|
| `GET /` | Dashboard | All IPOs with summary table and overview charts |
| `GET /upcoming` | Upcoming IPOs | IPOs opening in the future |
| `GET /live` | Live IPOs | Currently open for subscription |
| `GET /sme` | SME IPOs | NSE/BSE SME segment listings |
| `GET /mainboard` | Mainboard | Alias for dashboard |
| `GET /heatmap` | IPO Heatmap | Sector performance heatmap |
| `GET /news` | News Feed | Latest IPO news |
| `GET /news/<id>` | News Detail | Single article view |
| `GET /ipo-analysis` | IPO Analysis | Select an IPO to deep-analyse |
| `POST /ipo-analysis` | IPO Analysis | Submit form to analyse a specific IPO |
| `GET /market-overview` | Market Overview | Macro market conditions |
| `GET /model-insights` | Model Insights | ML model explainability |
| `GET /about` | About | Platform information |

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/refresh-data` | `GET` | Clears the in-memory data cache, forcing a fresh data fetch |

**Response:**
```json
{
  "status": "success",
  "message": "Data cache cleared"
}
```

---

## ⚙️ Configuration

| Setting | Location | Default |
|---|---|---|
| Flask secret key | `flask_app.py` line 31 | `ipo-intelligence-platform-secret-key` |
| Server host | `flask_app.py` line 675 | `0.0.0.0` |
| Server port | `flask_app.py` line 675 | `5000` |
| Debug mode | `flask_app.py` line 675 | `True` |
| Streamlit settings | `.streamlit/config.toml` | — |

> ⚠️ **Production Note:** Change the `secret_key` and set `debug=False` before deploying to production.

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

Please follow [PEP 8](https://peps.python.org/pep-0008/) for Python code style, and test your changes before submitting.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ for risk-aware trading decisions in the Indian IPO market.
</p>
