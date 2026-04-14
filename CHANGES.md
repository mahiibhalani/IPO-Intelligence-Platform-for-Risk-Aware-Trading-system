# 📋 CHANGES LOG — IPO Intelligence Platform

Auto-updated change log for all UI, backend, and template modifications.

---

## 🗓️ 2026-04-04

---

### ✅ [FIX] Logout Button Not Visible in Navbar Dropdown
**File:** `templates/base.html`

**Problem:** The dropdown menu was being clipped by the navbar's overflow, making the Logout item invisible.

**Changes:**
- Added `overflow: visible !important` and `z-index: 1050` to `.navbar`
- Set `z-index: 9999`, `position: absolute`, `top: calc(100% + 8px)` on `.dropdown-menu-dark`
- Added rounded corners, box-shadow, and tighter padding to the dropdown
- Added `.logout-item` class with distinct **red color** (`#ff6b6b`) and red hover effect
- Applied `.logout-item` class to the Logout `<a>` tag in the navbar HTML

---

### ✅ [FIX] Edit Profile Button — Missing Template Error
**File:** `templates/edit_profile.html` *(created)*

**Problem:** Clicking "Edit Profile" threw a `TemplateNotFound` error because `edit_profile.html` did not exist.

**Changes:**
- Created full `edit_profile.html` with:
  - Pre-filled form for First Name, Last Name, Email
  - Disabled (read-only) Username field
  - Error and success flash message display
  - Back to Profile button
  - "Change Password" quick-link
  - Dark glassmorphism styling matching platform design

---

### ✅ [FIX] Change Password — Missing Template
**File:** `templates/change_password.html` *(created)*

**Problem:** `/auth/change-password` route rendered a non-existent template.

**Changes:**
- Created `change_password.html` with:
  - Current password field
  - New password field with **live strength meter** (Weak / Fair / Good / Strong)
  - Password rules checklist (length, uppercase, lowercase, digit)
  - Confirm password with match indicator
  - Show/Hide password toggle for all fields
  - Submit button disabled hint when invalid

---

### ✅ [FIX] Forgot Password — Missing Template
**File:** `templates/forgot_password.html` *(created)*

**Problem:** `/auth/forgot-password` route rendered a non-existent template.

**Changes:**
- Created `forgot_password.html` with:
  - Centered glassmorphism card
  - Email address input
  - Back to Login / Create Account links
  - Success/Error message display

---

### ✅ [FEATURE] Saved IPOs — Rich Features & UI Overhaul
**Files:**
- `templates/profile.html` — Saved IPOs tab completely rewritten
- `src/user_api.py` — Two new API endpoints added

#### Backend (`src/user_api.py`)
| Endpoint | Method | Description |
|---|---|---|
| `/api/user/update-saved-note/<ipo_id>` | `PATCH` | Save/update personal note on a saved IPO |
| `/api/user/bulk-remove-saved` | `DELETE` | Remove multiple saved IPOs in one request |

Also enhanced `/api/user/get-saved-ipos` to return `price_band`, `issue_size`, `notes`, `saved_at`.

#### Frontend (`templates/profile.html` — Saved IPOs tab)
| Feature | Description |
|---|---|
| 🔍 Live Search | Filter cards by company name or sector in real-time |
| 📊 Sort | Newest First / Oldest First / A→Z / Z→A |
| 🏷️ Sector Filter | Auto-populated dropdown with unique sectors |
| ✅ Select All + Bulk Remove | Per-card checkbox + bulk remove button with count |
| 📝 Inline Notes | Pen icon to write/edit notes per card — saved to DB instantly |
| 👁️ Move to Watchlist | One-click button to add IPO to watchlist |
| 📈 View Analysis | Direct link to IPO analysis page |
| ⭐ Remove | Removes card with smooth 300ms fade-out (no page reload) |
| 📥 Export CSV | Downloads all visible saved IPOs as `.csv` file |
| 🔔 Toast Notifications | Green/red animated toasts for every action |
| 🎨 Redesigned Cards | Company letter-avatar, sector badge, price/size/date pill chips |
| 🔢 Count Badge | Live badge showing current saved IPO count |

---

## 📁 Files Modified This Session

| File | Type | Change |
|---|---|---|
| `templates/base.html` | Modified | Logout dropdown fix |
| `templates/edit_profile.html` | **Created** | New edit profile page |
| `templates/change_password.html` | **Created** | New change password page |
| `templates/forgot_password.html` | **Created** | New forgot password page |
| `templates/profile.html` | Modified | Saved IPOs tab overhaul |
| `src/user_api.py` | Modified | 2 new API endpoints, enhanced get-saved-ipos |

---

> 📌 **Note:** Add new entries above this line each session in the format shown above.
