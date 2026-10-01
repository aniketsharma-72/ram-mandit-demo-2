"""
Shri Ram Janmabhoomi Mandir - Visitor Portal
Flask + SQLite backend.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import os
import random
import sqlite3
import csv
import io
import re
import hashlib
import hmac

import qrcode
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, g, jsonify, render_template, request, session, redirect, Response, send_file, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "mandir.db")

app = Flask(__name__)
# For a real deployment set this via the environment instead of the fallback.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
app.config["JSON_AS_ASCII"] = False


# ---------------------------------------------------------------- database --

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'visitor',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS slots (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    label    TEXT    NOT NULL,
    start    TEXT    NOT NULL,
    end      TEXT    NOT NULL,
    kind     TEXT    NOT NULL,          -- darshan | aarti
    capacity INTEGER NOT NULL,
    sort     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slot_id       INTEGER NOT NULL REFERENCES slots(id),
    visit_date    TEXT    NOT NULL,
    people        INTEGER NOT NULL DEFAULT 1,
    reference     TEXT    NOT NULL UNIQUE,
    status        TEXT    NOT NULL DEFAULT 'confirmed',  -- confirmed | cancelled
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS festivals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    name_hi     TEXT,
    event_date  TEXT NOT NULL,
    description TEXT NOT NULL,
    icon        TEXT NOT NULL DEFAULT 'fa-calendar-days'
);

CREATE TABLE IF NOT EXISTS places (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,          -- temple | ghat | food | shopping
    distance_km REAL NOT NULL,
    description TEXT NOT NULL,
    image       TEXT,
    maps_query  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    service  TEXT NOT NULL,
    number   TEXT NOT NULL,
    detail   TEXT NOT NULL,
    icon     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS visits (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    day      TEXT NOT NULL UNIQUE,
    hits     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS announcements (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    type       TEXT NOT NULL DEFAULT 'info',
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id   INTEGER,
    action     TEXT NOT NULL,
    target     TEXT,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SLOTS = [
    ("Mangala Aarti",   "04:30", "05:30", "aarti",   3000,  1),
    ("Morning Darshan", "06:30", "11:30", "darshan", 25000, 2),
    ("Bhog Aarti",      "12:00", "12:30", "aarti",   3000,  3),
    ("Afternoon Break", "13:00", "13:59", "darshan", 5000,  4),
    ("Evening Darshan", "14:00", "18:30", "darshan", 22000, 5),
    ("Sandhya Aarti",   "19:00", "19:45", "aarti",   4000,  6),
    ("Night Darshan",   "20:00", "22:00", "darshan", 9000,  7),
]

FESTIVALS = [
    ("Ram Navami", "राम नवमी", "2027-04-16",
     "The birth anniversary of Bhagwan Shri Ram. The single busiest day of the year — "
     "expect extended darshan hours and very heavy crowds.", "fa-star"),
    ("Deepotsav", "दीपोत्सव", "2026-11-08",
     "Ayodhya's grand festival of lights. Lakhs of diyas are lit along the Saryu ghats "
     "on the eve of Diwali.", "fa-fire-flame-curved"),
    ("Pran Pratishtha Anniversary", "प्राण प्रतिष्ठा वर्षगांठ", "2027-01-22",
     "Anniversary of the consecration of Ram Lalla in the new temple. Special "
     "abhishek and cultural programmes.", "fa-gopuram"),
    ("Hanuman Jayanti", "हनुमान जयंती", "2027-04-21",
     "Celebrated with great devotion at Hanuman Garhi, a short walk from the mandir.", "fa-khanda"),
    ("Sawan Jhula Mela", "सावन झूला मेला", "2027-07-28",
     "The traditional swing festival held during the month of Sawan across Ayodhya's temples.",
     "fa-leaf"),
    ("Kartik Purnima", "कार्तिक पूर्णिमा", "2026-11-24",
     "Devotees take a holy dip in the Saryu river. Ghats stay open through the night.",
     "fa-moon"),
]

PLACES = [
    ("Hanuman Garhi", "temple", 0.8,
     "A 10th-century fort-like temple of Hanuman ji, reached by 76 steps. Traditionally "
     "visited before the darshan of Ram Lalla.",
     "nearby-hanuman-garhi.jpg", "Hanuman Garhi Ayodhya"),
    ("Kanak Bhawan", "temple", 1.2,
     "The 'golden palace' gifted to Mata Sita by Kaikeyi. Known for its ornate idols of "
     "Ram and Sita wearing gold crowns.",
     "nearby-kanak-bhawan.jpg", "Kanak Bhawan Ayodhya"),
    ("Ram Ki Paidi", "ghat", 2.1,
     "A chain of ghats on the Saryu river, spectacular at sunset and during Deepotsav "
     "when lakhs of diyas are lit.",
     "nearby-ram-ki-paidi.jpg", "Ram Ki Paidi Ayodhya"),
    ("Naya Ghat, Saryu River", "ghat", 2.6,
     "The main bathing ghat on the Saryu. Boat rides and evening aarti take place here.",
     "nearby-saryu.jpg", "Naya Ghat Ayodhya"),
    ("Ayodhya Food Street", "food", 0.5,
     "Local vegetarian thalis, kachori-sabzi, jalebi and the famous Ayodhya peda. "
     "Pure-veg only within the temple zone.",
     None, "restaurants near Ram Mandir Ayodhya"),
    ("Prasad & Puja Samagri Market", "shopping", 0.3,
     "Stalls selling prasad, rudraksh, brass idols and souvenirs on the approach road "
     "to the mandir.",
     None, "Ayodhya market near Ram Janmabhoomi"),
]

CONTACTS = [
    ("Police Control Room", "112", "24x7 emergency police assistance across Ayodhya.",
     "fa-shield-halved"),
    ("Ambulance", "108", "Free emergency ambulance service. Medical posts are stationed "
     "inside the temple complex.", "fa-truck-medical"),
    ("Fire Service", "101", "Fire and rescue services.", "fa-fire-extinguisher"),
    ("Temple Help Desk", "1800-000-0000", "Lost & found, wheelchair assistance and general "
     "visitor queries.", "fa-circle-info"),
    ("Women Helpline", "1090", "UP Women Power Line for the safety of women visitors.",
     "fa-person-dress"),
    ("Tourist Helpline", "1363", "Ministry of Tourism multilingual helpline.", "fa-passport"),
]


def init_db():
    """Create the schema and seed reference data if the database is empty."""
    fresh = not os.path.exists(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)

    # Lightweight migrations for databases created by older versions.
    cols = {r["name"] for r in con.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'visitor'")

    # Demo administrator for the college project. Change the password before deployment.
    admin_email = "admin@rammandir.local"
    if not con.execute("SELECT 1 FROM users WHERE email = ?", (admin_email,)).fetchone():
        con.execute(
            "INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)",
            ("Temple Administrator", admin_email, "9999999999",
             generate_password_hash("Admin@123"), "admin")
        )

    if con.execute("SELECT COUNT(*) c FROM announcements").fetchone()["c"] == 0:
        con.execute(
            "INSERT INTO announcements (title,body,type) VALUES (?,?,?)",
            ("Welcome to the Visitor Portal",
             "Use the online portal to check darshan slots and manage reservations.",
             "info")
        )

    if con.execute("SELECT COUNT(*) c FROM slots").fetchone()["c"] == 0:
        con.executemany(
            "INSERT INTO slots (label, start, end, kind, capacity, sort) "
            "VALUES (?,?,?,?,?,?)", SLOTS)

    if con.execute("SELECT COUNT(*) c FROM festivals").fetchone()["c"] == 0:
        con.executemany(
            "INSERT INTO festivals (name, name_hi, event_date, description, icon) "
            "VALUES (?,?,?,?,?)", FESTIVALS)

    if con.execute("SELECT COUNT(*) c FROM places").fetchone()["c"] == 0:
        con.executemany(
            "INSERT INTO places (name, category, distance_km, description, image, maps_query) "
            "VALUES (?,?,?,?,?,?)", PLACES)

    if con.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"] == 0:
        con.executemany(
            "INSERT INTO contacts (service, number, detail, icon) VALUES (?,?,?,?)", CONTACTS)

    con.commit()
    con.close()
    if fresh:
        print(f"  * Initialised new database at {DB_PATH}")


# ------------------------------------------------------------------ helpers --

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(ok=False, error="Please log in to continue."), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify(ok=False, error="Administrator login required."), 401
        if user["role"] != "admin":
            return jsonify(ok=False, error="Administrator access required."), 403
        return fn(*args, **kwargs)
    return wrapper


def audit(action, target="", details=""):
    db = get_db()
    db.execute(
        "INSERT INTO audit_logs (admin_id, action, target, details) VALUES (?,?,?,?)",
        (session.get("user_id"), action, target, details)
    )
    db.commit()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute(
        "SELECT id, name, email, phone, role FROM users WHERE id = ?", (uid,)).fetchone()


def json_body():
    return request.get_json(silent=True) or {}


def booked_count(db, slot_id, visit_date):
    row = db.execute(
        "SELECT COALESCE(SUM(people), 0) n FROM bookings "
        "WHERE slot_id = ? AND visit_date = ? AND status = 'confirmed'",
        (slot_id, visit_date)).fetchone()
    return row["n"]


def crowd_level(pct):
    if pct < 35:
        return "low", "Comfortable", "Great time to visit — minimal waiting."
    if pct < 65:
        return "moderate", "Moderate", "Steady flow. Expect a 20-40 minute queue."
    if pct < 85:
        return "high", "Busy", "Heavy rush. Allow 1-2 hours for darshan."
    return "peak", "Very Heavy", "Peak crowd. Consider an early morning slot instead."


# -------------------------------------------------------------- QR tickets --

def ticket_signature(reference):
    secret = app.secret_key.encode("utf-8")
    return hmac.new(secret, reference.encode("utf-8"), hashlib.sha256).hexdigest()

def ticket_url(reference):
    return url_for("verify_ticket", reference=reference, sig=ticket_signature(reference), _external=True)


@app.get("/api/bookings/<reference>/qr")
def booking_qr(reference):
    db = get_db()
    row = db.execute("""
        SELECT b.reference, b.status, b.visit_date, b.people, s.label, s.start, s.end,
               u.name, u.email
        FROM bookings b
        JOIN slots s ON s.id=b.slot_id
        JOIN users u ON u.id=b.user_id
        WHERE b.reference=?
    """, (reference,)).fetchone()
    if row is None:
        return jsonify(ok=False, error="Ticket not found."), 404

    # QR contains a signed public verification URL; it does not expose passwords or private data.
    qr = qrcode.QRCode(version=None, box_size=8, border=3)
    qr.add_data(ticket_url(reference))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return send_file(out, mimetype="image/png", max_age=3600)


@app.get("/ticket/<reference>")
def ticket_page(reference):
    sig = request.args.get("sig", "")
    expected = ticket_signature(reference)
    if not hmac.compare_digest(sig, expected):
        return render_template("ticket.html", valid=False, booking=None, verify_url=None), 403

    db = get_db()
    row = db.execute("""
        SELECT b.id, b.reference, b.status, b.visit_date, b.people, b.created_at,
               s.label, s.start, s.end, u.name, u.email, u.phone
        FROM bookings b
        JOIN slots s ON s.id=b.slot_id
        JOIN users u ON u.id=b.user_id
        WHERE b.reference=?
    """, (reference,)).fetchone()
    if row is None:
        return render_template("ticket.html", valid=False, booking=None, verify_url=None), 404
    return render_template("ticket.html", valid=True, booking=dict(row), verify_url=ticket_url(reference))


@app.get("/api/tickets/<reference>")
def verify_ticket(reference):
    sig = request.args.get("sig", "")
    if not hmac.compare_digest(sig, ticket_signature(reference)):
        return jsonify(ok=False, valid=False, error="Invalid ticket signature."), 403
    row = get_db().execute("""
        SELECT b.reference, b.status, b.visit_date, b.people,
               s.label AS slot, s.start, s.end, u.name AS devotee
        FROM bookings b JOIN slots s ON s.id=b.slot_id JOIN users u ON u.id=b.user_id
        WHERE b.reference=?
    """, (reference,)).fetchone()
    if row is None:
        return jsonify(ok=True, valid=False, error="Ticket not found."), 404
    return jsonify(ok=True, valid=True, ticket=dict(row))


# --------------------------------------------------------------------- page --

@app.route("/")
def index():
    db = get_db()
    today = date.today().isoformat()
    db.execute("INSERT INTO visits (day, hits) VALUES (?, 1) "
               "ON CONFLICT(day) DO UPDATE SET hits = hits + 1", (today,))
    db.commit()
    return render_template("index.html", year=date.today().year)


# --------------------------------------------------------------------- auth --

@app.post("/api/auth/register")
def register():
    data = json_body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if len(name) < 2:
        return jsonify(ok=False, error="Please enter your full name."), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(ok=False, error="Please enter a valid email address."), 400
    if phone and not (phone.isdigit() and len(phone) == 10):
        return jsonify(ok=False, error="Phone number must be 10 digits."), 400
    if len(password) < 6:
        return jsonify(ok=False, error="Password must be at least 6 characters."), 400

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify(ok=False, error="An account with this email already exists."), 409

    cur = db.execute(
        "INSERT INTO users (name, email, phone, password_hash) VALUES (?,?,?,?)",
        (name, email, phone, generate_password_hash(password)))
    db.commit()
    session["user_id"] = cur.lastrowid
    session.permanent = True
    return jsonify(ok=True, user={"id": cur.lastrowid, "name": name,
                                  "email": email, "phone": phone, "role": "visitor"}), 201


@app.post("/api/auth/login")
def login():
    data = json_body()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_db().execute(
        "SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(ok=False, error="Incorrect email or password."), 401

    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify(ok=True, user={"id": user["id"], "name": user["name"],
                                  "email": user["email"], "phone": user["phone"],
                                  "role": user["role"]})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/auth/me")
def me():
    user = current_user()
    if user is None:
        return jsonify(ok=True, user=None)
    return jsonify(ok=True, user=dict(user))


# ------------------------------------------------------------ timings/slots --

@app.get("/api/slots")
def slots():
    visit_date = request.args.get("date") or date.today().isoformat()
    try:
        d = datetime.strptime(visit_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(ok=False, error="Date must be in YYYY-MM-DD format."), 400
    if d < date.today():
        return jsonify(ok=False, error="Please choose today or a future date."), 400
    if d > date.today() + timedelta(days=60):
        return jsonify(ok=False, error="Bookings open only 60 days in advance."), 400

    db = get_db()
    out = []
    for s in db.execute("SELECT * FROM slots ORDER BY sort"):
        taken = booked_count(db, s["id"], visit_date)
        left = max(s["capacity"] - taken, 0)
        out.append({
            "id": s["id"], "label": s["label"], "start": s["start"], "end": s["end"],
            "kind": s["kind"], "capacity": s["capacity"], "booked": taken,
            "available": left, "full": left == 0,
        })
    return jsonify(ok=True, date=visit_date, slots=out)


# ----------------------------------------------------------------- bookings --

@app.post("/api/bookings")
@login_required
def create_booking():
    data = json_body()
    slot_id = data.get("slot_id")
    visit_date = (data.get("date") or "").strip()
    try:
        people = int(data.get("people", 1))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Number of people must be a whole number."), 400

    if not (1 <= people <= 10):
        return jsonify(ok=False, error="You can book for 1 to 10 people at a time."), 400
    try:
        d = datetime.strptime(visit_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(ok=False, error="Please choose a valid visit date."), 400
    if d < date.today():
        return jsonify(ok=False, error="You cannot book a date in the past."), 400

    db = get_db()
    slot = db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
    if slot is None:
        return jsonify(ok=False, error="That darshan slot does not exist."), 404

    dup = db.execute(
        "SELECT 1 FROM bookings WHERE user_id = ? AND slot_id = ? AND visit_date = ? "
        "AND status = 'confirmed'",
        (session["user_id"], slot_id, visit_date)).fetchone()
    if dup:
        return jsonify(ok=False,
                       error="You already have a booking for this slot on this date."), 409

    if booked_count(db, slot_id, visit_date) + people > slot["capacity"]:
        return jsonify(ok=False,
                       error="Not enough places left in this slot. Please pick another."), 409

    reference = f"RM{d.strftime('%y%m%d')}{random.randint(1000, 9999)}"
    cur = db.execute(
        "INSERT INTO bookings (user_id, slot_id, visit_date, people, reference) "
        "VALUES (?,?,?,?,?)",
        (session["user_id"], slot_id, visit_date, people, reference))
    db.commit()

    return jsonify(ok=True, booking={
        "id": cur.lastrowid, "reference": reference, "date": visit_date,
        "people": people, "slot": slot["label"],
        "time": f"{slot['start']} - {slot['end']}",
        "ticket_url": ticket_url(reference),
        "qr_url": url_for("booking_qr", reference=reference),
    }), 201


@app.get("/api/bookings")
@login_required
def my_bookings():
    rows = get_db().execute(
        "SELECT b.id, b.reference, b.visit_date, b.people, b.status, "
        "       s.label, s.start, s.end "
        "FROM bookings b JOIN slots s ON s.id = b.slot_id "
        "WHERE b.user_id = ? ORDER BY b.visit_date DESC, s.sort",
        (session["user_id"],)).fetchall()
    return jsonify(ok=True, bookings=[{
        "id": r["id"], "reference": r["reference"], "date": r["visit_date"],
        "people": r["people"], "status": r["status"], "slot": r["label"],
        "time": f"{r['start']} - {r['end']}",
        "ticket_url": ticket_url(r["reference"]),
        "qr_url": url_for("booking_qr", reference=r["reference"]),
        "past": r["visit_date"] < date.today().isoformat(),
    } for r in rows])


@app.delete("/api/bookings/<int:booking_id>")
@login_required
def cancel_booking(booking_id):
    db = get_db()
    row = db.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?",
                     (booking_id, session["user_id"])).fetchone()
    if row is None:
        return jsonify(ok=False, error="Booking not found."), 404
    if row["status"] == "cancelled":
        return jsonify(ok=False, error="This booking is already cancelled."), 400

    db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    db.commit()
    return jsonify(ok=True)


# ----------------------------------------------------------- visitor status --

@app.get("/api/visitors/status")
def visitor_status():
    """Live crowd estimate: real confirmed bookings plus a time-of-day walk-in curve."""
    db = get_db()
    today = date.today().isoformat()
    now = datetime.now()

    # Walk-in devotees follow a predictable daily curve, peaking morning and evening.
    hourly_weight = {4: .35, 5: .55, 6: .80, 7: .95, 8: 1.0, 9: .90, 10: .80,
                     11: .65, 12: .45, 13: .30, 14: .50, 15: .65, 16: .80,
                     17: .92, 18: .85, 19: .95, 20: .70, 21: .45, 22: .20}
    weight = hourly_weight.get(now.hour, 0.08)
    # Weekends are noticeably busier than weekdays.
    weight *= 1.35 if now.weekday() >= 5 else 1.0

    booked_today = db.execute(
        "SELECT COALESCE(SUM(people), 0) n FROM bookings "
        "WHERE visit_date = ? AND status = 'confirmed'", (today,)).fetchone()["n"]

    total_capacity = db.execute(
        "SELECT COALESCE(SUM(capacity), 0) c FROM slots").fetchone()["c"]

    inside = int(6500 * weight) + booked_today
    pct = min(round(inside / (total_capacity * 0.35) * 100), 100)
    level, label, advice = crowd_level(pct)

    # Suggest the quietest upcoming hour of the day.
    upcoming = {h: w for h, w in hourly_weight.items() if h > now.hour}
    best_hour = min(upcoming, key=upcoming.get) if upcoming else 6
    best_time = f"{best_hour:02d}:00"

    open_slot = db.execute(
        "SELECT label FROM slots WHERE start <= ? AND end >= ? ORDER BY sort LIMIT 1",
        (now.strftime("%H:%M"), now.strftime("%H:%M"))).fetchone()

    return jsonify(ok=True, status={
        "inside": inside,
        "percent": pct,
        "level": level,
        "label": label,
        "advice": advice,
        "wait_minutes": int(pct * 1.4),
        "booked_today": booked_today,
        "current_slot": open_slot["label"] if open_slot else "Temple Closed",
        "is_open": open_slot is not None,
        "best_time": best_time,
        "updated": now.strftime("%d %b %Y, %I:%M %p"),
    })


# ------------------------------------------------------------ content feeds --

@app.get("/api/festivals")
def festivals():
    rows = get_db().execute(
        "SELECT * FROM festivals ORDER BY event_date").fetchall()
    today = date.today()
    out = []
    for r in rows:
        d = datetime.strptime(r["event_date"], "%Y-%m-%d").date()
        days = (d - today).days
        out.append({
            "id": r["id"], "name": r["name"], "name_hi": r["name_hi"],
            "date": d.strftime("%d %B %Y"), "iso": r["event_date"],
            "description": r["description"], "icon": r["icon"],
            "days_away": days, "past": days < 0,
        })
    out.sort(key=lambda x: (x["past"], abs(x["days_away"])))
    return jsonify(ok=True, festivals=out)


@app.get("/api/places")
def places():
    category = request.args.get("category")
    db = get_db()
    if category and category != "all":
        rows = db.execute("SELECT * FROM places WHERE category = ? ORDER BY distance_km",
                          (category,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM places ORDER BY distance_km").fetchall()
    return jsonify(ok=True, places=[dict(r) for r in rows])


@app.get("/api/contacts")
def contacts():
    rows = get_db().execute("SELECT * FROM contacts ORDER BY id").fetchall()
    return jsonify(ok=True, contacts=[dict(r) for r in rows])


@app.post("/api/messages")
def post_message():
    data = json_body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    body = (data.get("message") or "").strip()

    if len(name) < 2:
        return jsonify(ok=False, error="Please enter your name."), 400
    if "@" not in email:
        return jsonify(ok=False, error="Please enter a valid email address."), 400
    if not subject:
        return jsonify(ok=False, error="Please choose a subject."), 400
    if len(body) < 10:
        return jsonify(ok=False, error="Please describe your query in at least 10 characters."), 400

    db = get_db()
    db.execute("INSERT INTO messages (name, email, subject, body) VALUES (?,?,?,?)",
               (name, email, subject, body))
    db.commit()
    return jsonify(ok=True, message="Thank you. Our help desk will reply within 24 hours."), 201


@app.get("/api/stats")
def stats():
    db = get_db()
    total_bookings = db.execute(
        "SELECT COALESCE(SUM(people), 0) n FROM bookings WHERE status = 'confirmed'"
    ).fetchone()["n"]
    users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    page_views = db.execute("SELECT COALESCE(SUM(hits), 0) n FROM visits").fetchone()["n"]
    return jsonify(ok=True, stats={
        "registered_devotees": users,
        "darshan_booked": total_bookings,
        "page_views": page_views,
    })



# -------------------------------------------------------------- announcements --

@app.get("/api/announcements")
def announcements():
    rows = get_db().execute(
        "SELECT * FROM announcements WHERE active = 1 ORDER BY id DESC"
    ).fetchall()
    return jsonify(ok=True, announcements=[dict(r) for r in rows])


# --------------------------------------------------------------- admin panel --

@app.get("/admin")
def admin_page():
    user = current_user()
    if not user:
        return redirect("/")
    if user["role"] != "admin":
        return redirect("/")
    return render_template("admin.html", year=date.today().year, admin=dict(user))


@app.get("/api/admin/overview")
@admin_required
def admin_overview():
    db = get_db()
    today = date.today().isoformat()
    stats = {
        "users": db.execute("SELECT COUNT(*) c FROM users WHERE role='visitor'").fetchone()["c"],
        "admins": db.execute("SELECT COUNT(*) c FROM users WHERE role='admin'").fetchone()["c"],
        "bookings": db.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"],
        "confirmed_people": db.execute(
            "SELECT COALESCE(SUM(people),0) n FROM bookings WHERE status='confirmed'"
        ).fetchone()["n"],
        "today_bookings": db.execute(
            "SELECT COUNT(*) c FROM bookings WHERE visit_date=?", (today,)
        ).fetchone()["c"],
        "messages": db.execute("SELECT COUNT(*) c FROM messages").fetchone()["c"],
        "page_views": db.execute("SELECT COALESCE(SUM(hits),0) n FROM visits").fetchone()["n"],
    }
    daily = db.execute("""
        SELECT visit_date AS day, COUNT(*) AS bookings, COALESCE(SUM(people),0) AS people
        FROM bookings
        WHERE visit_date >= date('now','-6 day')
        GROUP BY visit_date ORDER BY visit_date
    """).fetchall()
    popular = db.execute("""
        SELECT s.label, COUNT(b.id) bookings, COALESCE(SUM(b.people),0) people
        FROM bookings b JOIN slots s ON s.id=b.slot_id
        WHERE b.status='confirmed'
        GROUP BY s.id ORDER BY people DESC
    """).fetchall()
    return jsonify(ok=True, stats=stats,
                   daily=[dict(r) for r in daily],
                   popular=[dict(r) for r in popular])


@app.get("/api/admin/users")
@admin_required
def admin_users():
    rows = get_db().execute("""
        SELECT u.id,u.name,u.email,u.phone,u.role,u.created_at,
               COUNT(b.id) bookings
        FROM users u LEFT JOIN bookings b ON b.user_id=u.id
        GROUP BY u.id ORDER BY u.created_at DESC
    """).fetchall()
    return jsonify(ok=True, users=[dict(r) for r in rows])


@app.post("/api/admin/users/<int:user_id>/role")
@admin_required
def admin_user_role(user_id):
    data = json_body()
    role = data.get("role")
    if role not in ("visitor", "admin"):
        return jsonify(ok=False, error="Invalid role."), 400
    if user_id == session["user_id"] and role != "admin":
        return jsonify(ok=False, error="You cannot remove your own administrator role."), 400
    db = get_db()
    user = db.execute("SELECT name,email FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return jsonify(ok=False, error="User not found."), 404
    db.execute("UPDATE users SET role=? WHERE id=?", (role,user_id))
    db.commit()
    audit("ROLE_CHANGED", f"user:{user_id}", f"{user['email']} -> {role}")
    return jsonify(ok=True)


@app.get("/api/admin/bookings")
@admin_required
def admin_bookings():
    status = request.args.get("status", "all")
    q = (request.args.get("q") or "").strip()
    sql = """SELECT b.id,b.reference,b.visit_date,b.people,b.status,b.created_at,
                    u.name,u.email,u.phone,s.label,s.start,s.end
             FROM bookings b JOIN users u ON u.id=b.user_id
             JOIN slots s ON s.id=b.slot_id WHERE 1=1"""
    params=[]
    if status in ("confirmed","cancelled"):
        sql += " AND b.status=?"; params.append(status)
    if q:
        sql += " AND (b.reference LIKE ? OR u.name LIKE ? OR u.email LIKE ?)"
        params += [f"%{q}%"]*3
    sql += " ORDER BY b.visit_date DESC,b.id DESC LIMIT 500"
    rows=get_db().execute(sql,params).fetchall()
    return jsonify(ok=True, bookings=[dict(r) for r in rows])


@app.post("/api/admin/bookings/<int:booking_id>/status")
@admin_required
def admin_booking_status(booking_id):
    status=json_body().get("status")
    if status not in ("confirmed","cancelled"):
        return jsonify(ok=False,error="Invalid booking status."),400
    db=get_db()
    row=db.execute("SELECT reference,status FROM bookings WHERE id=?",(booking_id,)).fetchone()
    if not row: return jsonify(ok=False,error="Booking not found."),404
    db.execute("UPDATE bookings SET status=? WHERE id=?",(status,booking_id))
    db.commit()
    audit("BOOKING_STATUS",f"booking:{booking_id}",f"{row['reference']} -> {status}")
    return jsonify(ok=True)


@app.get("/api/admin/slots")
@admin_required
def admin_slots():
    rows=get_db().execute("SELECT * FROM slots ORDER BY sort").fetchall()
    return jsonify(ok=True, slots=[dict(r) for r in rows])


@app.post("/api/admin/slots/<int:slot_id>")
@admin_required
def admin_slot_update(slot_id):
    data=json_body()
    try: capacity=int(data.get("capacity"))
    except (TypeError,ValueError): return jsonify(ok=False,error="Capacity must be a number."),400
    if capacity < 1 or capacity > 100000: return jsonify(ok=False,error="Invalid capacity."),400
    label=(data.get("label") or "").strip()
    start=(data.get("start") or "").strip()
    end=(data.get("end") or "").strip()
    if not label or not re.match(r"^\d{2}:\d{2}$",start) or not re.match(r"^\d{2}:\d{2}$",end):
        return jsonify(ok=False,error="Please provide a label and valid HH:MM timings."),400
    db=get_db()
    if not db.execute("SELECT 1 FROM slots WHERE id=?",(slot_id,)).fetchone():
        return jsonify(ok=False,error="Slot not found."),404
    db.execute("UPDATE slots SET label=?,start=?,end=?,capacity=? WHERE id=?",
               (label,start,end,capacity,slot_id))
    db.commit()
    audit("SLOT_UPDATED",f"slot:{slot_id}",f"{label} capacity={capacity}")
    return jsonify(ok=True)


@app.get("/api/admin/messages")
@admin_required
def admin_messages():
    rows=get_db().execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 500").fetchall()
    return jsonify(ok=True,messages=[dict(r) for r in rows])


@app.get("/api/admin/audit")
@admin_required
def admin_audit():
    rows=get_db().execute("""
        SELECT a.*,u.name AS admin_name
        FROM audit_logs a LEFT JOIN users u ON u.id=a.admin_id
        ORDER BY a.id DESC LIMIT 100
    """).fetchall()
    return jsonify(ok=True,logs=[dict(r) for r in rows])


@app.post("/api/admin/announcements")
@admin_required
def admin_announcement_create():
    data=json_body()
    title=(data.get("title") or "").strip()
    body=(data.get("body") or "").strip()
    typ=data.get("type") or "info"
    if not title or not body: return jsonify(ok=False,error="Title and message are required."),400
    if typ not in ("info","warning","success"): typ="info"
    db=get_db()
    cur=db.execute("INSERT INTO announcements(title,body,type) VALUES(?,?,?)",(title,body,typ))
    db.commit(); audit("ANNOUNCEMENT_CREATED",f"announcement:{cur.lastrowid}",title)
    return jsonify(ok=True,id=cur.lastrowid),201


@app.delete("/api/admin/announcements/<int:announcement_id>")
@admin_required
def admin_announcement_delete(announcement_id):
    db=get_db()
    db.execute("UPDATE announcements SET active=0 WHERE id=?",(announcement_id,))
    db.commit(); audit("ANNOUNCEMENT_ARCHIVED",f"announcement:{announcement_id}","")
    return jsonify(ok=True)


@app.get("/api/admin/export/bookings.csv")
@admin_required
def export_bookings():
    rows=get_db().execute("""
        SELECT b.reference,b.visit_date,b.people,b.status,b.created_at,
               u.name,u.email,u.phone,s.label,s.start,s.end
        FROM bookings b JOIN users u ON u.id=b.user_id JOIN slots s ON s.id=b.slot_id
        ORDER BY b.visit_date DESC,b.id DESC
    """).fetchall()
    out=io.StringIO()
    writer=csv.writer(out)
    writer.writerow(["Reference","Visit Date","People","Status","Created At","Name","Email","Phone","Slot","Start","End"])
    for r in rows: writer.writerow(list(r))
    return Response(out.getvalue(),mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=ram_mandir_bookings.csv"})


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="Endpoint not found."), 404
    return render_template("index.html", year=date.today().year), 404


if __name__ == "__main__":
    init_db()
    print("  * Ram Mandir Visitor Portal -> http://127.0.0.1:5055")
    app.run(debug=True, port=5055)
