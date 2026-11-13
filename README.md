# Wallet API

A wallet API that demonstrates safe money transfers using Django 6, Django Ninja, JWT authentication, database transactions and idempotency keys.

## Features

- Register and login with JWT access and refresh tokens
- A wallet is created automatically for every new user
- Send money between users with all-or-nothing transactions
- Row-level locking so concurrent transfers cannot overspend
- Idempotency keys so a retried request never debits twice
- Interactive Swagger UI documentation
- Automated tests with pytest
- Django admin panel for wallets, transfers and idempotency keys

## Tech Stack

- **Django 6**: web framework and ORM
- **Django Ninja**: fast API layer with Pydantic validation and auto Swagger docs
- **PyJWT**: JWT token creation and verification
- **PostgreSQL (Prisma Postgres)**: database
- **pytest, pytest-django**: automated tests
- **python-dotenv, dj-database-url**: configuration from `.env`

## How It Works

**JWT authentication**
- Login returns a short-lived access token (15 minutes) and a refresh token (7 days).
- Each token has a `type` claim, so a refresh token cannot be used as an access token.
- Protected endpoints read the `Authorization: Bearer <token>` header and verify it.
- A missing or invalid token gives 401.

**Database transactions**
- Registration creates the user and wallet inside `transaction.atomic()`, so both exist or neither does.
- A transfer runs inside `transaction.atomic()`, so the debit, credit and transfer record happen together or not at all.
- `select_for_update()` locks both wallets, and rows are locked in `id` order to avoid deadlocks.
- A database `CheckConstraint` makes sure a balance can never go below zero.
- If anything fails midway, everything rolls back.

**Idempotency**
- The client sends an `Idempotency-Key` header with each transfer.
- The server saves the key, a hash of the request body and the response in the database.
- A retry with the same key and body returns the saved response (header `Idempotent-Replayed: true`), so money is never debited twice.
- The same key with a different body gives 422.
- The same key while the first request is still running gives 409.
- A unique constraint on `(user, key)` makes this safe even when two identical requests arrive at the same moment.

## Project Structure

```
walletapi/
├── config/            Django settings and URL routing
├── accounts/          Registration, login, refresh, JWT helpers
├── wallet/            Wallet, Transfer and IdempotencyKey models, transfer logic, tests
├── test_poc.py        End-to-end script that tests the running server
├── pytest.ini         pytest configuration
├── .env.example       Example environment variables
└── requirements.txt   Python dependencies
```

## API Endpoints

| Method | URL | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register | No | Create user and wallet |
| POST | /api/auth/login | No | Get access and refresh tokens |
| POST | /api/auth/refresh | No | Get a new access token |
| GET | /api/auth/me | JWT | Current user details |
| GET | /api/wallet/me | JWT | View balance |
| GET | /api/wallet/transfers | JWT | Last 20 transfers sent |
| POST | /api/wallet/transfer | JWT + Idempotency-Key header | Send money |

## Run Locally

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the values:

```
copy .env.example .env
```

Then:

```
python manage.py migrate
python manage.py runserver
```

- Swagger UI: http://127.0.0.1:8000/api/docs
- Admin panel: http://127.0.0.1:8000/admin (create a login with `python manage.py createsuperuser`)

## Testing

**Automated tests (pytest)**

```
pytest -v
```

The tests run on a temporary SQLite database, so they never touch the real database. They cover:

- Login, wrong password, missing token and refresh-token misuse
- Registration creating both user and wallet
- A normal transfer, insufficient funds, and rollback after a failure
- Idempotent replay, and the same key with a different body

SQLite ignores row locks, so the locking itself is checked by the end-to-end script below on real PostgreSQL.

**End-to-end script**

Start the server, then in a second terminal run:

```
python test_poc.py
```

It tests JWT protection, transfers, replay, rollback, insufficient funds and 5 parallel requests with the same key.

## Work Log

**13 Nov 2026**

- Built the Django 6 project with Django Ninja and connected it to Prisma Postgres
- Implemented JWT login with access and refresh tokens
- Implemented safe transfers using transactions and row locking
- Implemented idempotency keys with replay and conflict handling
- Tested all endpoints manually in Swagger UI
- Wrote the end-to-end test script `test_poc.py`
- Added automated tests with pytest
- Registered the models in the Django admin panel
- Added `.env.example`
- Wrote this README

## Known Limitations and Next Steps

- `simulate_failure` in the transfer request is a demo-only flag and should be removed
- Refresh tokens cannot be revoked yet
- Idempotency keys are never cleaned up
- Add a deposit endpoint and pagination for transfers
- Deploy the API and add a small frontend