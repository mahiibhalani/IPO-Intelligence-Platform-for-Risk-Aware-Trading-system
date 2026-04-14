"""
User and IPO Favorites Models
==============================
Database models for user authentication and saved IPO preferences.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    saved_ipos = db.relationship('SavedIPO', backref='user', lazy=True, cascade='all, delete-orphan')
    applied_ipos = db.relationship('AppliedIPO', backref='user', lazy=True, cascade='all, delete-orphan')
    watchlist = db.relationship('Watchlist', backref='user', lazy=True, cascade='all, delete-orphan')
    user_preferences = db.relationship('UserPreferences', backref='user', uselist=False, 
                                      cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'


class SavedIPO(db.Model):
    """Model for user's saved/starred IPOs."""
    __tablename__ = 'saved_ipos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ipo_id = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(80), nullable=True)
    price_band = db.Column(db.String(50), nullable=True)
    issue_size = db.Column(db.Float, nullable=True)
    lot_size = db.Column(db.String(50), nullable=True)
    subscription = db.Column(db.String(50), nullable=True)
    gmp = db.Column(db.String(50), nullable=True)
    ai_score = db.Column(db.Float, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)  # Strong Apply, Apply, Avoid, Strong Avoid
    risk_level = db.Column(db.String(20), nullable=True)  # Low, Medium, High
    status = db.Column(db.String(20), default='starred')  # starred, watchlist, etc.
    open_date = db.Column(db.String(50), nullable=True)
    close_date = db.Column(db.String(50), nullable=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'ipo_id', name='unique_user_ipo'),)
    
    def __repr__(self):
        return f'<SavedIPO {self.company_name}>'


class AppliedIPO(db.Model):
    """Model for IPOs user decided to apply for."""
    __tablename__ = 'applied_ipos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ipo_id = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    decision = db.Column(db.String(50), nullable=False)  # Apply, Hold, Avoid, etc.
    ai_score = db.Column(db.Float, nullable=True)
    user_score = db.Column(db.Float, nullable=True)  # User's own rating
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    application_status = db.Column(db.String(50), default='pending')  # pending, applied, allotted, rejected
    quantity = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'ipo_id', name='unique_user_applied_ipo'),)
    
    def __repr__(self):
        return f'<AppliedIPO {self.company_name}>'


class Watchlist(db.Model):
    """Model for IPO watchlist tracking."""
    __tablename__ = 'watchlist'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ipo_id = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    listing_price_target = db.Column(db.Float, nullable=True)
    target_return = db.Column(db.Float, nullable=True)  # Expected return %
    notes = db.Column(db.Text, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'ipo_id', name='unique_watchlist_entry'),)
    
    def __repr__(self):
        return f'<Watchlist {self.company_name}>'


class UserPreferences(db.Model):
    """Model for user preferences and settings."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    theme = db.Column(db.String(20), default='dark')  # dark, light
    email_alerts = db.Column(db.Boolean, default=True)
    price_alerts = db.Column(db.Boolean, default=True)
    subscription_alerts = db.Column(db.Boolean, default=True)
    listing_alerts = db.Column(db.Boolean, default=True)
    risk_tolerance = db.Column(db.String(20), default='moderate')  # low, moderate, high
    min_investment_size = db.Column(db.Float, default=0)  # Minimum issue size in Cr
    preferred_sectors = db.Column(db.String(500), default='')  # Comma-separated
    notification_frequency = db.Column(db.String(20), default='daily')  # real-time, daily, weekly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserPreferences {self.user_id}>'


class PortfolioIPO(db.Model):
    """Model for tracking user's IPO portfolio after listing."""
    __tablename__ = 'portfolio_ipos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ipo_id = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    listing_date = db.Column(db.DateTime, nullable=True)
    listing_price = db.Column(db.Float, nullable=True)
    quantity_allotted = db.Column(db.Integer, nullable=False)
    application_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    investment_amount = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PortfolioIPO {self.company_name}>'
