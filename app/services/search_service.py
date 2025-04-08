# app/services/search_service.py

import numpy as np
from typing import List, Dict
from bson import ObjectId

from app.db import db
from app.services.face_service import get_face_embedding_by_id


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_files_by_face(face_id: str, similarity_threshold: float = 0.7) -> List[Dict]:
    """
    Find files with embeddings similar to the given face within the same event.
    Returns a list of matching file metadata.
    """
    # Fetch the face document
    face_doc = db.faces.find_one({"_id": ObjectId(face_id)})
    if not face_doc:
        return []

    event_id = face_doc["event_id"]
    face_embedding = get_face_embedding_by_id(face_id)
    if face_embedding is None:
        return []

    matching_files = []

    # Fetch all file embeddings with matching event_id
    file_cursor = db.files.find({"event_id": event_id})

    for file_doc in file_cursor:
        file_id = file_doc["_id"]

        # Try to get the embedding_id from the file document
        embedding_id = file_doc.get("embeddings_id")

        # If missing, fall back to embeddings collection using file_id
        if not embedding_id:
            embedding_doc = db.embeddings.find_one({"file_id": file_id})
        else:
            embedding_doc = db.embeddings.find_one({"_id": embedding_id})

        if not embedding_doc:
            continue

        file_embedding = embedding_doc["embeddings_vector"]
        similarity = cosine_similarity(face_embedding, file_embedding)

        if similarity >= similarity_threshold:
            matching_files.append({
                "file_id": str(file_id),
                "path": file_doc["path"],
                "similarity": similarity
            })

    # Sort results by highest similarity first
    return sorted(matching_files, key=lambda x: x["similarity"], reverse=True)
