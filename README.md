# FutbolGo Backend

Django REST API + Telegram bot for the FutbolGo pitch-booking app. See
`/Users/dovudbek/.claude/plans/humming-knitting-liskov.md` for the full design.

## Apps

- `apps/accounts` — User, OTP + Telegram-link auth, friends
- `apps/stadiums` — venues, slot templates, reviews, favorites
- `apps/bookings` — Match/Booking/MatchResult, join/cancel pricing logic
- `apps/wallet` — Wallet, Transaction, TopUpRequest (admin-approved), PaymentMethod catalog
- `apps/gamification` — skill ratings (radar chart), badges, leaderboard
- `apps/notifications` — Telegram DM sender used by all the above
- `bot/` — aiogram bot (not a Django app): `/start <token>` deep-link handler + scheduled reminders

## Local dev (Docker)

```bash
cp .env.example .env          # fill in TELEGRAM_BOT_TOKEN once you have one
docker compose up --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_catalog       # amenities, payment methods, badges, exchange rate
docker compose exec web python manage.py generate_matches   # expand StadiumSlotTemplates into bookable Match rows
```

API: http://localhost:8000/api — docs at `/api/docs`, admin at `/admin`.

## Local dev (no Docker)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # point POSTGRES_HOST at a local Postgres
python manage.py migrate
python manage.py seed_catalog
python manage.py runserver 8000
```

With `OTP_DEBUG_MODE=True` (the `.env.example` default), `/api/auth/otp/request`
returns the code directly in the response so you can build/test the frontend
before a real bot token exists. Set it `False` once `TELEGRAM_BOT_TOKEN` is live.

## Telegram bot

```bash
python manage.py runbot            # polling + reminder/expiry scheduler
python manage.py setup_bot_menu    # registers the Mini App menu button via BotFather API
```

## Adding new stadium inventory

Create `Stadium` + `StadiumSlotTemplate` rows via `/admin`, then run
`generate_matches --days 14` (cron/manually) to expand templates into concrete,
bookable `Match` rows for the next N days.
