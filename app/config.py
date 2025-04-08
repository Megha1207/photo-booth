import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "event_face_recognition")

    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    # Local File Storage
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "D:/photobooth/app/storage")

    # Face Recognition Model
    MODEL_PATH = os.getenv("MODEL_PATH", "D:/photobooth/app/models/20180402-114759-vggface2.pt")

    # Security & Authentication
    SECRET_KEY = os.getenv("SECRET_KEY", "photobooth")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    # Chunk size (in bytes)
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024 * 1024))  # Default: 1MB

    # Deduplication threshold (Cosine similarity)
    DUPLICATE_THRESHOLD = float(os.getenv("DUPLICATE_THRESHOLD", 0.95))
