"""
User Features API Routes
========================
API endpoints for authenticated user features like saving IPOs, 
adding to watchlist, tracking decisions, etc.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging

from src.models import db, SavedIPO, AppliedIPO, Watchlist, PortfolioIPO, UserPreferences

user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/user')
logger = logging.getLogger(__name__)


@user_api_bp.route('/save-ipo', methods=['POST'])
@login_required
def save_ipo():
    """Save IPO to user's list."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        
        # Check if already saved
        existing = SavedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first()
        
        if existing:
            return jsonify({'status': 'success', 'message': 'Already saved'}), 200
        
        saved_ipo = SavedIPO(
            user_id=current_user.id,
            ipo_id=ipo_id,
            company_name=data.get('company_name', 'Unknown'),
            sector=data.get('sector'),
            price_band=data.get('price_band'),
            issue_size=float(data.get('issue_size', 0)) if data.get('issue_size') else None,
            notes=data.get('notes', '')
        )
        
        db.session.add(saved_ipo)
        db.session.commit()
        
        logger.info(f"IPO saved: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'IPO saved successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Save IPO error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/unsave-ipo/<ipo_id>', methods=['DELETE'])
@login_required
def unsave_ipo(ipo_id):
    """Remove IPO from saved list."""
    try:
        saved_ipo = SavedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first_or_404()
        
        db.session.delete(saved_ipo)
        db.session.commit()
        
        logger.info(f"IPO unsaved: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'IPO removed from saved list'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unsave IPO error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/is-saved/<ipo_id>', methods=['GET'])
@login_required
def is_saved(ipo_id):
    """Check if IPO is saved."""
    saved = SavedIPO.query.filter_by(
        user_id=current_user.id,
        ipo_id=ipo_id
    ).first() is not None
    
    return jsonify({'saved': saved}), 200


@user_api_bp.route('/toggle-save-ipo', methods=['POST'])
@login_required
def toggle_save_ipo():
    """Toggle IPO save status (save if not saved, unsave if saved)."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        
        # Check if already saved
        existing = SavedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first()
        
        if existing:
            # Unsave the IPO
            db.session.delete(existing)
            db.session.commit()
            logger.info(f"IPO unsaved: {current_user.username} - {ipo_id}")
            return jsonify({'status': 'success', 'message': 'IPO removed from saved list', 'saved': False}), 200
        else:
            # Save the IPO with all available details
            saved_ipo = SavedIPO(
                user_id=current_user.id,
                ipo_id=ipo_id,
                company_name=data.get('company_name', 'Unknown'),
                sector=data.get('sector'),
                price_band=data.get('price_band'),
                issue_size=float(data.get('issue_size', 0)) if data.get('issue_size') else None,
                lot_size=data.get('lot_size'),
                subscription=data.get('subscription'),
                gmp=data.get('gmp'),
                ai_score=float(data.get('ai_score', 0)) if data.get('ai_score') else None,
                recommendation=data.get('recommendation'),
                risk_level=data.get('risk_level'),
                open_date=data.get('open_date'),
                close_date=data.get('close_date'),
                notes=data.get('notes', '')
            )
            
            db.session.add(saved_ipo)
            db.session.commit()
            
            logger.info(f"IPO saved: {current_user.username} - {ipo_id}")
            return jsonify({'status': 'success', 'message': 'IPO saved successfully', 'saved': True}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toggle save IPO error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



@user_api_bp.route('/apply-decision', methods=['POST'])
@login_required
def apply_decision():
    """Record user's apply/hold/avoid decision for an IPO."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        decision = data.get('decision')  # Apply, Hold, Avoid
        
        # Check if already exists
        existing = AppliedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first()
        
        if existing:
            existing.decision = decision
            existing.user_score = float(data.get('user_score', 0)) if data.get('user_score') else None
            existing.notes = data.get('notes', '')
            existing.quantity = int(data.get('quantity', 0)) if data.get('quantity') else None
        else:
            applied_ipo = AppliedIPO(
                user_id=current_user.id,
                ipo_id=ipo_id,
                company_name=data.get('company_name', 'Unknown'),
                decision=decision,
                ai_score=float(data.get('ai_score', 0)) if data.get('ai_score') else None,
                user_score=float(data.get('user_score', 0)) if data.get('user_score') else None,
                quantity=int(data.get('quantity', 0)) if data.get('quantity') else None,
                notes=data.get('notes', '')
            )
            db.session.add(applied_ipo)
        
        db.session.commit()
        
        logger.info(f"Apply decision recorded: {current_user.username} - {ipo_id}: {decision}")
        return jsonify({'status': 'success', 'message': f'Decision recorded: {decision}'}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Apply decision error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/apply-decision', methods=['DELETE'])
@login_required
def delete_applied_decision():
    """Remove applied IPO decision."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        
        applied_ipo = AppliedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first_or_404()
        
        db.session.delete(applied_ipo)
        db.session.commit()
        
        logger.info(f"Applied IPO removed: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'Removed from applied IPOs'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete applied IPO error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/get-decision/<ipo_id>', methods=['GET'])
@login_required
def get_decision(ipo_id):
    """Get user's decision for an IPO."""
    applied = AppliedIPO.query.filter_by(
        user_id=current_user.id,
        ipo_id=ipo_id
    ).first()
    
    if applied:
        return jsonify({
            'has_decision': True,
            'decision': applied.decision,
            'user_score': applied.user_score,
            'quantity': applied.quantity
        }), 200
    
    return jsonify({'has_decision': False}), 200


@user_api_bp.route('/add-to-watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add IPO to watchlist with price targets."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        
        # Check if already in watchlist
        existing = Watchlist.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first()
        
        if existing:
            return jsonify({'status': 'success', 'message': 'Already in watchlist'}), 200
        
        watchlist_item = Watchlist(
            user_id=current_user.id,
            ipo_id=ipo_id,
            company_name=data.get('company_name', 'Unknown'),
            listing_price_target=float(data.get('listing_price_target', 0)) if data.get('listing_price_target') else None,
            target_return=float(data.get('target_return', 0)) if data.get('target_return') else None,
            notes=data.get('notes', '')
        )
        
        db.session.add(watchlist_item)
        db.session.commit()
        
        logger.info(f"Added to watchlist: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'Added to watchlist'}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Add to watchlist error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/remove-from-watchlist/<ipo_id>', methods=['DELETE'])
@login_required
def remove_from_watchlist(ipo_id):
    """Remove IPO from watchlist."""
    try:
        watchlist_item = Watchlist.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first_or_404()
        
        db.session.delete(watchlist_item)
        db.session.commit()
        
        logger.info(f"Removed from watchlist: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'Removed from watchlist'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Remove from watchlist error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/get-saved-ipos', methods=['GET'])
@login_required
def get_saved_ipos():
    """Get all saved IPOs for current user."""
    saved_ipos = SavedIPO.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'count': len(saved_ipos),
        'ipos': [{
            'ipo_id': ipo.ipo_id,
            'company_name': ipo.company_name,
            'sector': ipo.sector,
            'price_band': ipo.price_band,
            'issue_size': ipo.issue_size,
            'notes': ipo.notes or '',
            'saved_at': ipo.saved_at.isoformat()
        } for ipo in saved_ipos]
    }), 200


@user_api_bp.route('/update-saved-note/<ipo_id>', methods=['PATCH'])
@login_required
def update_saved_note(ipo_id):
    """Update notes for a saved IPO."""
    try:
        saved_ipo = SavedIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first_or_404()

        data = request.get_json()
        saved_ipo.notes = data.get('notes', '')
        db.session.commit()

        logger.info(f"Note updated: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'Note saved'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update note error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/bulk-remove-saved', methods=['DELETE'])
@login_required
def bulk_remove_saved():
    """Remove multiple saved IPOs at once."""
    try:
        data = request.get_json()
        ipo_ids = data.get('ipo_ids', [])

        if not ipo_ids:
            return jsonify({'status': 'error', 'message': 'No IPO IDs provided'}), 400

        SavedIPO.query.filter(
            SavedIPO.user_id == current_user.id,
            SavedIPO.ipo_id.in_(ipo_ids)
        ).delete(synchronize_session=False)

        db.session.commit()
        logger.info(f"Bulk removed {len(ipo_ids)} IPOs: {current_user.username}")
        return jsonify({'status': 'success', 'removed': len(ipo_ids)}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk remove error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/get-watchlist', methods=['GET'])
@login_required
def get_watchlist():
    """Get user's watchlist."""
    watchlist_items = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'count': len(watchlist_items),
        'items': [{
            'ipo_id': item.ipo_id,
            'company_name': item.company_name,
            'listing_price_target': item.listing_price_target,
            'target_return': item.target_return,
            'added_at': item.added_at.isoformat()
        } for item in watchlist_items]
    }), 200


@user_api_bp.route('/get-decisions', methods=['GET'])
@login_required
def get_decisions():
    """Get all user's decisions."""
    decisions = AppliedIPO.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'count': len(decisions),
        'decisions': [{
            'ipo_id': d.ipo_id,
            'company_name': d.company_name,
            'decision': d.decision,
            'user_score': d.user_score,
            'ai_score': d.ai_score,
            'quantity': d.quantity,
            'applied_at': d.applied_at.isoformat()
        } for d in decisions]
    }), 200


@user_api_bp.route('/update-portfolio-ipo', methods=['POST'])
@login_required
def update_portfolio_ipo():
    """Update or add IPO to user's portfolio."""
    try:
        data = request.get_json()
        ipo_id = data.get('ipo_id')
        
        portfolio = PortfolioIPO.query.filter_by(
            user_id=current_user.id,
            ipo_id=ipo_id
        ).first()
        
        if portfolio:
            portfolio.current_price = float(data.get('current_price', portfolio.current_price))
            portfolio.current_value = portfolio.current_price * portfolio.quantity_allotted if portfolio.current_price else None
        else:
            portfolio = PortfolioIPO(
                user_id=current_user.id,
                ipo_id=ipo_id,
                company_name=data.get('company_name', 'Unknown'),
                listing_date=datetime.fromisoformat(data['listing_date']) if data.get('listing_date') else None,
                listing_price=float(data.get('listing_price', 0)) if data.get('listing_price') else None,
                quantity_allotted=int(data.get('quantity_allotted', 0)),
                application_price=float(data.get('application_price', 0)),
                current_price=float(data.get('current_price', 0)) if data.get('current_price') else None,
                investment_amount=float(data.get('investment_amount', 0))
            )
            portfolio.current_value = portfolio.current_price * portfolio.quantity_allotted if portfolio.current_price else None
            db.session.add(portfolio)
        
        db.session.commit()
        
        logger.info(f"Portfolio updated: {current_user.username} - {ipo_id}")
        return jsonify({'status': 'success', 'message': 'Portfolio updated'}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Portfolio update error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/get-preferences', methods=['GET'])
@login_required
def get_preferences():
    """Get user preferences."""
    prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
    
    if prefs:
        return jsonify({
            'theme': prefs.theme,
            'email_alerts': prefs.email_alerts,
            'price_alerts': prefs.price_alerts,
            'subscription_alerts': prefs.subscription_alerts,
            'listing_alerts': prefs.listing_alerts,
            'risk_tolerance': prefs.risk_tolerance,
            'min_investment_size': prefs.min_investment_size,
            'preferred_sectors': prefs.preferred_sectors,
            'notification_frequency': prefs.notification_frequency
        }), 200
    
    return jsonify({'error': 'Preferences not found'}), 404


@user_api_bp.route('/update-preferences', methods=['PUT'])
@login_required
def update_preferences():
    """Update user preferences."""
    try:
        data = request.get_json()
        
        prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
        if not prefs:
            return jsonify({'error': 'Preferences not found'}), 404
        
        # Update preferences
        prefs.theme = data.get('theme', prefs.theme)
        prefs.email_alerts = data.get('email_alerts', prefs.email_alerts)
        prefs.price_alerts = data.get('price_alerts', prefs.price_alerts)
        prefs.subscription_alerts = data.get('subscription_alerts', prefs.subscription_alerts)
        prefs.listing_alerts = data.get('listing_alerts', prefs.listing_alerts)
        prefs.risk_tolerance = data.get('risk_tolerance', prefs.risk_tolerance)
        prefs.min_investment_size = float(data.get('min_investment_size', prefs.min_investment_size))
        prefs.preferred_sectors = data.get('preferred_sectors', prefs.preferred_sectors)
        prefs.notification_frequency = data.get('notification_frequency', prefs.notification_frequency)
        prefs.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Preferences updated: {current_user.username}")
        return jsonify({'status': 'success', 'message': 'Preferences updated'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Preferences update error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
