# Eve Buyback

Corp buyback tool — paste EVE items, get ISK quotes based on Jita buy prices.

## Run

```bash
docker compose up
```

Open `http://localhost:8000`

### Local dev (without Docker)

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Run tests with `pytest`.

## Config

Copy `.env.example` to `.env` and fill in `JANICE_API_KEY` before running.

| Variable | Default | Description |
|---|---|---|
| `JANICE_API_KEY` | *(required)* | API key for the Janice pricing service |
| `BUYBACK_PERCENTAGE` | `80` | % of Jita buy price offered |
| `ALLOWED_CATEGORIES` | *(empty = nothing priced)* | Comma-separated EVE categories to accept |
| `FIXED_PRICES` | *(empty)* | Comma-separated `Item Name:price` pairs that override the Jita-based price with a flat ISK price, regardless of category |

**Example:**
```
ALLOWED_CATEGORIES=Ship,Asteroid,Material,Planetary Commodities,Reaction,Subsystem,Deployable,Ancient Relics,Decryptors
BUYBACK_PERCENTAGE=80
FIXED_PRICES=Heavy Water:500,Liquid Ozone:120
```

Pastes are capped at 200 items per request.
