"""
Machine Learning Prediction Module
===================================
Implements ML models for IPO listing performance prediction.
Uses ensemble methods with feature engineering specific to IPO data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
import pickle
import joblib
from pathlib import Path
from datetime import datetime

# ML imports
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score
)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import ML_CONFIG, MODELS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPOPredictionModel:
    """
    Machine Learning model for IPO listing performance prediction.
    
    Features:
    - Multi-class prediction (Strong Apply, Apply, Hold, Avoid)
    - Ensemble of Random Forest, XGBoost-style Gradient Boosting, and Logistic Regression
    - Feature importance analysis
    - Confidence scoring
    - Model persistence
    """
    
    def __init__(self):
        self.config = ML_CONFIG
        self.models = {}
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        
        # Initialize models
        self._initialize_models()
        
        # Try to load existing models
        if not self.load_models():
            logger.info("No saved models found, will train on first use")
    
    def _initialize_models(self):
        """Initialize ML models."""
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=self.config['random_forest']['n_estimators'],
                max_depth=self.config['random_forest']['max_depth'],
                min_samples_split=self.config['random_forest']['min_samples_split'],
                min_samples_leaf=self.config['random_forest']['min_samples_leaf'],
                random_state=self.config['random_forest']['random_state'],
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=self.config['xgboost']['n_estimators'],
                max_depth=self.config['xgboost']['max_depth'],
                learning_rate=self.config['xgboost']['learning_rate'],
                subsample=self.config['xgboost']['subsample'],
                random_state=self.config['xgboost']['random_state']
            ),
            'logistic_regression': LogisticRegression(
                C=self.config['logistic_regression']['C'],
                max_iter=self.config['logistic_regression']['max_iter'],
                random_state=self.config['logistic_regression']['random_state']
            )
        }
    
    def prepare_features(self, ipo_data: Dict) -> np.ndarray:
        """
        Prepare feature vector from IPO data.
        
        Args:
            ipo_data: Dictionary containing all IPO-related data
            
        Returns:
            Feature array ready for prediction
        """
        fundamentals = ipo_data.get('fundamentals', {})
        subscription = ipo_data.get('subscription', {})
        gmp = ipo_data.get('gmp', {})
        market = ipo_data.get('market', {})
        sentiment = ipo_data.get('sentiment', {})
        basic = ipo_data.get('basic_info', {})
        
        # Extract features
        features = {
            # Fundamental features
            'roe': fundamentals.get('roe', 0),
            'roce': fundamentals.get('roce', 0),
            'ebitda_margin': fundamentals.get('ebitda_margin', 0),
            'pat_margin': fundamentals.get('pat_margin', 0),
            'debt_to_equity': fundamentals.get('debt_to_equity', 0),
            'current_ratio': fundamentals.get('current_ratio', 0),
            'pe_ratio': fundamentals.get('pe_ratio', 0),
            'revenue_growth': fundamentals.get('revenue_growth_3yr', 0),
            'pat_growth': fundamentals.get('pat_growth_3yr', 0),
            'promoter_holding': fundamentals.get('promoter_holding_post', 0),
            
            # Subscription features
            'qib_subscription': subscription.get('qib_subscription', 0),
            'nii_subscription': subscription.get('nii_subscription', 0),
            'retail_subscription': subscription.get('retail_subscription', 0),
            'total_subscription': subscription.get('total_subscription', 0),
            'anchor_subscribed': 1 if subscription.get('anchor_portion_subscribed') else 0,
            
            # GMP features
            'gmp_percentage': gmp.get('gmp_percentage', 0),
            'gmp_trend_score': self._encode_gmp_trend(gmp.get('gmp_trend', 'stable')),
            
            # Market features
            'nifty_change': market.get('nifty_50_change_pct', 0),
            'nifty_5d_return': market.get('nifty_50_5day_return', 0),
            'india_vix': market.get('india_vix', 15),
            'fii_net': market.get('fii_net_investment', 0) / 1000,  # Scale down
            'market_sentiment_score': self._encode_market_sentiment(
                market.get('market_sentiment', 'neutral')
            ),
            
            # Sentiment features
            'sentiment_score': sentiment.get('composite_score', 0.5) if isinstance(sentiment, dict) else 0.5,
            
            # Size features
            'issue_size_normalized': basic.get('issue_size_cr', 0) / 1000,  # Scale down
            'lot_size': basic.get('lot_size', 0) / 100,  # Scale down
        }
        
        self.feature_names = list(features.keys())
        return np.array(list(features.values())).reshape(1, -1)
    
    def _encode_gmp_trend(self, trend: str) -> float:
        """Encode GMP trend to numeric."""
        mapping = {
            'increasing': 1.0,
            'stable': 0.5,
            'decreasing': 0.0
        }
        return mapping.get(trend.lower(), 0.5)
    
    def _encode_market_sentiment(self, sentiment: str) -> float:
        """Encode market sentiment to numeric."""
        mapping = {
            'bullish': 1.0,
            'positive': 0.8,
            'neutral': 0.5,
            'negative': 0.3,
            'bearish': 0.0
        }
        return mapping.get(sentiment.lower(), 0.5)
    
    def generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for model training.
        In production, this would come from historical IPO data.
        
        Returns:
            Tuple of (features, labels)
        """
        np.random.seed(42)
        n_samples = 500
        
        # Generate synthetic features
        data = []
        labels = []
        
        for _ in range(n_samples):
            # Generate correlated features that mimic real IPO patterns
            quality = np.random.random()  # Base quality metric
            
            # Fundamentals - higher quality = better fundamentals
            roe = np.clip(quality * 30 + np.random.normal(0, 5), 0, 40)
            roce = np.clip(roe * 1.1 + np.random.normal(0, 3), 0, 50)
            ebitda_margin = np.clip(quality * 35 + np.random.normal(0, 5), 5, 45)
            pat_margin = np.clip(ebitda_margin * 0.6 + np.random.normal(0, 3), 0, 30)
            debt_to_equity = np.clip((1 - quality) * 2 + np.random.normal(0, 0.3), 0, 3)
            current_ratio = np.clip(quality * 2.5 + 0.5 + np.random.normal(0, 0.3), 0.5, 4)
            pe_ratio = np.clip(15 + (1 - quality) * 30 + np.random.normal(0, 5), 10, 60)
            revenue_growth = np.clip(quality * 40 + np.random.normal(0, 8), -10, 60)
            pat_growth = np.clip(revenue_growth * 1.2 + np.random.normal(0, 10), -20, 80)
            promoter_holding = np.clip(quality * 30 + 40 + np.random.normal(0, 5), 30, 85)
            
            # Subscription - correlated with quality
            base_sub = quality * 80
            qib_subscription = np.clip(base_sub * 1.5 + np.random.normal(0, 20), 0.5, 200)
            nii_subscription = np.clip(base_sub * 2 + np.random.normal(0, 30), 0.3, 300)
            retail_subscription = np.clip(base_sub * 0.5 + np.random.normal(0, 10), 0.2, 50)
            total_subscription = (qib_subscription + nii_subscription + retail_subscription) / 3
            anchor_subscribed = 1 if quality > 0.4 else np.random.choice([0, 1])
            
            # GMP - correlated with quality and subscription
            gmp_percentage = np.clip(quality * 50 - 10 + np.random.normal(0, 10), -30, 80)
            gmp_trend_score = np.clip(quality + np.random.normal(0, 0.2), 0, 1)
            
            # Market conditions - somewhat random
            market_factor = np.random.random()
            nifty_change = np.random.normal(0, 1)
            nifty_5d_return = np.random.normal(0, 2)
            india_vix = np.clip(np.random.normal(18, 8), 10, 40)
            fii_net = np.random.normal(0, 2)
            market_sentiment_score = np.clip(market_factor + np.random.normal(0, 0.2), 0, 1)
            
            # Sentiment - correlated with quality
            sentiment_score = np.clip(quality * 0.8 + 0.1 + np.random.normal(0, 0.1), 0, 1)
            
            # Size features
            issue_size_normalized = np.random.uniform(0.1, 5)
            lot_size = np.random.uniform(0.2, 2)
            
            features = [
                roe, roce, ebitda_margin, pat_margin, debt_to_equity, current_ratio,
                pe_ratio, revenue_growth, pat_growth, promoter_holding,
                qib_subscription, nii_subscription, retail_subscription, total_subscription,
                anchor_subscribed, gmp_percentage, gmp_trend_score,
                nifty_change, nifty_5d_return, india_vix, fii_net, market_sentiment_score,
                sentiment_score, issue_size_normalized, lot_size
            ]
            
            data.append(features)
            
            # Generate label based on combined factors
            combined_score = (
                quality * 0.4 +
                (total_subscription / 100) * 0.2 +
                (gmp_percentage / 50) * 0.15 +
                market_factor * 0.1 +
                sentiment_score * 0.15
            )
            
            # Add some noise
            combined_score += np.random.normal(0, 0.1)
            
            # Assign labels
            if combined_score > 0.7:
                label = "Strong Apply"
            elif combined_score > 0.5:
                label = "Apply"
            elif combined_score > 0.3:
                label = "Hold"
            else:
                label = "Avoid"
            
            labels.append(label)
        
        self.feature_names = [
            'roe', 'roce', 'ebitda_margin', 'pat_margin', 'debt_to_equity', 'current_ratio',
            'pe_ratio', 'revenue_growth', 'pat_growth', 'promoter_holding',
            'qib_subscription', 'nii_subscription', 'retail_subscription', 'total_subscription',
            'anchor_subscribed', 'gmp_percentage', 'gmp_trend_score',
            'nifty_change', 'nifty_5d_return', 'india_vix', 'fii_net', 'market_sentiment_score',
            'sentiment_score', 'issue_size_normalized', 'lot_size'
        ]
        
        return np.array(data), np.array(labels)
    
    def train(self, X: np.ndarray = None, y: np.ndarray = None) -> Dict:
        """
        Train the ensemble model.
        
        Args:
            X: Feature matrix (optional, will generate synthetic data if not provided)
            y: Labels (optional)
            
        Returns:
            Training metrics
        """
        logger.info("Training IPO prediction models...")
        
        if X is None or y is None:
            X, y = self.generate_training_data()
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded,
            test_size=self.config['test_size'],
            random_state=42,
            stratify=y_encoded
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train each model
        metrics = {}
        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            
            # Train
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            
            metrics[name] = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, average='weighted'),
                'recall': recall_score(y_test, y_pred, average='weighted'),
                'f1': f1_score(y_test, y_pred, average='weighted')
            }
            
            # Cross-validation
            cv_scores = cross_val_score(
                model, X_train_scaled, y_train,
                cv=self.config['cross_validation_folds']
            )
            metrics[name]['cv_mean'] = cv_scores.mean()
            metrics[name]['cv_std'] = cv_scores.std()
        
        self.is_trained = True
        
        # Log best model
        best_model = max(metrics.items(), key=lambda x: x[1]['accuracy'])
        logger.info(f"Best model: {best_model[0]} with accuracy: {best_model[1]['accuracy']:.3f}")
        
        return metrics
    
    def predict(self, ipo_data: Dict) -> Dict:
        """
        Predict IPO listing performance.
        
        Args:
            ipo_data: Complete IPO data dictionary
            
        Returns:
            Prediction results with confidence
        """
        if not self.is_trained:
            # Train with synthetic data if not trained
            self.train()
            # Save models after training
            self.save_models()
        
        # Prepare features
        features = self.prepare_features(ipo_data)
        features_scaled = self.scaler.transform(features)
        
        # Get predictions from all models
        predictions = {}
        probabilities = {}
        
        for name, model in self.models.items():
            pred = model.predict(features_scaled)[0]
            prob = model.predict_proba(features_scaled)[0]
            
            predictions[name] = self.label_encoder.inverse_transform([pred])[0]
            probabilities[name] = dict(zip(
                self.label_encoder.classes_,
                prob
            ))
        
        # Ensemble prediction (majority voting with confidence weighting)
        ensemble_pred = self._ensemble_predict(predictions, probabilities)
        
        # Get feature importance
        feature_importance = self._get_feature_importance()
        
        return {
            "prediction": ensemble_pred["prediction"],
            "confidence": ensemble_pred["confidence"],
            "probabilities": ensemble_pred["probabilities"],
            "model_predictions": predictions,
            "feature_importance": feature_importance[:10],  # Top 10
            "recommendation_strength": self._get_recommendation_strength(
                ensemble_pred["confidence"]
            )
        }
    
    def _ensemble_predict(self, predictions: Dict, probabilities: Dict) -> Dict:
        """Combine predictions from all models."""
        # Get all predictions
        pred_list = list(predictions.values())
        
        # Majority voting
        from collections import Counter
        vote_counts = Counter(pred_list)
        ensemble_prediction = vote_counts.most_common(1)[0][0]
        
        # Average probabilities
        avg_probs = {}
        for label in self.label_encoder.classes_:
            avg_probs[label] = np.mean([
                probabilities[model].get(label, 0)
                for model in probabilities
            ])
        
        # Confidence is the average probability of the predicted class
        confidence = avg_probs[ensemble_prediction]
        
        return {
            "prediction": ensemble_prediction,
            "confidence": float(confidence),
            "probabilities": avg_probs
        }
    
    def _get_feature_importance(self) -> List[Dict]:
        """Get feature importance from Random Forest."""
        if 'random_forest' in self.models:
            rf = self.models['random_forest']
            importances = rf.feature_importances_
            
            importance_list = []
            for name, importance in zip(self.feature_names, importances):
                importance_list.append({
                    "feature": name,
                    "importance": float(importance)
                })
            
            # Sort by importance
            importance_list.sort(key=lambda x: x['importance'], reverse=True)
            return importance_list
        
        return []
    
    def _get_recommendation_strength(self, confidence: float) -> str:
        """Convert confidence to recommendation strength."""
        if confidence >= 0.8:
            return "Very Strong"
        elif confidence >= 0.65:
            return "Strong"
        elif confidence >= 0.5:
            return "Moderate"
        elif confidence >= 0.35:
            return "Weak"
        else:
            return "Very Weak"
    
    def save_models(self, path: Path = None):
        """Save trained models to disk."""
        if path is None:
            path = MODELS_DIR
        
        path.mkdir(parents=True, exist_ok=True)
        
        # Save models
        for name, model in self.models.items():
            joblib.dump(model, path / f"{name}.joblib")
        
        # Save scaler and encoder
        joblib.dump(self.scaler, path / "scaler.joblib")
        joblib.dump(self.label_encoder, path / "label_encoder.joblib")
        
        # Save feature names
        with open(path / "feature_names.pkl", 'wb') as f:
            pickle.dump(self.feature_names, f)
        
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: Path = None):
        """Load trained models from disk."""
        if path is None:
            path = MODELS_DIR
        
        try:
            # Load models
            for name in self.models.keys():
                model_path = path / f"{name}.joblib"
                if model_path.exists():
                    self.models[name] = joblib.load(model_path)
            
            # Load scaler and encoder
            self.scaler = joblib.load(path / "scaler.joblib")
            self.label_encoder = joblib.load(path / "label_encoder.joblib")
            
            # Load feature names
            with open(path / "feature_names.pkl", 'rb') as f:
                self.feature_names = pickle.load(f)
            
            self.is_trained = True
            logger.info(f"Models loaded from {path}")
            return True
            
        except Exception as e:
            logger.warning(f"Could not load models: {e}")
            return False


# Module-level instance
prediction_model = IPOPredictionModel()


if __name__ == "__main__":
    # Test the prediction model
    model = IPOPredictionModel()
    
    # Train with synthetic data
    print("Training models...")
    metrics = model.train()
    
    print("\nModel Performance:")
    for name, m in metrics.items():
        print(f"\n{name}:")
        print(f"  Accuracy: {m['accuracy']:.3f}")
        print(f"  F1 Score: {m['f1']:.3f}")
        print(f"  CV Score: {m['cv_mean']:.3f} (+/- {m['cv_std']:.3f})")
    
    # Test prediction
    sample_ipo_data = {
        "basic_info": {"issue_size_cr": 1200, "lot_size": 50},
        "fundamentals": {
            "roe": 18.5, "roce": 21.2, "ebitda_margin": 22.5, "pat_margin": 14.9,
            "debt_to_equity": 0.35, "current_ratio": 2.1, "pe_ratio": 28.5,
            "revenue_growth_3yr": 37.5, "pat_growth_3yr": 52.3, "promoter_holding_post": 58.2
        },
        "subscription": {
            "qib_subscription": 85.5, "nii_subscription": 125.8, "retail_subscription": 15.2,
            "total_subscription": 45.8, "anchor_portion_subscribed": True
        },
        "gmp": {"gmp_percentage": 28.3, "gmp_trend": "increasing"},
        "market": {
            "nifty_50_change_pct": 0.85, "nifty_50_5day_return": 2.15,
            "india_vix": 14.25, "fii_net_investment": 2850.5, "market_sentiment": "bullish"
        },
        "sentiment": {"composite_score": 0.75}
    }
    
    print("\n\nSample Prediction:")
    result = model.predict(sample_ipo_data)
    print(f"Prediction: {result['prediction']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Strength: {result['recommendation_strength']}")
    print("\nTop Features:")
    for feat in result['feature_importance'][:5]:
        print(f"  {feat['feature']}: {feat['importance']:.3f}")
