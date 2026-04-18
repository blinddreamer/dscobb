# Eve Buyback

Corp buyback tool — paste EVE items, get ISK quotes based on Jita buy prices.

## Run

```bash
docker compose up
```

Open `http://localhost:8000`

## Config

| Variable | Default | Description |
|---|---|---|
| `BUYBACK_PERCENTAGE` | `90` | % of Jita buy price offered |
| `ALLOWED_CATEGORIES` | *(empty = nothing priced)* | Comma-separated EVE categories to accept |

**Example:**
```
ALLOWED_CATEGORIES=Ship,Asteroid,Material,Planetary Commodities,Reaction,Subsystem,Deployable,Ancient Relics,Decryptors
BUYBACK_PERCENTAGE=90
```
