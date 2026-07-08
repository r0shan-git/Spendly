# Spec: Login and Logout

## Overview
This feature implements user authentication flow for Spendly. Users who registered in Step 02 can now sign in with their email and password, maintain a persistent session while browsing, and sign out when finished. The navbar dynamically reflects the authentication state — showing "Sign in / Get started" for guests and the user's name plus a "Sign out" link for logged-in users. A `login_required` decorator protects future authenticated routes (profile, expenses) from anonymous access.

## Depends on
- **Step 01 — Database Setup** (users table, `get_db()`, `init_db()`, `seed_db()`)
- **Step 02 — Registration** (POST `/register` creates users with hashed passwords)

## Routes

- `POST /login` — Validates email/password, creates a session, redirects to landing — **public**
- `GET /logout` — Clears the session and redirects to landing — **logged-in**

The existing `GET /login` route will be updated to handle redirect-after-login and to block already-authenticated users.

## Database changes
No database changes. The existing `users` table already contains `id`, `name`, `email`, and `password_hash` columns needed for authentication.

## Templates

- **Modify:** `templates/login.html`
  - Pre-fill the email field on validation failure (pass `email` context variable)
  - Display flash messages for errors and success (already partially wired)
- **Modify:** `templates/base.html`
  - Conditionally render navbar links based on `session['user_id']`:
    - **Logged out:** Show "Sign in" and "Get started" (current behaviour)
    - **Logged in:** Show "Hi, {name}" greeting and a "Sign out" link

## Files to change

- [app.py](file:///D:/claude/claude%20project/expense-tracker/app.py)
  - Import `check_password_hash` from `werkzeug.security`
  - Add `login_required` decorator using `functools.wraps`
  - Update `GET /login` to redirect authenticated users away
  - Implement `POST /login` with validation, password check, and session creation
  - Implement `GET /logout` to clear session and redirect
  - Store `user_id` and `user_name` in `session` on successful login
- [templates/base.html](file:///D:/claude/claude%20project/expense-tracker/templates/base.html)
  - Update `.nav-links` to conditionally show logged-in vs logged-out state
- [templates/login.html](file:///D:/claude/claude%20project/expense-tracker/templates/login.html)
  - Add `value="{{ email }}"` to the email input for field persistence on error

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug` (already installed) provides `check_password_hash`.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQL via `sqlite3` only
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords checked with `werkzeug.security.check_password_hash`
- Use CSS variables from `style.css` — never hardcode hex/colour values
- All templates extend `base.html`
- Use `functools.wraps` when creating the `login_required` decorator
- Store only `user_id` and `user_name` in `flask.session` — never store passwords or hashes
- The `login_required` decorator must flash a message and redirect to `/login` when the user is not authenticated
- Close database connections in a `finally` block or use try/finally patterns
- Use `session.clear()` in logout to destroy the entire session
- Currency display must use Indian Rupee (₹) — never US Dollars ($)
- Keep the generic error message "Invalid email or password." for both wrong-email and wrong-password cases (avoid user enumeration)

## Definition of done

- [ ] Visiting `/login` while logged out renders the sign-in form
- [ ] Visiting `/login` while logged in redirects to `/` (landing page)
- [ ] Submitting the login form with a valid email/password logs the user in and redirects to `/`
- [ ] Submitting the login form with an invalid email shows "Invalid email or password."
- [ ] Submitting the login form with a wrong password shows "Invalid email or password."
- [ ] Submitting the login form with empty fields shows "All fields are required."
- [ ] After login, the navbar shows "Hi, {name}" and a "Sign out" link instead of "Sign in" / "Get started"
- [ ] Clicking "Sign out" clears the session and redirects to `/`
- [ ] After sign out, the navbar reverts to showing "Sign in" and "Get started"
- [ ] The `login_required` decorator redirects unauthenticated users to `/login` with a flash message
- [ ] Registering a new account (Step 02) and immediately logging in with those credentials works end-to-end
- [ ] The email field retains its value when the login form is re-rendered after a validation error
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
