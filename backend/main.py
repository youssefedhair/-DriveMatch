"""Content-based ML car recommendation API for an Egyptian-market demo."""
from pathlib import Path
from typing import Literal
import json
import sqlite3
import secrets
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, Header
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib

CARS = json.loads((Path(__file__).parent / 'cars.json').read_text(encoding='utf-8'))
# Unsupervised ML: vectorize natural-language vehicle profiles and compare to user intent.
DOCUMENTS = [f"{c['type']} {' '.join(c['tags'])} {c['description']}" for c in CARS]
MODEL_FILE = Path(__file__).parent / 'models' / 'car_tfidf.joblib'
MODEL_SOURCE = 'runtime fitted'
try:
    artifact = joblib.load(MODEL_FILE) if MODEL_FILE.exists() else None
    if (artifact and artifact.get('car_ids') == [str(c['id']) for c in CARS]
            and artifact.get('documents') == DOCUMENTS):
        VECTORIZER = artifact['vectorizer']
        CAR_VECTORS = artifact['car_vectors']
        MODEL_SOURCE = 'Jupyter notebook trained artifact'
    else:
        raise ValueError('Missing or stale trained artifact')
except (ValueError, OSError, KeyError, TypeError):
    VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    CAR_VECTORS = VECTORIZER.fit_transform(DOCUMENTS)

app = FastAPI(title='DriveMatch Car Recommendation AI', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

class Preferences(BaseModel):
    budget: int = Field(default=1200000, ge=250000, le=15000000)
    passengers: int = Field(default=4, ge=1, le=8)
    usage: Literal['city', 'mixed', 'highway'] = 'mixed'
    priority: Literal['economy', 'comfort', 'family', 'performance', 'resale'] = 'economy'
    roads: Literal['normal', 'rough'] = 'normal'
    parking: Literal['easy', 'normal'] = 'normal'
    transmission: Literal['Any', 'Automatic', 'Manual'] = 'Any'
    fuel: Literal['Any', 'Petrol', 'Hybrid', 'Electric'] = 'Any'
    notes: str = Field(default='', max_length=500)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'model': 'TF-IDF content-based recommender', 'catalog_size': len(CARS), 'model_source': MODEL_SOURCE}

@app.get('/api/cars')
def cars():
    return {'cars': CARS, 'demo_data': True}

@app.post('/api/recommend')
def recommend(p: Preferences, authorization: str | None = Header(default=None)):
    intent_parts = [p.usage, p.priority, p.roads, 'family' if p.passengers >= 5 else 'commute', p.notes]
    intent = ' '.join(intent_parts).replace('rough', 'weekend crossover SUV')
    semantic = cosine_similarity(VECTORIZER.transform([intent]), CAR_VECTORS).flatten()
    weights = {'city': {'city': 1.0, 'highway': .1}, 'mixed': {'city': .5, 'highway': .5}, 'highway': {'city': .1, 'highway': 1.0}}[p.usage]
    results = []
    for i, car in enumerate(CARS):
        if car['price'] > p.budget or car['seats'] < p.passengers:
            continue  # Hard constraints: never recommend unaffordable or undersized cars.
        if p.transmission != 'Any' and car['transmission'] != p.transmission:
            continue
        if p.fuel != 'Any' and car['fuel'] != p.fuel:
            continue
        drive = (car['city'] * weights['city'] + car['highway'] * weights['highway']) / 10
        priority = car[p.priority] / 10
        terrain = (car['rough'] if p.roads == 'rough' else car['comfort']) / 10
        parking = (car['parking'] if p.parking == 'easy' else car['comfort']) / 10
        value = max(0, min(1, 1 - car['price'] / p.budget))
        score = .28 * priority + .22 * drive + .13 * terrain + .10 * parking + .17 * float(semantic[i]) + .10 * value
        reasons = []
        if car[p.priority] >= 8:
            reasons.append(f"Strong fit for {p.priority}")
        if p.usage == 'city' and car['city'] >= 8:
            reasons.append('Suited to Cairo-style city driving')
        if p.usage == 'highway' and car['highway'] >= 8:
            reasons.append('Comfortable for frequent highway trips')
        if p.roads == 'rough' and car['rough'] >= 7:
            reasons.append('Higher suitability for uneven roads')
        if p.parking == 'easy' and car['parking'] >= 8:
            reasons.append('Easier to park in tight spaces')
        if car['family'] >= 8 and p.passengers >= 4:
            reasons.append('Practical for families')
        reasons.append(f"Within budget by EGP {p.budget-car['price']:,}")
        results.append({**car, 'score': round(score * 100), 'reasons': reasons[:3]})
    results.sort(key=lambda x: (-x['score'], x['price']))
    if authorization:
        # History belongs only to a verified user; public recommendations remain available.
        user = current_user(authorization)
        with database() as db:
            db.execute('INSERT INTO activity_history(user_id,kind,preferences,match_ids,created_at) VALUES (?,?,?,?,?)',
                       (user['id'], 'match', p.model_dump_json(), json.dumps([str(c['id']) for c in results[:6]]), datetime.now(timezone.utc).isoformat()))
    return {'matches': results[:6], 'total_eligible': len(results), 'demo_data': True, 'model': 'TF-IDF + explainable suitability ranking', 'model_source': MODEL_SOURCE}


# University demo authentication. The SQLite DB is created locally on first run.
DB_PATH = Path(__file__).parent / 'drivematch.db'

def database():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_db():
    with database() as db:
        db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER NOT NULL, car_id TEXT NOT NULL, PRIMARY KEY(user_id,car_id))')
        db.execute('CREATE TABLE IF NOT EXISTS activity_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL CHECK(kind IN ("match","search")), query TEXT, preferences TEXT, match_ids TEXT, created_at TEXT NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_history_user_date ON activity_history(user_id, id DESC)')
initialize_db()

class SignUp(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

class SignIn(BaseModel):
    email: str
    password: str

def normal_email(email):
    email = email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(status_code=422, detail='Please enter a valid email address.')
    return email

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 310_000).hex()

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def new_session(db, user):
    token = secrets.token_urlsafe(32)
    expiration = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    db.execute('INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?,?,?)', (token_digest(token), user['id'], expiration))
    return {'token': token, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}}

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Please sign in first.')
    with database() as db:
        row = db.execute('SELECT users.id, users.name, users.email, sessions.expires_at FROM sessions JOIN users ON sessions.user_id=users.id WHERE sessions.token_hash=?', (token_digest(authorization[7:]),)).fetchone()
    if not row or datetime.fromisoformat(row['expires_at']) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail='Session expired. Please sign in again.')
    return dict(row)

@app.post('/api/auth/signup', status_code=201)
def signup(payload: SignUp):
    email = normal_email(payload.email)
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail='Name must contain at least 2 characters.')
    salt = secrets.token_hex(16)
    with database() as db:
        try:
            cursor = db.execute('INSERT INTO users (name,email,salt,password_hash) VALUES (?,?,?,?)', (name, email, salt, hash_password(payload.password, salt)))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail='An account with this email already exists.')
        return new_session(db, {'id': cursor.lastrowid, 'name': name, 'email': email})

@app.post('/api/auth/signin')
def signin(payload: SignIn):
    email = normal_email(payload.email)
    with database() as db:
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if not user or not hmac.compare_digest(hash_password(payload.password, user['salt']), user['password_hash']):
            raise HTTPException(status_code=401, detail='Incorrect email or password.')
        return new_session(db, user)

@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return {'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}}

@app.post('/api/auth/signout')
def signout(user=Depends(current_user), authorization: str = Header()):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (token_digest(authorization[7:]),))
    return {'ok': True}

@app.get('/api/favorites')
def get_favorites(user=Depends(current_user)):
    with database() as db:
        ids = [r['car_id'] for r in db.execute('SELECT car_id FROM favorites WHERE user_id=?', (user['id'],)).fetchall()]
    return {'ids': ids}

@app.put('/api/favorites/{car_id}')
def add_favorite(car_id: str, user=Depends(current_user)):
    if not any(str(c['id']) == car_id for c in CARS):
        raise HTTPException(status_code=404, detail='Car not found.')
    with database() as db:
        db.execute('INSERT OR IGNORE INTO favorites(user_id,car_id) VALUES (?,?)', (user['id'], car_id))
    return {'saved': True}

@app.delete('/api/favorites/{car_id}')
def remove_favorite(car_id: str, user=Depends(current_user)):
    with database() as db:
        db.execute('DELETE FROM favorites WHERE user_id=? AND car_id=?', (user['id'], car_id))
    return {'saved': False}


class SearchHistoryEntry(BaseModel):
    query: str = Field(min_length=1, max_length=100)

@app.post('/api/history/search', status_code=201)
def record_search(payload: SearchHistoryEntry, user=Depends(current_user)):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail='Search cannot be empty.')
    with database() as db:
        db.execute('INSERT INTO activity_history(user_id,kind,query,created_at) VALUES (?,?,?,?)',
                   (user['id'], 'search', query, datetime.now(timezone.utc).isoformat()))
    return {'saved': True}

@app.get('/api/history')
def history(user=Depends(current_user)):
    with database() as db:
        rows = db.execute('SELECT id,kind,query,preferences,match_ids,created_at FROM activity_history WHERE user_id=? ORDER BY id DESC LIMIT 100', (user['id'],)).fetchall()
    return {'history': [{**dict(row), 'preferences': json.loads(row['preferences']) if row['preferences'] else None,
                         'match_ids': json.loads(row['match_ids']) if row['match_ids'] else []} for row in rows]}

@app.delete('/api/history')
def clear_history(user=Depends(current_user)):
    with database() as db:
        db.execute('DELETE FROM activity_history WHERE user_id=?', (user['id'],))
    return {'cleared': True}
