# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import router as api_router
from app.config import Config
from app.db import init_mongo, init_redis

app = FastAPI(
    title="Photobooth",
    description="Upload images, detect faces, search by event, and remove duplicates.",
    version="1.0.0"
)

# ✅ Ensure the directory exists
os.makedirs(Config.LOCAL_STORAGE_PATH, exist_ok=True)

# ✅ Mount the full absolute path correctly
app.mount("/files", StaticFiles(directory=Config.LOCAL_STORAGE_PATH), name="files")
print("Mounted path:", Config.LOCAL_STORAGE_PATH)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_mongo()
    init_redis()

# ✅ Includes all API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Photobooth Face Recognition API is running."}
