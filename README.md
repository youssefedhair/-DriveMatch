# DriveMatch — AI Car Recommendation System for Egypt

Human–Machine Interface university project (UI refresh + expanded 64-car catalog): responsive React + FastAPI web app that recommends vehicles based on budget, passengers, lifestyle, driving conditions, fuel and transmission preferences.


## Photos and catalog update (64 cars)

The catalog and AI engine now include **64 vehicle models**. Each car has a `photo_query` entry and the React photo component looks for a matching photograph on **Wikimedia Commons** when a card appears on screen. Photos are requested over the internet and credited with a link to their Commons file page, which contains licensing and attribution information. No third-party API key is necessary. For model-name accuracy, only photo filenames containing both the brand and model tokens are displayed; if the service is blocked, offline, or no sufficiently matching image exists, the card displays a clearly labeled **Photo unavailable** state instead of an incorrect generic car photo. Year, generation, body trim and market specification of Commons images may differ from the demo data. Wikimedia photos have individual licenses: review their file pages before republishing.

**Important:** this is online, on-demand photo lookup, not 64 bundled or individually verified car photographs. To guarantee every photo in an offline university presentation, download and verify licensed photos for each model in advance and replace the dynamic lookup with a local `photo_url` per car. The existing offline `preview.html` remains a legacy demo and does not show new photos.

## What's new in the refreshed design

- Modern green-and-cream visual system, typography, cards, hover/focus feedback, more prominent calls to action, and responsive spacing.
- Dedicated **Sign In** (`/signin`) and **Sign Up** (`/signup`) pages retained.
- **Explore cars** section on the homepage: 64 catalog entries, model/brand search, Sedan/SUV/Hatchback filters, Show all / Show fewer, and account-linked favorites.
- Refreshed recommendation result cards and hero illustration, with the original FastAPI + scikit-learn scoring engine unchanged in approach and updated automatically for the expanded catalog.
- **The prices, trims, model years, and suitability ratings in `backend/cars.json` are illustrative estimates for an HMI coursework demo, not verified current listings.** Real-world availability and pricing must be checked with official dealerships. Sample market model reference pages: https://www.yallamotor.com/news/egypt-2026-car-market-pound-devaluation-import-rules-cars-worth-buying-55349 and https://www.contactcars.com/en/new-cars/chevrolet-optra.

The latest design changes require running the full React app; `frontend/preview.html` is a legacy simplified offline preview and does **not** reflect the new catalog or separate auth pages.

## Which file should I open?

- **Legacy quick preview (no setup):** double-click `frontend/preview.html`. This is an offline, standalone recommendation preview with rule-based scores, **not** the AI engine; sign-in/sign-up only work in the full React + backend app.
- **Full React + ML application:** do **not** double-click `frontend/index.html`. Vite must compile JSX and load imports. On Windows, run `START_BACKEND_WINDOWS.bat` and `START_FRONTEND_WINDOWS.bat` in separate windows, then open `http://localhost:5173`. The first run requires Node.js 20+, Python 3.10+, and an internet connection to install dependencies.
- The backend ML API runs at `http://localhost:8000/docs`.

## Run locally

Requirements: Node.js 20+, Python 3.10+.

**Terminal 1 — AI backend**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Web app**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. API docs: **http://localhost:8000/docs**.

## Separate Sign In and Sign Up pages

The **DriveMatch** header has **Sign in** and **Sign up** buttons leading to dedicated, bookmarkable pages: **http://localhost:5173/signin** and **http://localhost:5173/signup**. These are full pages, not modal popups. Each screen links to the other and offers Back to home. Browser back/forward navigation is supported. The account forms provide clear form labels, email validation, an 8-character minimum for new passwords, password visibility toggle, error feedback, and keyboard focus indicators. After sign-in the header greets the user and offers **Sign out**.

- **Real backend account registration and login** over FastAPI, not simulated browser-only login.
- The backend stores users and favorite cars in a **local SQLite database**, created automatically as `backend/drivematch.db` on first run.
- Passwords are salted and hashed using PBKDF2-HMAC-SHA256; plain-text passwords are not stored.
- A 7-day bearer token is kept in the **browser sessionStorage** and invalidated on sign-out. Saved cars persist for the account across logins.
- Guests can explore car recommendations, but clicking **Save** asks them to sign in.
- REST API docs show `/api/auth/signup`, `/api/auth/signin`, `/api/auth/me`, `/api/auth/signout`, and `/api/favorites`.

**University/demo scope:** for production use HTTPS, secure HttpOnly cookies with CSRF protection, login rate limiting, password recovery/email verification, and periodic session cleanup. Use the app on localhost for the university demo; do not expose this basic authentication server publicly.

## HMI presentation highlights

The interface illustrates discoverability (obvious navigation), visibility of system status (loading and errors), form validation, recognition rather than recall (choice cards), feedback for selected options, consistency of colors and actions, mobile adaptation, and support for keyboard navigation.

## How AI works

- **Unsupervised content-based machine learning**: scikit-learn `TfidfVectorizer` fits text features from car descriptions and tags. It uses cosine similarity between user intent and vehicle profiles.
- **Explainable weighted ranking** adds city/highway suitability, top priority, rough-road tolerance, parking ease, and remaining budget to the semantic relevance score.
- **Strict constraints** filter out models above budget, with insufficient passenger seating, or that violate fuel/transmission choices.
- Each match includes plain-language explanations. No third-party AI API keys required.
- This is a *real, runnable baseline ML model*, not an LLM nor a supervised model trained on real buyers' preferences. To improve quality, gather verified structured specification data, real user interaction labels and test performance with held-out examples. For advanced natural-language recommendations, add a multilingual embedding model and optionally an LLM for explanation generation.

## Important data disclaimer

`backend/cars.json` is a **curated illustrative demo dataset** with 64 Egypt-relevant vehicle nameplates, not verified live listings. Prices, suitability scores, variants, fuel type and configurations are demo assumptions. **Do not treat them as accurate current offers or vehicle specifications.** Confirm current price, dealer stock, trim, safety and fuel figures with official dealers before a purchasing decision.

For production, connect a licensed or permissioned Egypt-market inventory feed, record `price_updated_at`, dealer/trim IDs, and source links, and validate each price and spec. Prices often change rapidly in Egypt.

## Files

- `frontend/src/main.jsx`: React UI, 3-step questionnaire, results shortlist, saved cars
- `frontend/src/style.css`: responsive design
- `backend/main.py`: FastAPI endpoints and ML ranking logic
- `backend/cars.json`: illustrative model catalog

## API endpoints

- `GET /api/health` — model status
- `GET /api/cars` — demo catalog
- `POST /api/recommend` — recommend and explain matches

Sample:

```bash
curl -X POST http://localhost:8000/api/recommend -H 'Content-Type: application/json' -d '{"budget":1300000,"passengers":4,"usage":"city","priority":"economy","roads":"normal","parking":"easy","transmission":"Automatic","fuel":"Any","notes":"short daily commute"}'
```

## Production next steps

1. Replace demo data with regularly refreshed Egypt dealer listings, trim-level specs and actual availability.
2. Add bilingual Arabic/English UX, EGP financing and total ownership cost estimates.
3. Store anonymized feedback (clicks, saves, shortlisted cars) with consent, evaluate offline metrics like Precision@K and NDCG@K, and train a learning-to-rank model when labels are sufficient.
4. Add caching, rate limiting, tests, monitoring, data-provenance audit trail and stronger accessibility checks.

## Routing notes

The React client uses the browser History API for `/signin` and `/signup`. Vite automatically serves `index.html` for these routes in local development. For production, configure your web server to fall back to `index.html` for unknown non-API routes.

**HMI presentation flow:** Open `/signup`, create account, sign out, open `/signin`, log in, explore recommendations, and save a car.


## Profile page & recommendation/search history

After signing in, click the **profile avatar** in the top-right corner, then **View profile & history**. The dedicated `/profile` route shows the account name, email, number of saved cars, and the user's recent activity. A profile is accessible only to its signed-in owner.

- Each successful **Find my match** recommendation request from a signed-in user is stored automatically in SQLite with the preferences and IDs of the recommended cars. The original recommendation API and machine-learning model remain connected.
- In **Explore cars**, press **Enter** after typing a search to save it to the signed-in user's history. Browsing/filtering alone is not logged.
- Click any previous match to restore its preferences in the questionnaire; click a search to repeat it in the catalog.
- **Clear history** deletes only the signed-in user's own activity.
- New endpoints: `GET /api/history`, `POST /api/history/search`, `DELETE /api/history`. The recommendation endpoint `POST /api/recommend` optionally accepts a Bearer token to save the match. Guest recommendations still work but are not saved.
- **Privacy note:** history is saved server-side in the local `backend/drivematch.db`; unlike a temporary browser-only list, it persists after sign-out and across logins. This is a local university demo, not a hosted production service.


## New: Improved vehicle photos and AI notebook

**Vehicle photos:** The React UI now prefers local images from `frontend/public/car-images/` using the `frontend/public/car-photos.json` photo manifest. If a local image is absent, it searches Wikimedia Commons for an exterior picture matching the brand and model, ranks suitable landscape shots, lazy-loads the result and links to the Wikimedia file page for licensing. This is a best-effort search: images can depict a different trim or model year, and some models may have no acceptable photo. Car photos are **not pre-bundled** in the archive due to unavailable image-host access during packaging.

**Recommended for an offline university demo:** With an internet connection, run this command from the `egypt-car-match` project folder:

```cmd
py scripts\download_car_photos.py
```

It attempts to download appropriately credited photos into `frontend/public/car-images/` and creates entries in `frontend/public/car-photos.json`. Review each downloaded image for the correct model and year before presenting; results depend on Wikimedia Commons availability. Re-run to continue missing entries. Wikimedia Commons files may have attribution and license requirements; open each linked source page to check.

**AI Jupyter notebook:** `notebooks/DriveMatch_AI_Recommendation_Model.ipynb` loads the same `backend/cars.json`, fits a scikit-learn TF-IDF model, uses cosine similarity and suitability weights, checks several test scenarios, and exports a trained artifact at `backend/models/car_tfidf.joblib`. That trained file is **already included**. Restart FastAPI and inspect `http://localhost:8000/api/health`; `model_source` should say `Jupyter notebook trained artifact`. The backend also works without the artifact by fitting the same model at startup.

To open the notebook in a virtual environment, install notebook prerequisites (outside the backend runtime requirements):

```cmd
.venv\Scripts\python.exe -m pip install notebook pandas matplotlib
.venv\Scripts\python.exe -m notebook
```

Run these commands from the `backend` folder and open the `../notebooks/DriveMatch_AI_Recommendation_Model.ipynb` file in Jupyter, or use VS Code's Jupyter extension. No real customer purchasing labels are available, so notebook evaluations test constraints and ranking behavior rather than measured purchase-prediction accuracy.
