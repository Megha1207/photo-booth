from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
from jose import JWTError, jwt  # ✅ Use python-jose instead of PyJWT
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.db import db
from app.config import Config
from app.utils import create_access_token, verify_password

# OAuth2 scheme for FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print(f"[hash_password] Raw: {password} → Hashed: {hashed}")
    return hashed


def verify_password(password: str, hashed: str) -> bool:
    is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    print(f"[verify_password] Raw: {password} | Stored: {hashed} | Match: {is_valid}")
    return is_valid


def create_user(user_name: str, email: str, password: str, device_id: Optional[str] = None) -> str:
    email = email.lower()
    print("[create_user] Raw password:", password)
    hashed_pw = hash_password(password)
    print("[create_user] Hashed password:", hashed_pw)

    user_data = {
        "user_name": user_name,
        "email": email,
    }

    user_id = user_name  # Use user_name directly as user_id
    db.users.insert_one(user_data)

    auth_data = {
        "user_id": user_id,
        "password": hashed_pw,
        "last_sign_in": datetime.utcnow(),
        "device_id": ObjectId(device_id) if device_id else None
    }

    db.user_auth.insert_one(auth_data)
    return user_id


def authenticate_user(email: str, password: str) -> Optional[Tuple[str, str, dict]]:
    email = email.lower()
    print("[authenticate_user] Attempting login for:", email)

    user = db.users.find_one({"email": email})
    if not user:
        print("[authenticate_user] User not found ❌")
        return None

    user_id = user["user_name"]
    auth = db.user_auth.find_one({"user_id": user_id})
    if not auth:
        print("[authenticate_user] Auth record not found ❌")
        return None

    if not verify_password(password, auth["password"]):
        print("[authenticate_user] Password mismatch ❌")
        return None

    token = create_access_token(data={"sub": user["email"]})
    db.user_auth.update_one(
        {"user_id": user_id},
        {"$set": {"last_sign_in": datetime.utcnow()}}
    )

    print("[authenticate_user] Login successful ✅")
    return token, user_id, user  # 👈 Added user_id in return


def generate_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token payload missing 'sub'")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:  # Catch all other JWT-related issues
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    return decode_token(token)


# OAuth2 scheme for FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print(f"[hash_password] Raw: {password} → Hashed: {hashed}")
    return hashed


def verify_password(password: str, hashed: str) -> bool:
    is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    print(f"[verify_password] Raw: {password} | Stored: {hashed} | Match: {is_valid}")
    return is_valid


def create_user(user_name: str, email: str, password: str, device_id: Optional[str] = None) -> str:
    email = email.lower()
    print("[create_user] Raw password:", password)
    hashed_pw = hash_password(password)
    print("[create_user] Hashed password:", hashed_pw)

    user_data = {
        "user_name": user_name,
        "email": email,
    }

    user_id = user_name  # Use user_name directly as user_id
    db.users.insert_one(user_data)

    auth_data = {
        "user_id": user_id,
        "password": hashed_pw,
        "last_sign_in": datetime.utcnow(),
        "device_id": ObjectId(device_id) if device_id else None
    }

    db.user_auth.insert_one(auth_data)
    return user_id


def authenticate_user(email: str, password: str) -> Optional[Tuple[str, dict]]:
    email = email.lower()
    print("[authenticate_user] Attempting login for:", email)

    user = db.users.find_one({"email": email})
    if not user:
        print("[authenticate_user] User not found ❌")
        return None

    user_id = user["user_name"]
    auth = db.user_auth.find_one({"user_id": user_id})
    if not auth:
        print("[authenticate_user] Auth record not found ❌")
        return None

    if not verify_password(password, auth["password"]):
        print("[authenticate_user] Password mismatch ❌")
        return None

    token = create_access_token(data={"sub": user["email"]})
    db.user_auth.update_one(
        {"user_id": user_id},
        {"$set": {"last_sign_in": datetime.utcnow()}}
    )

    print("[authenticate_user] Login successful ✅")
    return token, user


def generate_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token payload missing 'sub'")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    return decode_token(token)
