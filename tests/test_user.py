import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.services import user_service


@pytest.fixture
def mock_user_data():
    return {
        "user_name": "testuser",
        "email": "test@example.com",
        "password": "securepass123"
    }


@patch("app.services.user_service.hash_password")
@patch("app.services.user_service.db")
def test_create_user(mock_db, mock_hash_password, mock_user_data):
    mock_hash_password.return_value = "hashed_pw"
    mock_db.users.insert_one.return_value = None
    mock_db.user_auth.insert_one.return_value = None

    user_id = user_service.create_user(
        mock_user_data["user_name"],
        mock_user_data["email"],
        mock_user_data["password"]
    )

    assert user_id == mock_user_data["user_name"]
    mock_hash_password.assert_called_once_with(mock_user_data["password"])


@patch("app.services.user_service.verify_password")
@patch("app.services.user_service.create_access_token")
@patch("app.services.user_service.db")
def test_authenticate_user_success(mock_db, mock_create_token, mock_verify_password, mock_user_data):
    user_doc = {
        "user_name": mock_user_data["user_name"],
        "email": mock_user_data["email"].lower()
    }
    auth_doc = {
        "user_id": mock_user_data["user_name"],
        "password": "hashed_pw"
    }

    mock_db.users.find_one.return_value = user_doc
    mock_db.user_auth.find_one.return_value = auth_doc
    mock_verify_password.return_value = True
    mock_create_token.return_value = "fake-jwt-token"

    token, user = user_service.authenticate_user(
        mock_user_data["email"], mock_user_data["password"]
    )

    assert token == "fake-jwt-token"
    assert user == user_doc
    mock_create_token.assert_called_once()


@patch("app.services.user_service.verify_password")
@patch("app.services.user_service.db")
def test_authenticate_user_wrong_password(mock_db, mock_verify_password, mock_user_data):
    mock_db.users.find_one.return_value = {
        "user_name": mock_user_data["user_name"],
        "email": mock_user_data["email"]
    }
    mock_db.user_auth.find_one.return_value = {
        "user_id": mock_user_data["user_name"],
        "password": "hashed_pw"
    }
    mock_verify_password.return_value = False

    result = user_service.authenticate_user(mock_user_data["email"], "wrongpass")
    assert result is None


@patch("app.services.user_service.db")
def test_authenticate_user_no_user(mock_db):
    mock_db.users.find_one.return_value = None
    result = user_service.authenticate_user("notfound@example.com", "irrelevant")
    assert result is None


def test_generate_and_decode_token():
    user_id = "testuser"
    token = user_service.generate_token(user_id)
    decoded = user_service.decode_token(token)
    assert decoded == user_id


def test_decode_token_invalid():
    invalid_token = "this.is.invalid"
    result = user_service.decode_token(invalid_token)
    assert result is None
