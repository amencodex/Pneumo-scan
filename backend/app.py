from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
MEDIA_DIR = PROJECT_DIR / "website" / "media"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "data" / "pneumoscan.db"
MODEL_PATH = PROJECT_DIR / "models" / "pneumonia_model.json"
BLOOD_MODEL_PATH = PROJECT_DIR / "models" / "blood_cell_model.json"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123qwe...rpg"


app = FastAPI(title="PneumoScan Local Backend", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6, max_length=128)


class CheckinRequest(BaseModel):
    scan_id: int
    temperature: str = Field(default="", max_length=40)
    cough_level: int = Field(ge=0, le=10)
    breathing_level: int = Field(ge=0, le=10)
    oxygen_level: str = Field(default="", max_length=40)
    fluids_note: str = Field(default="", max_length=140)
    food_note: str = Field(default="", max_length=140)
    notes: str = Field(default="", max_length=500)


class AppointmentRequest(BaseModel):
    user_id: int
    appointment_at: str = Field(min_length=3, max_length=120)
    title: str = Field(default="PneumoScan follow-up", max_length=120)
    notes: str = Field(default="", max_length=500)
    status: str = Field(default="booked", max_length=40)


class UserMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class AdminMessageRequest(BaseModel):
    user_id: int
    body: str = Field(min_length=1, max_length=1000)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              salt TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL,
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS scans (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              original_name TEXT NOT NULL,
              saved_path TEXT NOT NULL,
              probability REAL NOT NULL,
              confidence INTEGER NOT NULL,
              result_label TEXT NOT NULL,
              xray_view TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS checkins (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              scan_id INTEGER NOT NULL,
              temperature TEXT NOT NULL,
              cough_level INTEGER NOT NULL,
              breathing_level INTEGER NOT NULL,
              oxygen_level TEXT NOT NULL,
              fluids_note TEXT NOT NULL,
              food_note TEXT NOT NULL,
              notes TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(scan_id) REFERENCES scans(id)
            );

            CREATE TABLE IF NOT EXISTS appointments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              admin_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              appointment_at TEXT NOT NULL,
              notes TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(admin_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              sender TEXT NOT NULL,
              body TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS blood_tests (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              original_name TEXT NOT NULL,
              saved_path TEXT NOT NULL,
              predicted_cell TEXT NOT NULL,
              confidence INTEGER NOT NULL,
              result_label TEXT NOT NULL,
              probabilities_json TEXT NOT NULL,
              support_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        ensure_admin_account(conn)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 160_000)
    return digest.hex()


def ensure_admin_account(conn: sqlite3.Connection) -> None:
    salt = secrets.token_hex(16)
    password_hash = hash_password(ADMIN_PASSWORD, salt)
    row = conn.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
    if row:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
            (password_hash, salt, ADMIN_USERNAME),
        )
    else:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (ADMIN_USERNAME, password_hash, salt, utc_now()),
        )


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, expires_at, utc_now()),
        )
    return token


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Log in first.")

    token = authorization.removeprefix("Bearer ").strip()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.username, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Session expired. Log in again.")

    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired. Log in again.")

    return {
        "id": row["id"],
        "username": row["username"],
        "token": token,
        "is_admin": row["username"] == ADMIN_USERNAME,
    }


def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin account required.")
    return user


def load_model() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Model not found at {MODEL_PATH}. Train pneumonia_model.json first.",
        )

    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def load_blood_model() -> dict[str, Any]:
    if not BLOOD_MODEL_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Blood cell model not found at {BLOOD_MODEL_PATH}. Train blood_cell_model.json first.",
        )

    return json.loads(BLOOD_MODEL_PATH.read_text(encoding="utf-8"))


def load_xray(path: Path, size: int) -> np.ndarray:
    image = Image.open(path).convert("L").resize((size, size), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def add_histogram(features: dict[str, float], gray: np.ndarray) -> None:
    values = gray.reshape(-1)
    indices = np.clip((values * 16).astype(int), 0, 15)
    counts = np.bincount(indices, minlength=16).astype(np.float32)
    counts = counts / max(1, values.size)
    for index, value in enumerate(counts):
        features[f"hist_gray_{index}"] = float(value)


def add_grid_features(features: dict[str, float], gray: np.ndarray) -> None:
    size = gray.shape[0]
    grid = 4
    cell = size // grid
    for grid_y in range(grid):
        for grid_x in range(grid):
            y_start = grid_y * cell
            y_end = size if grid_y == grid - 1 else (grid_y + 1) * cell
            x_start = grid_x * cell
            x_end = size if grid_x == grid - 1 else (grid_x + 1) * cell
            patch = gray[y_start:y_end, x_start:x_end]
            features[f"grid_mean_{grid_y}_{grid_x}"] = float(patch.mean())
            features[f"grid_std_{grid_y}_{grid_x}"] = float(patch.std())


def symmetry_abs_diff(gray: np.ndarray) -> float:
    left = gray[:, : gray.shape[1] // 2]
    right = np.fliplr(gray[:, -left.shape[1] :])
    return float(np.abs(left - right).mean())


def extract_features(path: Path, model: dict[str, Any]) -> list[float]:
    size = int(model.get("input_size", 96))
    gray = load_xray(path, size)
    values = gray.reshape(-1)
    dx = gray[:-1, 1:] - gray[:-1, :-1]
    dy = gray[1:, :-1] - gray[:-1, :-1]
    edge = np.sqrt(dx * dx + dy * dy)

    features = {
        "mean_gray": float(values.mean()),
        "std_gray": float(values.std()),
        "min_gray": float(values.min()),
        "max_gray": float(values.max()),
        "p10_gray": float(np.percentile(values, 10)),
        "p25_gray": float(np.percentile(values, 25)),
        "p50_gray": float(np.percentile(values, 50)),
        "p75_gray": float(np.percentile(values, 75)),
        "p90_gray": float(np.percentile(values, 90)),
        "dark_ratio": float((values < 0.25).mean()),
        "mid_ratio": float(((values >= 0.25) & (values <= 0.75)).mean()),
        "bright_ratio": float((values > 0.75).mean()),
        "edge_mean": float(edge.mean()),
        "edge_strong_ratio": float((edge > 0.18).mean()),
        "symmetry_abs_diff": symmetry_abs_diff(gray),
    }
    add_histogram(features, gray)
    add_grid_features(features, gray)
    return [float(features.get(name, 0.0)) for name in model["feature_names"]]


def predict_probability(model: dict[str, Any], features: list[float]) -> float:
    logit = float(model["bias"])
    for index, value in enumerate(features):
        scale = float(model["scale"][index]) or 1.0
        normalized = (value - float(model["mean"][index])) / scale
        logit += float(model["weights"][index]) * normalized
    return float(1 / (1 + np.exp(-logit)))


def load_blood_image(path: Path, size: int) -> np.ndarray:
    image = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def extract_blood_features(path: Path, model: dict[str, Any]) -> list[float]:
    size = int(model.get("input_size", 32))
    rgb = load_blood_image(path, size)
    gray = rgb.mean(axis=2)
    values = gray.reshape(-1)
    features: list[float] = rgb.reshape(-1).astype(np.float32).tolist()

    for channel_index in range(3):
        channel = rgb[:, :, channel_index].reshape(-1)
        features.extend(
            [
                float(channel.mean()),
                float(channel.std()),
                float(np.percentile(channel, 10)),
                float(np.percentile(channel, 50)),
                float(np.percentile(channel, 90)),
            ]
        )
        hist = np.bincount(np.clip((channel * 8).astype(int), 0, 7), minlength=8).astype(np.float32)
        hist = hist / max(1, channel.size)
        features.extend(float(value) for value in hist)

    features.extend(
        [
            float(values.mean()),
            float(values.std()),
            float(np.percentile(values, 10)),
            float(np.percentile(values, 50)),
            float(np.percentile(values, 90)),
        ]
    )
    gray_hist = np.bincount(np.clip((values * 12).astype(int), 0, 11), minlength=12).astype(np.float32)
    gray_hist = gray_hist / max(1, values.size)
    features.extend(float(value) for value in gray_hist)

    expected = len(model["mean"])
    if len(features) != expected:
        raise HTTPException(
            status_code=500,
            detail=f"Blood model feature mismatch. Expected {expected}, got {len(features)}.",
        )
    return features


def predict_blood_cell(model: dict[str, Any], features: list[float]) -> dict[str, float]:
    normalized = np.asarray(
        [
            (float(value) - float(model["mean"][index])) / (float(model["scale"][index]) or 1.0)
            for index, value in enumerate(features)
        ],
        dtype=np.float32,
    )
    if model.get("model_type") == "standardized_one_hidden_layer_mlp_blood_cell_features":
        hidden_weights = np.asarray(model["hidden_weights"], dtype=np.float32)
        hidden_bias = np.asarray(model["hidden_bias"], dtype=np.float32)
        output_weights = np.asarray(model["output_weights"], dtype=np.float32)
        output_bias = np.asarray(model["output_bias"], dtype=np.float32)
        hidden = np.maximum(0.0, normalized @ hidden_weights + hidden_bias)
        scores = hidden @ output_weights + output_bias
    else:
        weights = np.asarray(model["weights"], dtype=np.float32)
        bias = np.asarray(model["bias"], dtype=np.float32)
        scores = weights @ normalized + bias
    scores = scores - float(scores.max())
    exp_scores = np.exp(scores)
    probabilities = exp_scores / float(exp_scores.sum())
    return {
        str(label): float(probabilities[index])
        for index, label in enumerate(model["classes"])
    }


def support_from_blood_probabilities(probabilities: dict[str, float]) -> dict[str, int]:
    neutrophil = float(probabilities.get("NEUTROPHIL", 0.0))
    lymphocyte = float(probabilities.get("LYMPHOCYTE", 0.0))
    monocyte = float(probabilities.get("MONOCYTE", 0.0))
    eosinophil = float(probabilities.get("EOSINOPHIL", 0.0))
    bacterial = min(1.0, 0.10 + neutrophil * 0.82 + monocyte * 0.12)
    viral = min(1.0, 0.10 + lymphocyte * 0.72 + monocyte * 0.28)
    other = min(1.0, 0.08 + eosinophil * 0.80)
    return {
        "bacterial_support": round(bacterial * 100),
        "viral_support": round(viral * 100),
        "other_support": round(other * 100),
    }


def blood_guidance_for(probabilities: dict[str, float]) -> dict[str, Any]:
    predicted_cell = max(probabilities, key=probabilities.get)
    confidence = round(float(probabilities[predicted_cell]) * 100)
    support = support_from_blood_probabilities(probabilities)

    if predicted_cell == "NEUTROPHIL":
        result_label = "bacterial-leaning support signal"
        interpretation = (
            "The model sees a neutrophil-like white cell. Neutrophil predominance can support bacterial inflammation, "
            "but it is not enough to determine the infection cause."
        )
    elif predicted_cell == "LYMPHOCYTE":
        result_label = "viral-leaning support signal"
        interpretation = (
            "The model sees a lymphocyte-like white cell. Lymphocyte-heavy patterns can be seen with viral illness, "
            "but clinical context and a real CBC differential are still required."
        )
    elif predicted_cell == "MONOCYTE":
        result_label = "viral/inflammatory support signal"
        interpretation = (
            "The model sees a monocyte-like white cell. This may support an inflammatory or recovery pattern, "
            "but it is not specific for viral or bacterial pneumonia."
        )
    else:
        result_label = "other immune pattern, not specific"
        interpretation = (
            "The model sees an eosinophil-like white cell. Eosinophil-heavy findings are not a direct viral-vs-bacterial clue "
            "and may point to allergic, parasitic, drug-related, or other causes."
        )

    doctor_actions = [
        "Treat this as a blood-cell type classifier plus a support signal, not an infection diagnosis.",
        "Confirm with a real CBC with differential, symptoms, duration of illness, vitals, oxygen saturation, exam, and X-ray review.",
        "Do not start, stop, or withhold antibiotics from this model output alone.",
        "If pneumonia is clinically suspected, use local pneumonia/CAP guidance and consider severity scoring and microbiology testing where indicated.",
        "Escalate urgently for hypoxemia, sepsis concern, shock, severe respiratory distress, altered mental state, or major comorbidity.",
    ]
    evidence = [
        {
            "name": "MedlinePlus WBC and differential",
            "url": "https://medlineplus.gov/lab-tests/white-blood-count-wbc/",
            "note": "Explains WBC count and how differential testing reports white blood cell types.",
        },
        {
            "name": "AAFP leukocytosis review",
            "url": "https://www.aafp.org/pubs/afp/issues/2015/1201/p1004.html",
            "note": "Clinical review of leukocytosis patterns, including neutrophilia and infection context.",
        },
        {
            "name": "NCBI Bookshelf WBC differential",
            "url": "https://www.ncbi.nlm.nih.gov/books/NBK261/",
            "note": "Reference chapter on white blood cells and differential count interpretation.",
        },
    ]
    return {
        "predicted_cell": predicted_cell,
        "confidence": confidence,
        "result_label": result_label,
        "interpretation": interpretation,
        "support": support,
        "doctor_actions": doctor_actions,
        "evidence": evidence,
    }


def guidance_for(probability: float) -> dict[str, Any]:
    threshold = float(load_model().get("threshold", 0.5))
    percent = round(probability * 100)
    if probability >= threshold + 0.15:
        level = "pneumonia-like pattern detected"
        chart = {"today": 100, "care_24_48h": 85, "days_3_5": 65, "follow_up": 75}
        advice = [
            "Review the image quality, view, and clinical story before acting on the AI result.",
            "Check vital signs, oxygen saturation, respiratory distress, confusion, blood pressure, risk factors, and sepsis red flags.",
            "If clinical/radiographic pneumonia is suspected, use local CAP guidance for severity scoring, site-of-care decision, diagnostics, and antimicrobials.",
            "Consider urgent hospital-level review if hypoxemia, shock, severe respiratory distress, altered mental state, or major comorbidity is present.",
            "Document that this is an AI triage signal, not a diagnosis.",
        ]
        doctor_actions = [
            "Correlate the model signal with symptoms and exam findings; pneumonia diagnosis should not be made from AI alone.",
            "Use a validated severity approach such as CRB65/CURB65 plus clinical judgement to decide outpatient vs hospital care.",
            "For suspected adult community-acquired pneumonia, follow ATS/IDSA or local guidelines for cultures, MRSA/Pseudomonas risk review, and empiric antibiotic selection.",
            "Check oxygen saturation and assess for sepsis or respiratory failure before any discharge decision.",
            "Book follow-up or escalation based on clinical severity and response, not the model percentage alone.",
        ]
    elif probability >= threshold:
        level = "possible pneumonia-like pattern"
        chart = {"today": 80, "care_24_48h": 70, "days_3_5": 50, "follow_up": 65}
        advice = [
            "Treat this as uncertain and review symptoms, vitals, and image quality.",
            "Consider repeat/alternate imaging review if the clinical picture is stronger than the AI score.",
            "Use local pneumonia pathways if symptoms and exam support CAP.",
        ]
        doctor_actions = [
            "Re-check image quality and whether the X-ray view is appropriate.",
            "Correlate with cough, fever, pleuritic chest pain, breathlessness, oxygen saturation, and lung exam.",
            "Use severity assessment and local guidance if a clinical diagnosis of CAP is made.",
            "Consider alternate diagnoses if clinical signs do not match pneumonia.",
        ]
    else:
        level = "no strong pneumonia-like pattern"
        chart = {"today": 45, "care_24_48h": 40, "days_3_5": 30, "follow_up": 55}
        advice = [
            "A low model score does not rule out pneumonia.",
            "If symptoms or vitals are concerning, continue clinical review and consider other causes.",
            "Use the AI result only as one supporting signal.",
        ]
        doctor_actions = [
            "Do not use a low AI probability as a rule-out test.",
            "If fever, hypoxemia, focal findings, or high-risk history is present, follow clinical judgement and local pathways.",
            "Consider alternate diagnoses such as viral infection, asthma/COPD flare, pulmonary edema, TB, or noninfectious causes when appropriate.",
        ]
    evidence = [
        {
            "name": "ATS/IDSA adult CAP guideline",
            "url": "https://www.idsociety.org/practice-guideline/community-acquired-pneumonia-cap-in-adults/",
            "note": "Evidence-based adult CAP guidance covering diagnostic testing, site-of-care, empiric treatment, and follow-up decisions.",
        },
        {
            "name": "NICE pneumonia guidance",
            "url": "https://www.nice.org.uk/guidance/ng250/chapter/Recommendations",
            "note": "Uses clinical judgement with CRB65/CURB65 severity assessment for community-acquired pneumonia.",
        },
        {
            "name": "CDC pneumonia resources",
            "url": "https://www.cdc.gov/pneumonia/",
            "note": "Provider resources, risk factors, prevention, and management guideline links.",
        },
        {
            "name": "WHO pneumonia overview",
            "url": "https://www.who.int/health-topics/pneumonia",
            "note": "Global overview of symptoms, risk factors, prevention, treatment concepts, and severe-case hospitalization.",
        },
    ]
    return {
        "level": level,
        "percent": percent,
        "threshold": threshold,
        "chart": chart,
        "advice": advice,
        "doctor_actions": doctor_actions,
        "evidence": evidence,
    }


def blood_gate_for_latest_scan(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    threshold = float(load_model().get("threshold", 0.5))
    latest_scan = conn.execute(
        """
        SELECT id, probability, result_label, created_at
        FROM scans
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    if not latest_scan:
        return {
            "allowed": False,
            "threshold": threshold,
            "reason": "Run an X-ray review first. The blood-cell support input appears only after a pneumonia-like X-ray signal.",
        }

    probability = float(latest_scan["probability"])
    if probability < threshold:
        return {
            "allowed": False,
            "threshold": threshold,
            "latest_scan_id": int(latest_scan["id"]),
            "latest_probability": probability,
            "latest_result_label": latest_scan["result_label"],
            "reason": "The latest X-ray did not show a pneumonia-like pattern, so blood-cell support is hidden for this patient.",
        }

    return {
        "allowed": True,
        "threshold": threshold,
        "latest_scan_id": int(latest_scan["id"]),
        "latest_probability": probability,
        "latest_result_label": latest_scan["result_label"],
        "reason": "The latest X-ray has a pneumonia-like signal, so blood-cell support is available for doctor review.",
    }


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/api/signup")
def signup(payload: AuthRequest) -> dict[str, Any]:
    username = payload.username.strip().lower()
    if username == ADMIN_USERNAME:
        raise HTTPException(status_code=409, detail="That username is reserved for the admin account.")
    salt = secrets.token_hex(16)
    password_hash = hash_password(payload.password, salt)
    try:
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, utc_now()),
            )
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists.")
    return {"token": create_session(user_id), "username": username, "is_admin": False}


@app.post("/api/login")
def login(payload: AuthRequest) -> dict[str, Any]:
    username = payload.username.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    password_hash = hash_password(payload.password, row["salt"])
    if not hmac.compare_digest(password_hash, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    return {"token": create_session(int(row["id"])), "username": username, "is_admin": username == ADMIN_USERNAME}


@app.post("/api/logout")
def logout(user: dict[str, Any] = Depends(require_user)) -> dict[str, str]:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
    return {"ok": "true"}


@app.get("/api/me")
def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"id": user["id"], "username": user["username"], "is_admin": user["is_admin"]}


@app.post("/api/analyze")
async def analyze(
    xray_view: str = Form("unknown"),
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    raise HTTPException(status_code=403, detail="Chest X-ray scanning is only available to the admin/doctor account.")


async def analyze_xray_for_patient(patient_id: int, xray_view: str, file: UploadFile) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, BMP, or TIF X-ray image.")

    saved_name = f"{patient_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(6)}{suffix}"
    saved_path = UPLOAD_DIR / saved_name
    saved_path.write_bytes(await file.read())

    model = load_model()
    features = extract_features(saved_path, model)
    probability = predict_probability(model, features)
    confidence = round(abs(probability - 0.5) * 200)
    guidance = guidance_for(probability)

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scans (user_id, original_name, saved_path, probability, confidence, result_label, xray_view, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                file.filename or "xray",
                str(saved_path),
                probability,
                confidence,
                guidance["level"],
                xray_view,
                utc_now(),
            ),
        )
        scan_id = int(cursor.lastrowid)

    return {
        "scan_id": scan_id,
        "patient_id": patient_id,
        "probability": probability,
        "confidence": confidence,
        "result_label": guidance["level"],
        "xray_view": xray_view,
        "guidance": guidance,
        "created_at": utc_now(),
    }


@app.post("/api/admin/analyze")
async def admin_analyze(
    patient_id: int = Form(...),
    xray_view: str = Form("unknown"),
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    with connect() as conn:
        patient = conn.execute(
            "SELECT id FROM users WHERE id = ? AND username != ?",
            (patient_id, ADMIN_USERNAME),
        ).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return await analyze_xray_for_patient(patient_id, xray_view, file)


@app.post("/api/admin/analyze-blood")
async def admin_analyze_blood(
    patient_id: int = Form(...),
    scan_id: int = Form(...),
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP, BMP, or TIF blood-cell image.")

    with connect() as conn:
        patient = conn.execute(
            "SELECT id FROM users WHERE id = ? AND username != ?",
            (patient_id, ADMIN_USERNAME),
        ).fetchone()
        scan = conn.execute(
            """
            SELECT id, probability, result_label
            FROM scans
            WHERE id = ? AND user_id = ?
            """,
            (scan_id, patient_id),
        ).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    if not scan:
        raise HTTPException(status_code=409, detail="Complete the Doctor Review Workspace X-ray scan before blood support.")

    threshold = float(load_model().get("threshold", 0.5))
    if float(scan["probability"]) < threshold:
        raise HTTPException(
            status_code=409,
            detail="The first X-ray scan did not indicate pneumonia, so the blood sample infection support scan is locked.",
        )

    saved_name = f"blood_{patient_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(6)}{suffix}"
    saved_path = UPLOAD_DIR / saved_name
    saved_path.write_bytes(await file.read())

    model = load_blood_model()
    features = extract_blood_features(saved_path, model)
    probabilities = predict_blood_cell(model, features)
    guidance = blood_guidance_for(probabilities)
    support = guidance["support"]

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO blood_tests (
              user_id, original_name, saved_path, predicted_cell, confidence, result_label,
              probabilities_json, support_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                file.filename or "blood_sample",
                str(saved_path),
                guidance["predicted_cell"],
                guidance["confidence"],
                guidance["result_label"],
                json.dumps(probabilities, sort_keys=True),
                json.dumps(support, sort_keys=True),
                utc_now(),
            ),
        )
        blood_test_id = int(cursor.lastrowid)

    return {
        "blood_test_id": blood_test_id,
        "patient_id": patient_id,
        "scan_id": scan_id,
        "probabilities": probabilities,
        "support": support,
        "predicted_cell": guidance["predicted_cell"],
        "confidence": guidance["confidence"],
        "result_label": guidance["result_label"],
        "guidance": guidance,
        "created_at": utc_now(),
    }


@app.get("/api/scans")
def scans(user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, xray_view, created_at
            FROM scans
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "original_name": "Hidden by admin",
            "probability": 0,
            "confidence": 0,
            "result_label": "Doctor review reference",
            "xray_view": row["xray_view"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@app.post("/api/checkins")
def create_checkin(payload: CheckinRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    with connect() as conn:
        scan = conn.execute(
            "SELECT id FROM scans WHERE id = ? AND user_id = ?",
            (payload.scan_id, user["id"]),
        ).fetchone()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found.")
        cursor = conn.execute(
            """
            INSERT INTO checkins
              (user_id, scan_id, temperature, cough_level, breathing_level, oxygen_level, fluids_note, food_note, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                payload.scan_id,
                payload.temperature,
                payload.cough_level,
                payload.breathing_level,
                payload.oxygen_level,
                payload.fluids_note,
                payload.food_note,
                payload.notes,
                utc_now(),
            ),
        )
    return {"id": int(cursor.lastrowid), "ok": True}


@app.get("/api/checkins")
def list_checkins(scan_id: int | None = None, user: dict[str, Any] = Depends(require_user)) -> list[dict[str, Any]]:
    params: tuple[Any, ...]
    query = """
        SELECT checkins.*
        FROM checkins
        JOIN scans ON scans.id = checkins.scan_id
        WHERE checkins.user_id = ? AND scans.user_id = ?
    """
    params = (user["id"], user["id"])
    if scan_id is not None:
        query += " AND checkins.scan_id = ?"
        params = (user["id"], user["id"], scan_id)
    query += " ORDER BY checkins.id DESC LIMIT 50"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/dashboard")
def dashboard(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    with connect() as conn:
        checkin_count = conn.execute("SELECT COUNT(*) AS count FROM checkins WHERE user_id = ?", (user["id"],)).fetchone()["count"]
    return {
        "scan_count": 0,
        "high_pattern_count": 0,
        "average_probability": 0,
        "checkin_count": checkin_count,
    }


@app.get("/api/mail")
def user_mail(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if user["is_admin"]:
        raise HTTPException(status_code=400, detail="Use the admin dashboard for admin mail.")
    with connect() as conn:
        appointments = conn.execute(
            """
            SELECT id, title, appointment_at, notes, status, created_at
            FROM appointments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
        messages = conn.execute(
            """
            SELECT id, sender, body, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 200
            """,
            (user["id"],),
        ).fetchall()
    return {
        "appointments": [dict(row) for row in appointments],
        "messages": [dict(row) for row in messages],
    }


@app.post("/api/messages")
def send_user_message(payload: UserMessageRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if user["is_admin"]:
        raise HTTPException(status_code=400, detail="Admin messages must choose a patient.")
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (user_id, sender, body, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], "user", payload.body.strip(), utc_now()),
        )
    return {"id": int(cursor.lastrowid), "ok": True}


@app.get("/api/admin/overview")
def admin_overview(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    with connect() as conn:
        users = conn.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE username != ?
            ORDER BY id DESC
            """,
            (ADMIN_USERNAME,),
        ).fetchall()
        rows: list[dict[str, Any]] = []
        total_scans = 0
        total_blood_tests = 0
        high_count_total = 0
        for user_row in users:
            user_id = int(user_row["id"])
            scan_count = conn.execute(
                "SELECT COUNT(*) AS count FROM scans WHERE user_id = ?",
                (user_id,),
            ).fetchone()["count"]
            high_count = conn.execute(
                "SELECT COUNT(*) AS count FROM scans WHERE user_id = ? AND probability >= 0.65",
                (user_id,),
            ).fetchone()["count"]
            latest_scan = conn.execute(
                """
                SELECT id, probability, confidence, result_label, xray_view, created_at
                FROM scans
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            latest_checkin = conn.execute(
                """
                SELECT scan_id, temperature, cough_level, breathing_level, oxygen_level, notes, created_at
                FROM checkins
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            latest_appointment = conn.execute(
                """
                SELECT id, title, appointment_at, notes, status, created_at
                FROM appointments
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            appointment_count = conn.execute(
                "SELECT COUNT(*) AS count FROM appointments WHERE user_id = ?",
                (user_id,),
            ).fetchone()["count"]
            message_count = conn.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE user_id = ?",
                (user_id,),
            ).fetchone()["count"]
            blood_count = conn.execute(
                "SELECT COUNT(*) AS count FROM blood_tests WHERE user_id = ?",
                (user_id,),
            ).fetchone()["count"]
            latest_blood = conn.execute(
                """
                SELECT id, predicted_cell, confidence, result_label, created_at
                FROM blood_tests
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            session_count = conn.execute(
                "SELECT COUNT(*) AS count FROM sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()["count"]

            total_scans += int(scan_count)
            total_blood_tests += int(blood_count)
            high_count_total += int(high_count)
            rows.append(
                {
                    "id": user_id,
                    "username": user_row["username"],
                    "created_at": user_row["created_at"],
                    "active_sessions": session_count,
                    "scan_count": scan_count,
                    "high_pattern_count": high_count,
                    "condition": latest_scan["result_label"] if latest_scan else "No scan yet",
                    "latest_scan": dict(latest_scan) if latest_scan else None,
                    "latest_checkin": dict(latest_checkin) if latest_checkin else None,
                    "latest_blood": dict(latest_blood) if latest_blood else None,
                    "latest_appointment": dict(latest_appointment) if latest_appointment else None,
                    "appointment_count": appointment_count,
                    "message_count": message_count,
                    "blood_count": blood_count,
                }
            )

    return {
        "admin": admin["username"],
        "stats": {
            "patient_count": len(rows),
            "scan_count": total_scans,
            "blood_test_count": total_blood_tests,
            "high_pattern_count": high_count_total,
            "message_count": sum(int(row["message_count"]) for row in rows),
        },
        "users": rows,
    }


@app.get("/api/admin/patient/{user_id}")
def admin_patient(user_id: int, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    with connect() as conn:
        patient = conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ? AND username != ?",
            (user_id, ADMIN_USERNAME),
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")
        scans_rows = conn.execute(
            """
            SELECT id, original_name, probability, confidence, result_label, xray_view, created_at
            FROM scans
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        checkins_rows = conn.execute(
            """
            SELECT id, scan_id, temperature, cough_level, breathing_level, oxygen_level, fluids_note, food_note, notes, created_at
            FROM checkins
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        blood_rows = conn.execute(
            """
            SELECT id, original_name, predicted_cell, confidence, result_label, probabilities_json, support_json, created_at
            FROM blood_tests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        appointment_rows = conn.execute(
            """
            SELECT id, title, appointment_at, notes, status, created_at
            FROM appointments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()
        message_rows = conn.execute(
            """
            SELECT id, sender, body, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 200
            """,
            (user_id,),
        ).fetchall()
        blood_gate = blood_gate_for_latest_scan(conn, user_id)
    blood_tests = []
    for row in blood_rows:
        item = dict(row)
        item["probabilities"] = json.loads(item.pop("probabilities_json") or "{}")
        item["support"] = json.loads(item.pop("support_json") or "{}")
        blood_tests.append(item)

    return {
        "patient": dict(patient),
        "scans": [dict(row) for row in scans_rows],
        "checkins": [dict(row) for row in checkins_rows],
        "blood_tests": blood_tests,
        "blood_gate": blood_gate,
        "appointments": [dict(row) for row in appointment_rows],
        "messages": [dict(row) for row in message_rows],
    }


@app.post("/api/admin/appointments")
def create_admin_appointment(
    payload: AppointmentRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    with connect() as conn:
        patient = conn.execute(
            "SELECT id FROM users WHERE id = ? AND username != ?",
            (payload.user_id, ADMIN_USERNAME),
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")
        cursor = conn.execute(
            """
            INSERT INTO appointments (user_id, admin_id, title, appointment_at, notes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.user_id,
                admin["id"],
                payload.title.strip() or "PneumoScan follow-up",
                payload.appointment_at.strip(),
                payload.notes.strip(),
                payload.status.strip() or "booked",
                utc_now(),
            ),
        )
        conn.execute(
            "INSERT INTO messages (user_id, sender, body, created_at) VALUES (?, ?, ?, ?)",
            (
                payload.user_id,
                "admin",
                f"Appointment booked: {payload.title.strip() or 'PneumoScan follow-up'} at {payload.appointment_at.strip()}. {payload.notes.strip()}".strip(),
                utc_now(),
            ),
        )
    return {"id": int(cursor.lastrowid), "ok": True}


@app.post("/api/admin/messages")
def send_admin_message(
    payload: AdminMessageRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    with connect() as conn:
        patient = conn.execute(
            "SELECT id FROM users WHERE id = ? AND username != ?",
            (payload.user_id, ADMIN_USERNAME),
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")
        cursor = conn.execute(
            "INSERT INTO messages (user_id, sender, body, created_at) VALUES (?, ?, ?, ?)",
            (payload.user_id, "admin", payload.body.strip(), utc_now()),
        )
    return {"id": int(cursor.lastrowid), "ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/app")
def account_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.html")


@app.get("/models/pneumonia_model.json")
def pneumonia_model_file() -> FileResponse:
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=404, detail="Train pneumonia_model.json first.")
    return FileResponse(
        MODEL_PATH,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
