import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.services import embeddings_service


@patch("app.services.embeddings_service.Image")
@patch("app.services.embeddings_service.mtcnn")
@patch("app.services.embeddings_service.face_transform")
@patch("app.services.embeddings_service.model")
def test_extract_embeddings_success(mock_model, mock_transform, mock_mtcnn, mock_image):
    # Mock the image and MTCNN detection
    mock_image.open.return_value.convert.return_value = "mock_image"
    mock_mtcnn.detect.return_value = ([(10, 10, 100, 100)], None)

    # Mock transform and model output
    mock_tensor = MagicMock()
    mock_tensor.unsqueeze.return_value = "unsqueezed"
    mock_transform.return_value = mock_tensor
    mock_model.return_value.detach.return_value.cpu.return_value.numpy.return_value.flatten.return_value = np.ones(512)

    # Patch torch.no_grad to a dummy context
    with patch("torch.no_grad", return_value=MagicMock()) as _:
        result = embeddings_service.extract_embeddings("path/to/image.jpg")

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], list)
    assert len(result[0]) == 512


@patch("app.services.embeddings_service.Image")
@patch("app.services.embeddings_service.mtcnn")
def test_extract_embeddings_no_faces(mock_mtcnn, mock_image):
    mock_image.open.return_value.convert.return_value = "mock_image"
    mock_mtcnn.detect.return_value = (None, None)

    result = embeddings_service.extract_embeddings("path/to/empty.jpg")
    assert result == []


def test_compare_embeddings_match():
    emb1 = np.ones(512)
    emb2 = np.ones(512)
    result = embeddings_service.compare_embeddings(emb1.tolist(), emb2.tolist(), threshold=0.6)
    assert result is True


def test_compare_embeddings_no_match():
    emb1 = np.zeros(512)
    emb2 = np.ones(512)
    result = embeddings_service.compare_embeddings(emb1.tolist(), emb2.tolist(), threshold=0.6)
    assert result is False


def test_compare_embeddings_empty():
    assert embeddings_service.compare_embeddings([], [1]*512) is False
    assert embeddings_service.compare_embeddings([1]*512, []) is False
