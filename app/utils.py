import hashlib
import os
import uuid
import logging
import numpy as np
from typing import List
from fastapi import HTTPException
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt


# ---------- LOGGING SETUP ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- HASHING ----------

def generate_file_hash(file_path: str) -> str:
    """Generate SHA256 hash for a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def generate_chunk_hash(data: bytes) -> str:
    """Generate SHA256 hash for a chunk."""
    return hashlib.sha256(data).hexdigest()


# ---------- ID GENERATION ----------

def generate_id(prefix: str = "") -> str:
    return f"{prefix}_{uuid.uuid4().hex}" if prefix else uuid.uuid4().hex


# ---------- VALIDATION ----------

def validate_event_id(event_id: str):
    if not event_id or not isinstance(event_id, str):
        raise HTTPException(status_code=400, detail="Invalid event ID")


# ---------- VECTOR UTILS ----------

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot / (norm_v1 * norm_v2 + 1e-10)


# ---------- FILE UTILS ----------

def save_file(file_data: bytes, save_path: str):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(file_data)
    logger.info(f"Saved file to {save_path}")


# Setup for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key & algorithm (ideally should be stored in env vars)
SECRET_KEY = "your-secret-key"  # 🔐 replace with secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ---------- PASSWORD UTILS ----------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ---------- JWT TOKEN UTILS ----------

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
