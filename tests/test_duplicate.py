import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from bson import ObjectId

from app.services import duplicate


def mock_file_doc(_id, embeddings_id, path="/mock/path/file.jpg", owner_id=None, event_id=None):
    return {
        "_id": _id,
        "embeddings_id": embeddings_id,
        "path": path,
        "owner_id": owner_id if owner_id else ObjectId(),
        "event_id": event_id if event_id else "event123"
    }


def mock_embedding_doc(_id, vector):
    return {
        "_id": _id,
        "embeddings_vector": vector.tolist()
    }


@patch("app.services.duplicate.db")
@patch("app.services.duplicate.np")
def test_get_all_file_embeddings(mock_np, mock_db):
    fake_embedding = np.ones(512)
    mock_np.array.return_value = fake_embedding

    mock_db["file"].find.return_value = [
        mock_file_doc(ObjectId("507f1f77bcf86cd799439011"), ObjectId("507f1f77bcf86cd799439012"))
    ]
    mock_db["embeddings"].find_one.return_value = mock_embedding_doc(ObjectId("507f1f77bcf86cd799439012"), fake_embedding)

    results = duplicate.get_all_file_embeddings("507f1f77bcf86cd799439010", "event123")
    assert len(results) == 1
    assert "file_id" in results[0]
    assert "vector" in results[0]
    assert isinstance(results[0]["vector"], np.ndarray)


@patch("app.services.duplicate.cosine_similarity")
@patch("app.services.duplicate.get_all_file_embeddings")
def test_find_duplicate_files(mock_get_embeddings, mock_cosine_sim):
    emb1 = {"file_id": "1", "vector": np.ones(512), "path": "path1"}
    emb2 = {"file_id": "2", "vector": np.ones(512), "path": "path2"}
    mock_get_embeddings.return_value = [emb1, emb2]
    mock_cosine_sim.return_value = 0.97  # Above threshold

    duplicates = duplicate.find_duplicate_files("user123", "event123")
    assert len(duplicates) == 1
    assert "file_ids" in duplicates[0]
    assert "similarity" in duplicates[0]
    assert duplicates[0]["similarity"] == 0.97


@patch("app.services.duplicate.db")
def test_delete_files(mock_db):
    fid = ObjectId("507f1f77bcf86cd799439011")
    embeddings_id = ObjectId("507f1f77bcf86cd799439012")

    mock_db["file"].find_one.return_value = mock_file_doc(fid, embeddings_id)
    deleted = duplicate.delete_files([str(fid)])

    mock_db["file"].delete_one.assert_called_with({"_id": fid})
    mock_db["embeddings"].delete_one.assert_called_with({"_id": embeddings_id})
    mock_db["chunk"].delete_many.assert_called_with({"file_id": fid})
    mock_db["file_metadata"].delete_one.assert_called_with({"file_id": fid})
    assert deleted == [str(fid)]
