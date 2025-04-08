# app/services/file_service.py

import os
import hashlib
import io
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, HTTPException
from bson import ObjectId
import numpy as np
from app.db import db
from app.config import Config
from app.services.chunk_service import chunk_image_bytes, reconstruct_file_from_chunks
from app.services.embedding_service import extract_embeddings
from bson.json_util import dumps
from app.services import face_service

# ---------- Auto-Increment ID Generator ----------
def get_next_sequence(name: str) -> int:
    counter = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]


# ---------- Handle File Upload ----------
async def handle_file_upload(upload_file: UploadFile, user_id: str, event_id: str):
    file_bytes = await upload_file.read()

    filename = f"{ObjectId()}_{upload_file.filename}"
    local_path = os.path.join(Config.LOCAL_STORAGE_PATH, filename)

    # Save file locally (optional, can be removed if using only cloud)
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # --- Use in-memory chunking (cloud-compatible) ---
    chunks = chunk_image_bytes(file_bytes)
    chunk_ids = []
    for index, chunk_data in enumerate(chunks):
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        chunk_id = ObjectId()
        db.chunks.insert_one({
            "_id": chunk_id,
            "file_id": None,
            "chunk_index": index,
            "chunk_hash": chunk_hash,
            "chunk_data": chunk_data
        })
        chunk_ids.append(chunk_id)

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image = image.convert("RGB")
        embeddings = extract_embeddings(image)
    except UnidentifiedImageError:
        image = None
        embeddings = []
    except Exception as e:
        print("[Embedding Extraction Error]", e)
        embeddings = []

    if isinstance(embeddings, np.ndarray):
        embeddings = [embeddings.tolist()]
    elif isinstance(embeddings, list):
        embeddings = [e.tolist() if isinstance(e, np.ndarray) else e for e in embeddings]
    else:
        embeddings = []

    next_file_id = get_next_sequence("file_id")

    file_doc = {
        "_id": next_file_id,
        "path": local_path,
        "file_version": 1,
        "file_hash": file_hash,
        "owner_id": ObjectId(user_id),
        "embeddings_id": None,
        "event_id": event_id
    }
    db.files.insert_one(file_doc)

    embedding_doc = {
        "embeddings_vector": embeddings,
        "file_id": next_file_id
    }
    embedding_result = db.embeddings.insert_one(embedding_doc)
    embedding_id = embedding_result.inserted_id

    db.files.update_one(
        {"_id": next_file_id},
        {"$set": {"embeddings_id": embedding_id}}
    )

    db.chunks.update_many(
        {"_id": {"$in": chunk_ids}},
        {"$set": {"file_id": next_file_id}}
    )

    return {"file_id": str(next_file_id), "path": local_path}

# ---------- Get Files by User ----------
def get_files_by_user(user_id: str):
    files = db.files.find({"owner_id": ObjectId(user_id)})
    result = []
    for file in files:
        result.append({
            "file_id": file["_id"],
            "filename": os.path.basename(file["path"]),
            "event_id": file.get("event_id"),
            "path": file["path"],
        })
    return result

# ---------- Delete File ----------
def delete_user_file(file_id: str, user_id: str):
    try:
        file_id = int(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file_id format")

    file_doc = db.files.find_one({"_id": file_id})

    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    if str(file_doc["owner_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Unauthorized to delete this file")

    try:
        if os.path.exists(file_doc["path"]):
            os.remove(file_doc["path"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

    db.files.delete_one({"_id": file_id})
    db.embeddings.delete_many({"file_id": file_id})
    db.chunks.delete_many({"file_id": file_id})

    return {"deleted_file_id": file_id}

# ---------- Reconstruct File ----------
def reconstruct_file(file_id: int, output_path: str):
    return reconstruct_file_from_chunks(file_id, output_path, db)

# ---------- Store File Embedding ----------
def store_file_embedding(file_path: str, file_id: ObjectId):
    embeddings = face_service.extract_face_embeddings(file_path, return_all=True)

    if isinstance(embeddings, np.ndarray):
        embeddings = [embeddings.tolist()]
    elif isinstance(embeddings, list):
        embeddings = [e.tolist() if isinstance(e, np.ndarray) else e for e in embeddings]
    else:
        embeddings = []

    if embeddings:
        embedding_id = db.embeddings.insert_one({
            "embeddings_vector": embeddings,
            "file_id": file_id
        }).inserted_id

        db.files.update_one({"_id": file_id}, {"$set": {"embeddings_id": embedding_id}})
