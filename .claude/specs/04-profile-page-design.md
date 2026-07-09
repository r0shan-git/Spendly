# Spec: Profile Page Design

## Overview
This feature implements a fully functional, premium-styled profile page for authenticated Spendly users. Once a user is logged in, they can navigate to `/profile` to view their account details (name, email, member-since date) and a summary snapshot of their expense activity (total expenses logged, total amount spent in INR). The page is protected by the `login_required` decorator so anonymous users are redirected to `/login`. The design uses the existing Spendly CSS design system and extends `base.html`, adding a rich, visually premium layout consistent with the app's aesthetic.

## Depends on
- **Step 01 — Database Setup** (`get_db()`, `users` table with `created_at`, `expenses` table)
- **Step 02 — Registration** (user accounts exist in the database)
- **Step 03 — Login and Logout** (`login_required` decorator, `session['user_id']` and `session['user_name']`)

## Routes

- `GET /profile` — Fetches the logged-in user's account details and expense summary from the database, then renders the profile template — **logged-in**
  - On success: `200`, renders `profile.html`
  - If `session['user_id']` no longer matches a row in `users` (e.g. account deleted mid-session): clear the session and redirect to `/login` with a flash message, rather than raising a 500 or rendering `None` values

## Database changes
No new tables or columns are required. The existing schema already provides all necessary data:
- `users.id`, `users.name`, `users.email`, `users.created_at` — for account info
- `expenses.user_id`, `expenses.amount` — for aggregated spending stats (COUNT, SUM)

### Query notes
- Use a single query for the aggregate to avoid N+1 lookups:
  ```sql
  SELECT COUNT(id) AS expense_count, COALESCE(SUM(amount), 0) AS total_spent
  FROM expenses
  WHERE user_id = ?
  ```
- **`COALESCE` is required.** `SUM()` over zero rows returns `NULL` in SQLite, not `0`. Without it, a brand-new user with no expenses will crash the template on the currency filter or render "₹None."

## Templates

- **Create:** `templates/profile.html`
  - Extends `base.html`
  - Displays a premium profile card with:
    - User avatar section (initials-based avatar generated from the user's name)
    - Full name and email address
    - Member-since date (formatted from `created_at`)
    - Expense snapshot: total number of expenses logged and total amount spent (₹)
  - Includes an "Edit Profile" placeholder button (disabled/coming-soon state) for future extensibility
  - Responsive layout using CSS grid/flex consistent with existing design system
  - **Empty state:** when `expense_count == 0`, the stats cards should show "0" and "₹0" gracefully (not blank, not an error) — consider a small subtext like "No expenses logged yet" under the stats grid, with a link back to the add-expense page if one exists
  - **Escaping:** rely on Jinja2's autoescaping (on by default in Flask) for `name` and `email` — do not mark anything `|safe` on this page, since name is user-supplied at registration

## Files to change

- [`app.py`](file:///D:/claude/claude%20project/expense-tracker/app.py)
  - Replace the placeholder `GET /profile` stub with a full implementation:
    - Apply `@login_required` decorator
    - Query the database for the current user's `name`, `email`, `created_at`
    - Aggregate the user's expense data: `COUNT(id)` and `SUM(amount)` from the `expenses` table (see query note above for the `NULL`-safe form)
    - Compute the initials for the avatar server-side (see Avatar logic below) and pass as a template variable rather than doing string slicing in Jinja
    - Pass all context variables to `profile.html`
  - Close all database connections in a `try/finally` block
  - If the user row is missing (deleted account, stale session), clear the session and redirect to `/login` instead of letting a `None` propagate into the template

### Avatar logic (server-side, in `app.py`)
- Split `name` on whitespace, filter out empty strings
- One word (e.g. "Priya") → first letter, uppercased: `"P"`
- Two or more words (e.g. "Priya Sharma") → first letter of first and last word: `"PS"`
- Guard against a name that's empty or only whitespace (shouldn't happen if registration validates, but don't let it crash the page) — fall back to `"?"`

- [`static/css/style.css`](file:///D:/claude/claude%20project/expense-tracker/static/css/style.css)
  - Add profile page CSS rules under a clearly marked `/* === Profile Page === */` comment block:
    - `.profile-container` — centered layout wrapper with max-width constraint
    - `.profile-card` — glassmorphism-style card with border, backdrop blur, and shadow using existing CSS variables
    - `.profile-avatar` — circular initials avatar using `var(--accent)` background
    - `.profile-stats` — grid layout for the expense snapshot cards
    - `.stat-card` — individual stat card with icon, value, and label
    - `.profile-stats-empty` — small muted subtext style for the zero-expenses empty state
    - Responsive breakpoints for mobile screens
    - `backdrop-filter` has patchy support on older browsers — add a solid-background fallback (e.g. `background: var(--surface)` before the blur rule) so the card isn't invisible/transparent where blur isn't supported

## Files to create

- `templates/profile.html` — New Jinja2 template for the user profile page

## New dependencies
No new dependencies. All required libraries (`flask`, `sqlite3`, `werkzeug`) are already installed.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQL via `sqlite3` only
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords hashed with werkzeug — do not expose `password_hash` in any template context variable
- Use CSS variables — never hardcode hex values (use `var(--ink)`, `var(--accent)`, `var(--surface)`, etc.)
- All templates extend `base.html`
- Apply `@login_required` to `GET /profile` — anonymous requests must be redirected to `/login`
- Close database connections in a `finally` block
- Currency must be displayed in Indian Rupee (₹) — never use US Dollars ($)
  - Format the amount using the Indian digit-grouping convention (lakh/crore commas — e.g. `₹1,23,456`), not the Western `123,456` grouping, since this is a jarring inconsistency for INR. Implement as a small Jinja filter or helper function rather than relying on Python's default `{:,}` formatting, which uses Western grouping.
  - Round/display to 2 decimal places consistently (e.g. `₹1,234.50`, not `₹1234.5`)
- The initials avatar must be generated server-side (pass first letter(s) of name to template) or via pure CSS/JS — no third-party avatar services
- The `created_at` date should be formatted in a human-readable form (e.g. "July 2026") within the template using Jinja2 filters
- The "Edit Profile" button should be visually present but marked disabled/coming-soon — do not add a route or form for it in this step
  - Use a real `<button disabled>` (not a styled `<a>` or `<div>`) so it's not keyboard-focusable and screen readers announce it as unavailable
- Keep JavaScript minimal and DOMContentLoaded-scoped if needed
- Handle the zero-expenses case explicitly (see Empty state above) — this is the state a brand-new user will actually see first, so it shouldn't look broken or like an error

## Definition of done

- [ ] Visiting `/profile` while logged out redirects to `/login` with a flash message
- [ ] Visiting `/profile` while logged in renders the profile page without errors
- [ ] The profile page correctly displays the logged-in user's full name
- [ ] The profile page correctly displays the logged-in user's email address
- [ ] The profile page correctly displays the member-since date derived from `users.created_at`
- [ ] The total number of expenses logged is accurately queried and displayed
- [ ] The total amount spent (₹) is accurately queried and displayed using `SUM(amount)` from the `expenses` table, formatted with Indian digit grouping and 2 decimal places
- [ ] A user with zero expenses sees a clean "0 / ₹0" empty state, not a crash or blank field
- [ ] The initials avatar renders correctly for single-word names, multi-word names, and (as a defensive check) doesn't crash on an edge-case empty name
- [ ] The "Edit Profile" button is a real disabled `<button>` — visible, non-interactive, no working form or route
- [ ] The page is responsive and looks correct on both desktop and mobile screen widths
- [ ] The `.profile-card` remains visually readable in browsers without `backdrop-filter` support
- [ ] All colours and spacing use CSS variables — no hardcoded hex values in new CSS rules
- [ ] No `|safe` filters are used on user-supplied fields (name, email) — autoescaping stays on
- [ ] `password_hash` is never passed into the template context
- [ ] The demo user (`demo@spendly.com` / `demo123`) profile page shows their 8 seeded expenses and correct total amount
- [ ] Database connections are always closed (no connection leaks), including on the error path where the user row is missing