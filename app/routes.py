from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi import Depends
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from bson import ObjectId
import base64
import os
from fastapi import Request

from app.services import (
    file_service,
    face_service,
    search_service,
    user_service,
    duplicate_service,
    chunk_service
)
from app.db import db
from app.services.user_service import get_current_user_id

router = APIRouter()


# ------------------ File Upload ------------------

@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    event_id: str = Form(...),
    user_id: str = Form(...)
):
    return await file_service.handle_file_upload(file, user_id, event_id)


# ------------------ Face Upload ------------------

@router.post("/upload/face")
async def upload_face(
    face: UploadFile = File(...),
    user_id: str = Form(...),
    event_id: str = Form(...)
):
    file_bytes = await face.read()
    filename = face.filename

    # Save face and return DB face_id
    result = face_service.handle_face_upload(file_bytes, filename, user_id, event_id)

    if result is None:
        return {"error": "No face detected in the image."}

    # Convert image bytes to base64
    base64_image = base64.b64encode(file_bytes).decode("utf-8")

    return {
        "face_id": str(result),
        "base64_image": base64_image
    }


# ------------------ Chunk Upload ------------------

@router.post("/upload/chunked-file")
async def upload_chunked_file(
    file: UploadFile = File(...),
    event_id: str = Form(...),
    user_id: str = Form(...)
):
    # Save file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    chunks = chunk_service.chunk_image(temp_path)
    file_doc = file_service.save_file_metadata(file.filename, user_id, event_id)
    chunk_ids = chunk_service.save_chunks(file_doc["_id"], chunks)

    os.remove(temp_path)

    return {
        "file_id": str(file_doc["_id"]),
        "chunk_count": len(chunk_ids)
    }


# ------------------ Chunk Reconstruct ------------------

@router.get("/reconstruct-file/{file_id}")
def reconstruct_file(file_id: str):
    file_doc = db.files.find_one({"_id": ObjectId(file_id)})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    output_path = f"/tmp/reconstructed_{file_doc['filename']}"
    chunk_service.reconstruct_file_from_chunks(ObjectId(file_id), output_path)

    return FileResponse(path=output_path, filename=file_doc["filename"])


# ------------------ Face-File Matching ------------------

@router.post("/match-face")
async def match_face(
    face_id: str = Form(...),
    event_id: str = Form(...)
):
    return face_service.match_face_with_files(face_id, event_id)


# ------------------ Search by Event ------------------

@router.get("/search/event/{event_id}")
async def search_by_event(event_id: str):
    return search_service.search_files_by_event(event_id)


# ------------------ Duplicate Detection ------------------

@router.get("/duplicates/")
async def find_duplicates(user_id: str = None, event_id: str = None):
    duplicates = duplicate_service.find_duplicate_files(user_id, event_id)
    return {"duplicates": duplicates}


@router.delete("/duplicates/")
async def delete_duplicates(file_ids: List[str]):
    if not file_ids:
        raise HTTPException(status_code=400, detail="file_ids list is required.")
    deleted = duplicate_service.delete_files(file_ids)
    return {"deleted_file_ids": deleted}


# ------------------ User Registration ------------------

@router.post("/register")
def register(
    user_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    device_id: str = Form(None)
):
    try:
        user_id = user_service.create_user(user_name, email, password, device_id)
        return {"user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------ User Login ------------------

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_result = user_service.authenticate_user(form_data.username, form_data.password)
    if not auth_result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, user = auth_result

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_name": user["user_name"],
        "user_id": str(user["_id"])
    }


# ------------------ Get File by ID ------------------

@router.get("/get-file/{file_id}")
def get_file(file_id: str):
    file_doc = db.files.find_one({"_id": ObjectId(file_id)})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_doc["path"])


@router.get("/my-files")
async def get_my_files(user_id: str = Depends(get_current_user_id)):
    return file_service.get_files_by_user(user_id)
@router.delete("/delete-files/")
async def delete_files(request: Request, user_id: str = Depends(get_current_user_id)):
    body = await request.json()
    file_ids = body.get("file_ids", [])
    return file_service.delete_files_by_ids(file_ids, user_id)


@router.delete("/delete-file/{file_id}")
async def delete_my_file(file_id: str, user_id: str = Depends(get_current_user_id)):
    return file_service.delete_user_file(file_id, user_id)
