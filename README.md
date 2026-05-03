# EdgeLab Sports Intelligence

A deployable sports research dashboard inspired by AI sports-analysis tools. It supports NFL, MLB, NBA, NHL, and MMA with:

- Research chat and natural-language stats questions
- Insights feed
- Player/fighter profiles
- Custom player, fighter, or team prop entries saved in each user's browser
- Rankings
- Parlay-style research card builder
- FastAPI `/api` engine with simulation, edge, confidence, sharp filter, and first-action probabilities
- Typed prediction lab for any player, team, fighter, or prop market
- Optional live event/odds provider support with `ODDS_API_KEY`
- Provider health/admin status endpoints
- Prediction analytics, recent prediction history, and win/loss/push grading
- Vegas-style market intelligence: power ratings, true probability, fair odds, vig awareness, CLV watch, risk tiers, and alternate lines
- Playing-environment notes for weather, roof, turf/grass/ice/court, venue, travel/rest context, and matchup/coaching tendencies
- 24-hour automatic roster/stat/context refresh worker plus manual admin refresh
- News/injury context hooks for late-breaking updates
- User accounts, saved cards, watchlists, alerts, and database-backed prediction history
- CLV tracking, settlement workflow placeholder, EV math, data validation, and pro-model layer explanations
- Event time/location cards for games and fights when live event feeds are connected
- Day/night mode saved per browser

This app is for entertainment and research. It is not gambling, betting, or financial advice.

If gambling is causing problems for you or someone you know in the U.S., the National Council on Problem Gambling lists free confidential help through the National Problem Gambling Helpline: call `1-800-MY-RESET`, text `800GAM`, or use chat at `https://www.ncpgambling.org/chat/`.

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Add Different Players Or Teams

Open the **Players** tab, fill out the add form, and click **Add to slate**. The new entry is saved in that browser and immediately appears in:

- Research chat
- Insights
- Player/fighter profiles
- Rankings
- Parlay builder
- Engine tab local fallback

## Live Data Keys

The app works without keys using built-in team/market catalogs and model projections. For live event and odds access, add an environment variable in Render:

```text
ODDS_API_KEY=your_key_here
```

The current integration supports The Odds API v4 event and odds endpoints. API keys are private and should only be entered in Render's Environment settings, never committed to GitHub.

For player stats, rosters, injuries, and news context, add:

```text
SPORTSDATA_API_KEY=your_key_here
```

For weather and environment upgrades, add either:

```text
WEATHER_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
```

For persistent users, saved cards, alerts, analytics, and CLV history on Render, add a Render Postgres database and connect its:

```text
DATABASE_URL=your_render_postgres_url
```

Useful live/admin endpoints:

```text
/api/admin/status
/api/analytics
/api/insights
/api/rankings
/api/context/NBA?q=player-name
/api/data-freshness
/api/market-sources
/api/responsible-use
/api/events/NBA
/api/cards
/api/alerts
```

## Share With Friends

Deploy the folder to a Python web host such as Render, Railway, Fly.io, or a VPS.

For Render:

1. Push this folder to a GitHub repository.
2. In Render, choose **New +** then **Blueprint** and select the repository.
3. Render will read `render.yaml`, install the requirements, start the app, and check `/health`.
4. Share the public URL Render gives you.

Manual Render setup also works:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

The included `Procfile` and `Dockerfile` are there for hosts that detect either style automatically.
