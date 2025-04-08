import os
import hashlib
from PIL import Image
import torch
import numpy as np
from facenet_pytorch import InceptionResnetV1, MTCNN
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId
from sklearn.metrics.pairwise import cosine_similarity
import base64
from app.config import Config
from app.db import db
from typing import Union, List

# ========== Initialize Models ==========
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = InceptionResnetV1(pretrained=None).to(device)
model.load_state_dict(torch.load(Config.MODEL_PATH, map_location=device), strict=False)
model.eval()
mtcnn = MTCNN(keep_all=True, device=device)

# ========== Helpers ==========

def get_next_sequence(name: str) -> int:
    counter = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def save_face_locally(file: bytes, filename: str) -> str:
    path = os.path.join(Config.LOCAL_STORAGE_PATH, 'faces')
    os.makedirs(path, exist_ok=True)
    full_path = os.path.join(path, filename)
    with open(full_path, 'wb') as f:
        f.write(file)
    return full_path

def extract_face_embeddings(image_path: str, return_all=False) -> Union[np.ndarray, List[np.ndarray], None]:
    image = Image.open(image_path).convert('RGB')
    boxes, _ = mtcnn.detect(image)

    if boxes is None or len(boxes) == 0:
        return None

    embeddings = []
    for box in boxes:
        (x1, y1, x2, y2) = box
        face = image.crop((int(x1), int(y1), int(x2), int(y2)))
        face = face.resize((160, 160))
        face_tensor = torch.tensor(np.array(face)).permute(2, 0, 1).float().div(255).unsqueeze(0).to(device)

        with torch.no_grad():
            embedding = model(face_tensor).cpu().numpy().flatten()
        embeddings.append(embedding)

        if not return_all:
            break

    return embeddings if return_all else embeddings[0]

# ========== Core Service ==========

def handle_face_upload(file: bytes, filename: str, owner_id: str, event_id: str) -> Union[str, None]:
    file_path = save_face_locally(file, filename)
    file_hash = hashlib.sha256(file).hexdigest()
    embedding_vectors = extract_face_embeddings(file_path, return_all=True)

    if not embedding_vectors:
        return None

    next_face_id = get_next_sequence("face_id")

    face_doc = {
        "_id": next_face_id,
        "path": file_path,
        "file_hash": file_hash,
        "owner_id": ObjectId(owner_id),
        "embeddings_id": None,
        "event_id": event_id
    }
    db.faces.insert_one(face_doc)

    embedding_doc = {
        "embeddings_vector": [vec.tolist() for vec in embedding_vectors],  # Store list of embeddings
        "face_id": next_face_id
    }
    embedding_id = db.embeddings.insert_one(embedding_doc).inserted_id

    db.faces.update_one(
        {"_id": next_face_id},
        {"$set": {"embeddings_id": embedding_id}}
    )

    return str(next_face_id)


def get_face_embedding_by_id(face_id: str) -> Union[List[float], None]:
    try:
        face_id = int(face_id)
    except ValueError:
        print(f"[get_face_embedding_by_id] Invalid face_id format.")
        return None

    face = db.faces.find_one({"_id": face_id})
    if face and face.get("embeddings_id"):
        embedding = db.embeddings.find_one({"_id": face["embeddings_id"]})
        if embedding:
            return embedding["embeddings_vector"]
    return None



def match_face_with_files(face_id: str, event_id: str):
    query_embedding = get_face_embedding_by_id(face_id)
    if query_embedding is None or len(query_embedding) == 0:
        raise HTTPException(status_code=404, detail="Face embedding not found or empty.")

    query_embedding = np.array(query_embedding).reshape(1, -1)
    if query_embedding.shape[1] == 0:
        raise HTTPException(status_code=400, detail="Query embedding has zero features.")

    files = db.files.find({"event_id": event_id})
    threshold = 0.6  # Similarity threshold

    matched_images = []

    for file_doc in files:
        embedding_data = db.embeddings.find_one({"file_id": file_doc["_id"]})
        if not embedding_data:
            continue

        embeddings_list = embedding_data.get("embeddings_vector")
        if not embeddings_list:
            continue

        for emb in embeddings_list:
            db_embedding = np.array(emb).reshape(1, -1)
            if db_embedding.shape[1] != query_embedding.shape[1]:
                continue

            similarity = cosine_similarity(query_embedding, db_embedding)[0][0]

            if similarity >= threshold:
                try:
                    with open(file_doc["path"], "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                        matched_images.append({
                            "image_base64": encoded,
                            "similarity": similarity
                        })
                    break  # One match per file is enough
                except Exception as e:
                    print(f"Error reading file {file_doc['path']}: {e}")
                continue

    if not matched_images:
        raise HTTPException(status_code=404, detail="No matching image found above the threshold.")

    return {"matched_images": matched_images}






