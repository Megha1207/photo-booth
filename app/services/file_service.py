import os
import io
import numpy as np
import hashlib
from PIL import Image, UnidentifiedImageError  
from fastapi import UploadFile, HTTPException
from bson import ObjectId
from app.db import db
from app.config import Config
from app.services.chunk_service import chunk_image_bytes, reconstruct_file_from_chunks
from app.services.embedding_service import extract_embeddings
from bson.json_util import dumps
from app.services import face_service
from fastapi.responses import FileResponse, JSONResponse

def get_next_sequence(name: str) -> int:
    counter = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

# async def handle_file_upload(upload_file: UploadFile, user_id: str, event_id: str):
#     try:
#         valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'svg']
#         file_extension = os.path.splitext(upload_file.filename)[-1].lower()[1:]

#         if file_extension not in valid_extensions:
#             raise HTTPException(status_code=400, detail="Unsupported file type")

#         file_bytes = await upload_file.read()

#         event_folder = os.path.join(Config.LOCAL_STORAGE_PATH, f"event_{event_id}")
#         os.makedirs(event_folder, exist_ok=True)

#         filename = f"{ObjectId()}_{upload_file.filename}"
#         local_path = os.path.join(event_folder, filename)
#         with open(local_path, "wb") as f:
#             f.write(file_bytes)

#         chunks = chunk_image_bytes(file_bytes)
#         chunk_ids = []
#         for index, chunk_data in enumerate(chunks):
#             chunk_id = ObjectId()
#             db.chunks.insert_one({
#                 "_id": chunk_id,
#                 "file_id": None,
#                 "chunk_index": index,
#                 "chunk_data": chunk_data
#             })
#             chunk_ids.append(chunk_id)

#         try:
#             image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
#             embeddings = extract_embeddings(image)
#         except UnidentifiedImageError:
#             embeddings = []
#         except Exception as e:
#             print("[Embedding Error]:", str(e))
#             embeddings = []

#         if isinstance(embeddings, np.ndarray):
#             embeddings = [embeddings.tolist()]
#         elif isinstance(embeddings, list):
#             embeddings = [e.tolist() if isinstance(e, np.ndarray) else e for e in embeddings]
#         else:
#             embeddings = []

#         next_file_id = get_next_sequence("file_id")
#         file_doc = {
#             "_id": next_file_id,
#             "filename": upload_file.filename,
#             "path": local_path,
#             "file_version": 1,
#             "owner_id": ObjectId(user_id),
#             "event_id": event_id,
#             "embeddings_id": None
#         }
#         db.files.insert_one(file_doc)

#         embedding_doc = {
#             "embeddings_vector": embeddings,
#             "file_id": next_file_id
#         }
#         embedding_id = db.embeddings.insert_one(embedding_doc).inserted_id

#         db.files.update_one(
#             {"_id": next_file_id},
#             {"$set": {"embeddings_id": embedding_id}}
#         )

#         db.chunks.update_many(
#             {"_id": {"$in": chunk_ids}},
#             {"$set": {"file_id": next_file_id}}
#         )

#         return {
#             "status": "success",
#             "file_id": str(next_file_id),
#             "filename": upload_file.filename,
#             "path": local_path,
#             "event_folder": event_folder,
#             "embedding_status": "created" if embeddings else "not created"
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

async def handle_file_upload(upload_file: UploadFile, user_id: str, event_id: str):
    try:
        # Validate file type
        valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'svg']
        file_extension = os.path.splitext(upload_file.filename)[-1].lower()[1:]
        
        if file_extension not in valid_extensions:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Read file content
        file_bytes = await upload_file.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check for existing file with same hash and same user (just for tracking)
        existing_file = db.files.find_one({
            "owner_id": ObjectId(user_id),
            "content_hash": file_hash
        })
        
        is_duplicate = existing_file is not None

        # Create event folder if not exists
        event_folder = os.path.join(Config.LOCAL_STORAGE_PATH, f"event_{event_id}")
        os.makedirs(event_folder, exist_ok=True)

        # Generate unique filename even for duplicates
        filename = f"{ObjectId()}_{upload_file.filename}"
        local_path = os.path.join(event_folder, filename)
        
        # Save file locally
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        # Chunking logic (unchanged)
        chunks = chunk_image_bytes(file_bytes)
        chunk_ids = []
        for index, chunk_data in enumerate(chunks):
            chunk_id = ObjectId()
            db.chunks.insert_one({
                "_id": chunk_id,
                "file_id": None,
                "chunk_index": index,
                "chunk_data": chunk_data
            })
            chunk_ids.append(chunk_id)

        # Embedding extraction (unchanged)
        try:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            embeddings = extract_embeddings(image)
        except UnidentifiedImageError:
            embeddings = []
        except Exception as e:
            print("[Embedding Error]:", str(e))
            embeddings = []

        if isinstance(embeddings, np.ndarray):
            embeddings = [embeddings.tolist()]
        elif isinstance(embeddings, list):
            embeddings = [e.tolist() if isinstance(e, np.ndarray) else e for e in embeddings]
        else:
            embeddings = []

        # Get next file ID
        next_file_id = get_next_sequence("file_id")

        # Create file document with duplicate info
        file_doc = {
            "_id": next_file_id,
            "filename": upload_file.filename,
            "path": local_path,
            "file_version": 1,
            "owner_id": ObjectId(user_id),
            "event_id": event_id,
            "embeddings_id": None,
            "content_hash": file_hash,
            "is_duplicate": is_duplicate,
            "original_file_id": existing_file["_id"] if is_duplicate else None,
            "duplicate_upload_time": datetime.utcnow() if is_duplicate else None
        }

        db.files.insert_one(file_doc)

        # Create embedding document
        embedding_doc = {
            "embeddings_vector": embeddings,
            "file_id": next_file_id
        }
        embedding_id = db.embeddings.insert_one(embedding_doc).inserted_id

        # Update file with embedding ID
        db.files.update_one(
            {"_id": next_file_id},
            {"$set": {"embeddings_id": embedding_id}}
        )

        # Update chunks with file ID
        db.chunks.update_many(
            {"_id": {"$in": chunk_ids}},
            {"$set": {"file_id": next_file_id}}
        )

        return {
            "status": "success",
            "file_id": str(next_file_id),
            "filename": upload_file.filename,
            "path": local_path,
            "is_duplicate": is_duplicate,
            "original_file_id": str(existing_file["_id"]) if is_duplicate else None,
            "embedding_status": "created" if embeddings else "not created"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# Fetch files associated with a specific event and display in a gallery format
def get_files_by_event(event_id: str):
    files = db.files.find({"event_id": event_id})
    result = []

    for file in files:
        filename = os.path.basename(file["path"])
        if filename.lower().endswith(('jpg', 'jpeg', 'png', 'gif', 'bmp', 'heic')):
            result.append({
                "file_id": file["_id"],
                "filename": filename,
                "url": f"/files/{filename}",
                "delete_url": f"/delete/{file['_id']}",  # URL to delete the file
            })

    return result

# Fetch all files uploaded by a user
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

# Endpoint to delete a file (gallery delete option)
def delete_user_file(file_id: str, user_id: str):
    try:
        file_id = ObjectId(file_id)
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

    return {"status": "success", "deleted_file_id": str(file_id)}

def serve_file(filename: str):
    try:
        file_path = os.path.join(Config.LOCAL_STORAGE_PATH, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")