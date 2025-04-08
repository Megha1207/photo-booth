import numpy as np
from app.db import db
from bson import ObjectId
from app.utils import cosine_similarity

DUPLICATE_THRESHOLD = 0.95

def get_all_file_embeddings(user_id=None, event_id=None):
    query = {}
    if user_id:
        query["owner_id"] = ObjectId(user_id)
    if event_id:
        query["event_id"] = event_id

    files = list(db["file"].find(query))
    embeddings = []
    for file in files:
        embedding_doc = db["embeddings"].find_one({"_id": file["embeddings_id"]})
        if embedding_doc:
            embeddings.append({
                "file_id": str(file["_id"]),
                "vector": np.array(embedding_doc["embeddings_vector"]),
                "path": file["path"]
            })
    return embeddings


def find_duplicate_files(user_id=None, event_id=None):
    embeddings = get_all_file_embeddings(user_id, event_id)
    duplicates = []
    visited = set()

    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            file1 = embeddings[i]
            file2 = embeddings[j]
            sim = cosine_similarity(file1["vector"], file2["vector"])

            if sim > DUPLICATE_THRESHOLD:
                key = frozenset([file1["file_id"], file2["file_id"]])
                if key not in visited:
                    visited.add(key)
                    duplicates.append({
                        "file_ids": [file1["file_id"], file2["file_id"]],
                        "similarity": round(sim, 4),
                        "paths": [file1["path"], file2["path"]]
                    })
    return duplicates


def delete_files(file_ids):
    deleted = []
    for fid in file_ids:
        file = db["file"].find_one({"_id": ObjectId(fid)})
        if file:
            db["file"].delete_one({"_id": ObjectId(fid)})
            db["embeddings"].delete_one({"_id": file["embeddings_id"]})
            db["chunk"].delete_many({"file_id": ObjectId(fid)})
            db["file_metadata"].delete_one({"file_id": ObjectId(fid)})
            deleted.append(str(fid))
    return deleted
