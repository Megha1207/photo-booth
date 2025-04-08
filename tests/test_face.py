# test_face_service.py

import pytest
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
from bson import ObjectId
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services import face_service


@pytest.fixture
def dummy_file_bytes():
    return b"dummy image data"


@pytest.fixture
def dummy_embedding():
    return np.random.rand(512).tolist()


@patch("app.services.face_service.save_face_locally")
@patch("app.services.face_service.extract_face_embeddings")
@patch("app.services.face_service.db")
def test_handle_face_upload_success(mock_db, mock_extract, mock_save, dummy_file_bytes, dummy_embedding):
    mock_save.return_value = "/path/to/image.jpg"
    mock_extract.return_value = np.array(dummy_embedding)
    mock_db.embeddings.insert_one.return_value.inserted_id = ObjectId("5f43a2b4e1d3e3a1a8a8a8a8")
    mock_db.faces.insert_one.return_value.inserted_id = ObjectId("5f43a2b4e1d3e3a1a8a8a8a9")

    face_id = face_service.handle_face_upload(dummy_file_bytes, "test.jpg", "5f43a2b4e1d3e3a1a8a8a8b1", "event123")

    assert face_id is not None


@patch("app.services.face_service.db")
def test_get_face_embedding_by_id_success(mock_db, dummy_embedding):
    face_id = str(ObjectId())
    embedding_id = ObjectId()

    mock_db.faces.find_one.return_value = {
        "_id": ObjectId(face_id),
        "embeddings_id": embedding_id
    }
    mock_db.embeddings.find_one.return_value = {
        "_id": embedding_id,
        "embeddings_vector": dummy_embedding
    }

    result = face_service.get_face_embedding_by_id(face_id)
    assert result == dummy_embedding


@patch("app.services.face_service.db")
def test_get_face_embedding_by_id_invalid(mock_db):
    result = face_service.get_face_embedding_by_id("invalid_id")
    assert result is None


@patch("app.services.face_service.os.path.exists", return_value=True)
@patch("app.services.face_service.get_face_embedding_by_id")
@patch("app.services.face_service.db")
@patch("app.services.face_service.open", new_callable=mock_open, read_data=b"image content")
def test_match_face_with_files(mock_open_file, mock_db, mock_get_embed, mock_exists, dummy_embedding):
    mock_get_embed.return_value = dummy_embedding
    file_id = ObjectId()
    db_embedding = np.random.rand(512).tolist()

    mock_db.files.find.return_value = [{"_id": file_id, "path": "/fake/path.jpg", "event_id": "event123"}]
    mock_db.embeddings.find_one.return_value = {"file_id": file_id, "embeddings_vector": db_embedding}

    response = face_service.match_face_with_files(str(ObjectId()), "event123")

    assert isinstance(response, face_service.StreamingResponse)


@patch("app.services.face_service.extract_face_embeddings")
@patch("app.services.face_service.db")
def test_store_file_embedding(mock_db, mock_extract, dummy_embedding):
    file_id = ObjectId()
    mock_extract.return_value = np.array(dummy_embedding)

    face_service.store_file_embedding("/path/to/image.jpg", file_id)

    mock_db.embeddings.insert_one.assert_called_once()
