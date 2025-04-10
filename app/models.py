from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ---------- USER MODELS ----------

class User(BaseModel):
    user_id: str
    user_name: str
    email: EmailStr


class UserAuth(BaseModel):
    user_id: str
    password: str
    last_sign_in: Optional[datetime]
    device_id: Optional[str]


# ---------- DEVICE MODEL ----------

class Device(BaseModel):
    device_id: str
    user_id: str


# ---------- FILE MODELS ----------

class File(BaseModel):
    file_id: str
    path: str
    file_version: int
    owner_id: str
    embeddings_id: Optional[str]
    event_id: Optional[str]


class FileMetadata(BaseModel):
    file_id: str
    metadata: dict


class FileVersion(BaseModel):
    version_id: str
    file_id: str
    version_number: int


# ---------- CHUNK MODEL ----------

class Chunk(BaseModel):
    chunk_id: str
    file_id: str
    chunk_index: int
    chunk_data: Any


# ---------- FACE MODELS ----------

class Face(BaseModel):
    face_id: str
    path: str
    owner_id: str
    embeddings_id: Optional[str]
    event_id: Optional[str]


class FaceMetadata(BaseModel):
    face_id: str
    metadata: dict


# ---------- EMBEDDING MODEL ----------

class Embedding(BaseModel):
    embeddings_id: str
    embeddings_vector: List[float]
    face_id: Optional[str] = None
    file_id: Optional[str] = None


# ---------- AUTH TOKENS (OPTIONAL) ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ---------- DUPLICATE RESPONSE ----------

class DuplicateGroup(BaseModel):
    duplicate_files: List[str]
    similarity: float
