# Spec: Registration

## Overview
This feature implements user registration (user sign-up) for the Spendly application. It allows new users to create accounts by entering their name, email, and password. The system validates the inputs, hashes the password using `werkzeug.security` (to prevent storing plain text passwords), verifies that the email is not already registered, and saves the new user record in the SQLite database.

## Depends on
Step 1: Database Setup (`01-database-setup.md`)

## Routes
- `GET /register` — Renders the registration form page — public. If the user already has an active logged-in session, redirect them to the dashboard/home page instead of showing the form.
- `POST /register` — Processes registration form submission, validates input, inserts the user into the database, and redirects to the login page — public

## Database changes
No database changes. The existing `users` table schema (with `id`, `name`, `email`, `password_hash`, `created_at`) is sufficient.

## Templates
- **Create:** None
- **Modify:**
  - `templates/login.html` — Add a success alert container block to display a registration success message.
  - `templates/register.html` — Add a "confirm password" input field alongside name, email, and password. Ensure form inputs bind cleanly to the POST request, and display error messages in the `.auth-error` container.

## Files to change
- `app.py` — Add the `POST /register` endpoint, implement input validation, email uniqueness check, password hashing, database insertion, and session/redirect handling.
- `templates/login.html` — Display a success message if redirected after successful registration.
- `static/css/style.css` — Add `.auth-success` CSS styles using CSS variables (`--accent`, `--accent-light`, etc.).

## Files to create
- `tests/test_registration.py` — Automated tests to verify registration success, input validation, and duplicate email prevention.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash` / `check_password_hash`)
- Password must be at least 8 characters long
- Password and confirm-password fields must match, or registration fails with a clear error
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Input fields must be trimmed (whitespace removed) before validation and database insertion
- Email addresses must be handled case-insensitively (stored as lowercase and checked case-insensitively)
- Name max length: 100 characters. Email max length: 255 characters. Reject anything longer with a validation error.
- Use Flask's `flash()` with categories (`success` / `error`) to pass both validation errors and the post-redirect success message to templates — do not invent a separate mechanism.
- If the database insert fails due to a duplicate email (race condition where two identical emails are submitted near-simultaneously), catch the resulting database error and show the same "email already registered" message rather than a 500 error.
- Validation failures should re-render the registration page with a 200 status code (not redirect, not 400), showing the entered values (except passwords) and the relevant error message.

## Definition of done
- [ ] Submitting the registration form with valid, unique details creates a new user in the database.
- [ ] Passwords are stored securely in hashed format using `werkzeug.security.generate_password_hash`.
- [ ] Email input is handled case-insensitively (e.g., registering `User@Example.com` prevents registering `user@example.com`).
- [ ] Registration fails and shows a clear error message on the registration page if:
  - Any field (name, email, password, confirm password) is missing or contains only whitespace.
  - Email format is invalid.
  - Password is less than 8 characters long.
  - Password and confirm-password do not match.
  - Name exceeds 100 characters or email exceeds 255 characters.
  - Email address is already registered (including the race-condition case caught at the database level).
  - A logged-in user is redirected away from `/register` without seeing the form.
- [ ] On successful registration, the user is redirected to the login page (`/login`) with a success message indicating registration was successful.
- [ ] Success and error alerts are styled consistently with the UI using CSS variables in `style.css`.
- [ ] The registration test suite in `tests/test_registration.py` is implemented and passes successfully.