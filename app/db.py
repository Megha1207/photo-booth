# app/db.py

from pymongo import MongoClient
import redis
from app.config import Config

# MongoDB Client
mongo_client = MongoClient(Config.MONGO_URI)
mongo_db = mongo_client[Config.MONGO_DB_NAME]
# Expose database object for import
db = mongo_db

# Redis Client
redis_client = redis.StrictRedis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    decode_responses=True
)

# MongoDB Collections
users_collection = mongo_db["users"]
auth_collection = mongo_db["user_auth"]
devices_collection = mongo_db["devices"]
files_collection = mongo_db["files"]
file_metadata_collection = mongo_db["file_metadata"]
file_versions_collection = mongo_db["file_versions"]
chunks_collection = mongo_db["chunks"]
faces_collection = mongo_db["faces"]
face_metadata_collection = mongo_db["face_metadata"]
embeddings_collection = mongo_db["embeddings"]
events_collection = mongo_db["events"]

# Optional: Exported init functions
def init_mongo():
    return mongo_client, mongo_db, db

def init_redis():
    return redis_client