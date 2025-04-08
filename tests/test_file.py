# test_file_service.py

import pytest
from unittest.mock import patch, MagicMock, mock_open
from bson import ObjectId
from fastapi import UploadFile
from io import BytesIO
import numpy as np

from app.services import file_service


class DummyUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


@pytest.fixture
def dummy_file():
    return DummyUploadFile("D:/photobooth/app/storage/faces/1.jpg", b"fake-image-bytes")


@pytest.fixture
def dummy_chunks():
    return [b"chunk1", b"chunk2", b"chunk3"]


@pytest.fixture
def dummy_embeddings():
    return np.random.rand(512)


@patch("app.services.file_service.extract_embeddings")
@patch("app.services.file_service.chunk_image")
@patch("app.services.file_service.db")
@patch("app.services.file_service.open", new_callable=mock_open)
@patch("app.services.file_service.Image.open")
@pytest.mark.asyncio
async def test_handle_file_upload_success(
    mock_image_open,
    mock_open_file,
    mock_db,
    mock_chunk_image,
    mock_extract_embeddings,
    dummy_file,
    dummy_chunks,
    dummy_embeddings
):
    # Mocks
    mock_chunk_image.return_value = dummy_chunks
    mock_extract_embeddings.return_value = dummy_embeddings
    mock_image_open.return_value = MagicMock()

    mock_db.files.insert_one.return_value.inserted_id = ObjectId()
    mock_db.embeddings.insert_one.return_value.inserted_id = ObjectId()

    mock_db.chunks.insert_one.side_effect = lambda doc: doc["_id"]

    result = await file_service.handle_file_upload(dummy_file, str(ObjectId()), "event123")

    assert "file_id" in result
    assert "path" in result
    assert isinstance(result["file_id"], str)
    assert result["path"].endswith(dummy_file.filename)


@patch("app.services.file_service.extract_embeddings")
@patch("app.services.file_service.chunk_image")
@patch("app.services.file_service.db")
@patch("app.services.file_service.open", new_callable=mock_open)
@patch("app.services.file_service.Image.open", side_effect=Exception("Not an image"))
@pytest.mark.asyncio
async def test_handle_file_upload_non_image(
    mock_image_open,
    mock_open_file,
    mock_db,
    mock_chunk_image,
    mock_extract_embeddings,
    dummy_file,
    dummy_chunks
):
    mock_chunk_image.return_value = dummy_chunks
    mock_extract_embeddings.return_value = []

    mock_db.files.insert_one.return_value.inserted_id = ObjectId()
    mock_db.embeddings.insert_one.return_value.inserted_id = ObjectId()

    result = await file_service.handle_file_upload(dummy_file, str(ObjectId()), "event123")

    assert "file_id" in result
    assert "path" in result
