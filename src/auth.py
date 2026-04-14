"""
Authentication Routes and Logic
================================
Handles user registration, login, logout, and session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import re

from src.models import db, User, SavedIPO, AppliedIPO, Watchlist, UserPreferences, PortfolioIPO

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_login_manager(app):
    """Initialize Flask-Login."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return login_manager


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format."""
    pattern = r'^[a-zA-Z0-9_]{4,20}$'
    return re.match(pattern, username) is not None


def validate_password_strength(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        risk_tolerance = request.form.get('risk_tolerance', 'moderate')

        # Validation
        errors = []

        if not first_name:
            errors.append('First name is required')
        
        if len(first_name) > 80:
            errors.append('First name too long')

        if not email or not validate_email(email):
            errors.append('Invalid email address')

        if not username or not validate_username(username):
            errors.append('Username must be 4-20 characters, alphanumeric and underscores only')

        if password != confirm_password:
            errors.append('Passwords do not match')

        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            errors.append(msg)

        if not request.form.get('terms'):
            errors.append('You must accept the terms of service')

        # Check if user exists
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')

        if errors:
            error_msg = ' | '.join(errors)
            return redirect(url_for('auth.register', error=error_msg))

        try:
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name or ''
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            # Create user preferences
            preferences = UserPreferences(
                user_id=user.id,
                risk_tolerance=risk_tolerance
            )
            db.session.add(preferences)
            db.session.commit()

            logger.info(f"New user registered: {username}")
            
            # Auto-login the user
            login_user(user, remember=True)
            
            return redirect(url_for('dashboard', success="Account created successfully! Welcome to IPO Intelligence Platform."))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return redirect(url_for('auth.register', error="Registration failed. Please try again."))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not username_or_email or not password:
            return redirect(url_for('auth.login', error='Username and password required'))

        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                return redirect(url_for('auth.login', error='Account is deactivated'))
            
            login_user(user, remember=remember)
            logger.info(f"User logged in: {user.username}")
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt for: {username_or_email}")
            return redirect(url_for('auth.login', error='Invalid username or password'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logger.info(f"User logged out: {current_user.username}")
    logout_user()
    return redirect(url_for('auth.login', success='Logged out successfully'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    saved_ipos = SavedIPO.query.filter_by(user_id=current_user.id).all()
    applied_ipos = AppliedIPO.query.filter_by(user_id=current_user.id).all()
    watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    portfolio = PortfolioIPO.query.filter_by(user_id=current_user.id).all()
    user_preferences = UserPreferences.query.filter_by(user_id=current_user.id).first()

    return render_template('profile.html',
                         saved_ipos_list=saved_ipos,
                         saved_ipos_count=len(saved_ipos),
                         applied_ipos_list=applied_ipos,
                         applied_ipos_count=len(applied_ipos),
                         watchlist_list=watchlist,
                         watchlist_count=len(watchlist),
                         portfolio_list=portfolio,
                         portfolio_count=len(portfolio),
                         user_preferences=user_preferences or UserPreferences(user_id=current_user.id))


@auth_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()

        # Validation
        if not first_name:
            return redirect(url_for('auth.edit_profile', error='First name required'))

        if email != current_user.email:
            if not validate_email(email) or User.query.filter_by(email=email).first():
                return redirect(url_for('auth.edit_profile', error='Invalid or already used email'))

        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email
        current_user.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            logger.info(f"Profile updated: {current_user.username}")
            return redirect(url_for('auth.profile', success='Profile updated successfully'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {e}")
            return redirect(url_for('auth.edit_profile', error='Update failed'))

    return render_template('edit_profile.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            return redirect(url_for('auth.change_password', error='Current password is incorrect'))

        if new_password != confirm_password:
            return redirect(url_for('auth.change_password', error='New passwords do not match'))

        is_strong, msg = validate_password_strength(new_password)
        if not is_strong:
            return redirect(url_for('auth.change_password', error=msg))

        current_user.set_password(new_password)
        current_user.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            logger.info(f"Password changed: {current_user.username}")
            return redirect(url_for('auth.profile', success='Password changed successfully'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password change error: {e}")
            return redirect(url_for('auth.change_password', error='Change failed'))

    return render_template('change_password.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password recovery."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            # In production, send reset email
            logger.info(f"Password reset requested for: {email}")
            return redirect(url_for('auth.login', success='If email exists, reset link sent'))
        else:
            # Security: don't reveal if email exists
            return redirect(url_for('auth.login', success='If email exists, reset link sent'))

    return render_template('forgot_password.html')


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account."""
    try:
        user_id = current_user.id
        username = current_user.username

        # Delete all related data
        SavedIPO.query.filter_by(user_id=user_id).delete()
        AppliedIPO.query.filter_by(user_id=user_id).delete()
        Watchlist.query.filter_by(user_id=user_id).delete()
        PortfolioIPO.query.filter_by(user_id=user_id).delete()
        UserPreferences.query.filter_by(user_id=user_id).delete()
        User.query.filter_by(id=user_id).delete()

        db.session.commit()
        logout_user()

        logger.info(f"Account deleted: {username}")
        return redirect(url_for('dashboard', success='Account deleted'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Account deletion error: {e}")
        return redirect(url_for('auth.profile', error='Deletion failed'))


# API Routes for AJAX calls

@auth_bp.route('/api/toggle-save-ipo/<ipo_id>', methods=['POST'])
@login_required
def toggle_save_ipo(ipo_id):
    """Toggle IPO in saved list."""
    saved = SavedIPO.query.filter_by(
        user_id=current_user.id,
        ipo_id=ipo_id
    ).first()

    try:
        if saved:
            db.session.delete(saved)
        else:
            # Get IPO data from collector (simplified)
            saved_ipo = SavedIPO(
                user_id=current_user.id,
                ipo_id=ipo_id,
                company_name=request.json.get('company_name', 'Unknown'),
                sector=request.json.get('sector'),
                price_band=request.json.get('price_band'),
                issue_size=request.json.get('issue_size')
            )
            db.session.add(saved_ipo)

        db.session.commit()
        return jsonify({'status': 'success', 'saved': not bool(saved)})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Toggle save error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@auth_bp.route('/api/add-applied-ipo', methods=['POST'])
@login_required
def add_applied_ipo():
    """Add IPO to applied list."""
    data = request.json

    try:
        applied_ipo = AppliedIPO(
            user_id=current_user.id,
            ipo_id=data.get('ipo_id'),
            company_name=data.get('company_name'),
            decision=data.get('decision'),
            ai_score=float(data.get('ai_score', 5.0)),
            quantity=int(data.get('quantity', 0))
        )
        db.session.add(applied_ipo)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Added to applied IPOs'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Add applied IPO error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@auth_bp.route('/api/add-watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add IPO to watchlist."""
    data = request.json

    try:
        watchlist_item = Watchlist(
            user_id=current_user.id,
            ipo_id=data.get('ipo_id'),
            company_name=data.get('company_name'),
            listing_price_target=float(data.get('listing_price_target', 0)) if data.get('listing_price_target') else None,
            target_return=float(data.get('target_return', 0)) if data.get('target_return') else None
        )
        db.session.add(watchlist_item)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Added to watchlist'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Add watchlist error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
