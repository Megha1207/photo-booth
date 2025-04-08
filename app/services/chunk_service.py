# app/services/chunk_service.py

import os
from bson import ObjectId
from app.db import db
from typing import BinaryIO, Union

CHUNK_SIZE = 1024 * 512  # 512 KB


def chunk_image(file_path: str, chunk_size: int = CHUNK_SIZE) -> list:
    """
    Splits the image file on disk into byte chunks for storage.
    Returns a list of byte chunks.
    """
    chunks = []
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
    return chunks


def chunk_image_file(file_obj: BinaryIO, chunk_size: int = CHUNK_SIZE) -> list:
    """
    Splits a file-like object into byte chunks.
    Useful for in-memory or streamed files (e.g. cloud uploads).
    """
    chunks = []
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
    file_obj.seek(0)  # Reset pointer if needed
    return chunks


def chunk_image_bytes(file_bytes: bytes, chunk_size: int = CHUNK_SIZE) -> list:
    """
    Splits a bytes object into chunks.
    Useful for directly uploaded files in memory.
    """
    return [file_bytes[i:i + chunk_size] for i in range(0, len(file_bytes), chunk_size)]


def save_chunks(file_id: Union[int, str], chunks: list) -> list:
    """
    Saves byte chunks into MongoDB `chunks` collection.
    """
    chunk_ids = []
    for index, chunk_data in enumerate(chunks):
        chunk_id = ObjectId()
        db.chunks.insert_one({
            "_id": chunk_id,
            "file_id": file_id,
            "chunk_index": index,
            "chunk_data": chunk_data,
        })
        chunk_ids.append(chunk_id)
    return chunk_ids


def reconstruct_file_from_chunks(file_id: Union[int, str], output_path: str) -> str:
    """
    Reassembles and writes the file from chunks based on `file_id`.
    Returns the path to the reconstructed file.
    """
    chunks = db.chunks.find({"file_id": file_id}).sort("chunk_index", 1)

    with open(output_path, "wb") as output_file:
        for chunk in chunks:
            output_file.write(chunk["chunk_data"])

    return output_path
