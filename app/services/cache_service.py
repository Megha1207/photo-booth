import redis
import json
from app.config import Config

# Initialize Redis client
redis_client = redis.StrictRedis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    decode_responses=True
)

def cache_embedding(embedding_id: str, embedding_vector: list, ttl: int = 3600):
    """
    Cache embedding vector with optional TTL (default 1 hour)
    """
    redis_client.setex(f"embedding:{embedding_id}", ttl, json.dumps(embedding_vector))

def get_cached_embedding(embedding_id: str):
    """
    Retrieve cached embedding vector if exists
    """
    cached = redis_client.get(f"embedding:{embedding_id}")
    if cached:
        return json.loads(cached)
    return None

def invalidate_cached_embedding(embedding_id: str):
    """
    Remove embedding from cache
    """
    redis_client.delete(f"embedding:{embedding_id}")

def cache_face_match_result(face_id: str, matched_file_ids: list, ttl: int = 300):
    """
    Cache face-to-file match results for quick repeated lookups
    """
    redis_client.setex(f"match:{face_id}", ttl, json.dumps(matched_file_ids))

def get_cached_match_result(face_id: str):
    """
    Retrieve cached match results for a face
    """
    cached = redis_client.get(f"match:{face_id}")
    if cached:
        return json.loads(cached)
    return None
