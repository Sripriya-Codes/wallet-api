# Wallet API POC

A small wallet API that shows safe money transfers using Django 6, Django Ninja, JWT, database transactions and idempotency.

## Tech Stack

- **Django 6**: web framework and ORM
- **Django Ninja**: fast API layer with auto Swagger docs
- **PyJWT**: JWT token creation and verification
- **PostgreSQL (Prisma Postgres)**: database
- **python-dotenv, dj-database-url**: config from `.env`

## How It Works

**JWT authentication**
- Login returns a short-lived access token (15 min) and a refresh token (7 days).
- Protected endpoints read the `Authorization: Bearer <token>` header and verify it.
- No token or an invalid token gives 401.

**Database transactions**
- A transfer runs inside `transaction.atomic()`, so the debit and credit happen together or not at all.
- `select_for_update()` locks both wallets, so two transfers can't overspend.
- If anything fails midway, everything rolls back.

**Idempotency**
- The client sends an `Idempotency-Key` header with each transfer.
- The server saves the key, request hash and response in the database.
- A retry with the same key and body returns the saved response, so money is never debited twice.
- The same key with a different body gives 422.

## Endpoints

| Method | URL | Purpose |
|---|---|---|
| POST | /api/auth/register | Create user and wallet |
| POST | /api/auth/login | Get JWT tokens |
| POST | /api/auth/refresh | Get a new access token |
| GET | /api/wallet/me | View balance |
| POST | /api/wallet/transfer | Send money (needs Idempotency-Key) |

## Run Locally

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Create a `.env` file with `SECRET_KEY`, `JWT_SECRET`, `DEBUG` and `DATABASE_URL`.

Swagger UI: http://127.0.0.1:8000/api/docs

## Testing

Run `python test_poc.py` while the server is running. It tests JWT, transfers, replay, rollback and concurrency.