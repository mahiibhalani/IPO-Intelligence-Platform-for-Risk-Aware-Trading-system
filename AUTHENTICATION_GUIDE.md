# Authentication & User Features - IPO Intelligence Platform

## Overview
The platform now includes a complete authentication system with user accounts, personalized features, and decision tracking for IPO investments.

---

## 🔐 Authentication System

### Registration
**Route:** `/auth/register`

**Features:**
- Email validation and uniqueness check
- Strong password requirements (8+ chars, uppercase, lowercase, number)
- Username validation (4-20 chars, alphanumeric + underscore)
- Risk tolerance preference selection
- Terms of service acceptance

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

### Login
**Route:** `/auth/login`

**Features:**
- Login with username or email
- "Remember me" functionality
- Session persistence
- Failed login tracking

### Security
- Passwords hashed with Werkzeug (PBKDF2 with SHA256)
- CSRF protection via Flask-Login
- Secure session management
- Optional email recovery

---

## 👤 User Profile & Dashboard

### Profile Page
**Route:** `/auth/profile`

**Sections:**
1. **Overview Tab**
   - Statistics dashboard (saved IPOs, applied IPOs, watchlist, portfolio)
   - Recent activity feed
   - Quick actions

2. **Saved IPOs Tab**
   - Star/pin IPOs for future reference
   - Organized cards with IPO details
   - Quick access to full analysis
   - Batch management

3. **Applied IPOs Tab**
   - Track all apply/hold/avoid decisions
   - AI score vs user score comparison
   - Application status tracking
   - Quantity tracking for applications

4. **Watchlist Tab**
   - Monitor IPOs before listing
   - Price targets and return expectations
   - Pre-listing tracking
   - Performance alerts

5. **Portfolio Tab**
   - Track allotted IPOs
   - Entry price, current price tracking
   - P&L calculation
   - Investment metrics

6. **Settings Tab**
   - Alert preferences
   - Risk tolerance adjustment
   - Preferred sectors selection
   - Notification frequency
   - Password management
   - Account deletion option

---

## 📊 User Features

### 1. Save/Star IPOs
**API:** `POST /api/user/save-ipo`

Save IPOs for later review and comparison.

```javascript
{
  "ipo_id": "gsp",
  "company_name": "GSP Crop Science",
  "sector": "Agriculture",
  "price_band": "₹304-320",
  "issue_size": 286,
  "notes": "Interesting sector, good fundamentals"
}
```

### 2. Apply Decisions
**API:** `POST /api/user/apply-decision`

Record your investment decision for an IPO.

```javascript
{
  "ipo_id": "gsp",
  "company_name": "GSP Crop Science",
  "decision": "Apply",      // Apply, Hold, Avoid, Strong Apply, Strong Avoid
  "ai_score": 7.2,
  "user_score": 8.0,
  "quantity": 50,
  "notes": "Good growth prospect"
}
```

**Decision Levels:**
- **Strong Apply** - Excellent opportunity, invest if possible
- **Apply** - Good opportunity, consider applying
- **Hold** - Neutral, wait for more information
- **Avoid** - Weak opportunity, skip
- **Strong Avoid** - Poor opportunity, not recommended

### 3. Watchlist Management
**API:** `POST /api/user/add-to-watchlist`

Monitor IPOs from application to listing and beyond.

```javascript
{
  "ipo_id": "gsp",
  "company_name": "GSP Crop Science",
  "listing_price_target": 350,
  "target_return": 15.0,
  "notes": "Expecting 15% uplift on listing"
}
```

### 4. Portfolio Tracking
**API:** `POST /api/user/update-portfolio-ipo`

Track allotted IPOs and monitor performance.

```javascript
{
  "ipo_id": "gsp",
  "company_name": "GSP Crop Science",
  "listing_date": "2024-04-10",
  "listing_price": 340,
  "quantity_allotted": 50,
  "application_price": 320,
  "current_price": 355,
  "investment_amount": 16000
}
```

### 5. User Preferences
**API:** `PUT /api/user/update-preferences`

Customize your trading profile and alerts.

```javascript
{
  "theme": "dark",
  "risk_tolerance": "moderate",
  "email_alerts": true,
  "price_alerts": true,
  "subscription_alerts": true,
  "listing_alerts": true,
  "min_investment_size": 50,
  "preferred_sectors": "Technology,Finance,Healthcare",
  "notification_frequency": "daily"
}
```

---

## 🗄️ Database Schema

### Users Table
```
- id (Primary Key)
- username (Unique)
- email (Unique)
- password_hash
- first_name
- last_name
- created_at
- updated_at
- is_active
```

### SavedIPO Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- ipo_id
- company_name
- sector
- price_band
- issue_size
- saved_at
- status
- notes
```

### AppliedIPO Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- ipo_id
- company_name
- decision (Apply/Hold/Avoid)
- ai_score
- user_score
- applied_at
- application_status (pending/applied/allotted/rejected)
- quantity
- notes
```

### Watchlist Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- ipo_id
- company_name
- added_at
- listing_price_target
- target_return
- notes
```

### UserPreferences Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- theme
- email_alerts
- price_alerts
- subscription_alerts
- listing_alerts
- risk_tolerance
- min_investment_size
- preferred_sectors
- notification_frequency
```

### PortfolioIPO Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- ipo_id
- company_name
- listing_date
- listing_price
- quantity_allotted
- application_price
- current_price
- investment_amount
- current_value
- notes
```

---

## 🔗 API Endpoints Summary

### Authentication
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login user |
| `/auth/logout` | GET | Logout user |
| `/auth/profile` | GET | View user profile |
| `/auth/edit-profile` | POST | Update profile |
| `/auth/change-password` | POST | Change password |
| `/auth/delete-account` | POST | Delete account |

### User Features
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/save-ipo` | POST | Save IPO |
| `/api/user/unsave-ipo/<id>` | DELETE | Remove saved IPO |
| `/api/user/is-saved/<id>` | GET | Check if saved |
| `/api/user/apply-decision` | POST | Record decision |
| `/api/user/get-decision/<id>` | GET | Get decision |
| `/api/user/add-to-watchlist` | POST | Add to watchlist |
| `/api/user/remove-from-watchlist/<id>` | DELETE | Remove from watchlist |
| `/api/user/get-saved-ipos` | GET | List saved IPOs |
| `/api/user/get-watchlist` | GET | Get watchlist |
| `/api/user/get-decisions` | GET | Get all decisions |
| `/api/user/update-portfolio-ipo` | POST | Update portfolio |
| `/api/user/get-preferences` | GET | Get preferences |
| `/api/user/update-preferences` | PUT | Update preferences |

---

## 🎯 Usage Examples

### 1. Register and Login
```bash
# Register
POST /auth/register
{
  "first_name": "John",
  "email": "john@example.com",
  "username": "john_trader",
  "password": "SecurePass123",
  "risk_tolerance": "moderate"
}

# Login
POST /auth/login
{
  "username": "john_trader",
  "password": "SecurePass123",
  "remember": true
}
```

### 2. Save and Track IPO
```bash
# Save IPO
POST /api/user/save-ipo
{
  "ipo_id": "gsp",
  "company_name": "GSP Crop Science",
  "sector": "Agriculture"
}

# Record decision
POST /api/user/apply-decision
{
  "ipo_id": "gsp",
  "decision": "Apply",
  "user_score": 8.0,
  "quantity": 50
}

# Add to watchlist
POST /api/user/add-to-watchlist
{
  "ipo_id": "gsp",
  "listing_price_target": 350,
  "target_return": 15.0
}
```

### 3. View Analytics
```bash
# Get all saved IPOs
GET /api/user/get-saved-ipos

# Get all decisions
GET /api/user/get-decisions

# Get watchlist
GET /api/user/get-watchlist
```

---

## 🔄 Access Control

### Protected Routes
All routes starting with `/auth/` (except login/register) and `/api/user/` require authentication.

**Login required for:**
- User profile
- Save/star IPOs
- Track decisions
- Watchlist management
- Portfolio tracking
- Preference management

**Unprotected routes:**
- Public IPO analysis
- Dashboard (limited data)
- Market overview
- News feed

---

## 🛡️ Security Features

1. **Password Security**
   - PBKDF2 hashing with SHA256
   - Salt generation per user
   - Strong password enforcement

2. **Session Management**
   - Flask-Login integration
   - Secure session tokens
   - Session expiration
   - Remember-me functionality

3. **Data Privacy**
   - User data isolation
   - Database constraints
   - Cascade delete protection

4. **Validation**
   - Email format validation
   - Username format validation
   - Password strength validation
   - Input sanitization

---

## 📧 Future Enhancements

1. **Email Alerts**
   - IPO application deadlines
   - Price threshold alerts
   - Listing day notifications
   - Performance updates

2. **Social Features**
   - Compare decisions with other traders
   - Share analysis
   - Community rankings

3. **Performance Analytics**
   - Track portfolio returns
   - Win/loss ratio
   - Decision accuracy
   - Risk-adjusted returns

4. **Integration**
   - Broker API integration
   - Real-time price updates
   - Broker order placement
   - Dividend tracking

---

## 📝 Files Created

1. **src/models.py** - Database models
2. **src/auth.py** - Authentication routes
3. **src/user_api.py** - User features API
4. **templates/login.html** - Login page
5. **templates/register.html** - Registration page
6. **templates/profile.html** - User profile dashboard

---

## ✅ Quick Start

1. Start Flask server: `python flask_app.py`
2. Navigate to http://localhost:5000/auth/register
3. Create account and set preferences
4. Browse IPOs and star/save favorites
5. Record apply decisions
6. Add IPOs to watchlist
7. Track portfolio performance
8. View profile analytics

---

**Status:** ✅ Authentication system fully implemented and ready to use!
