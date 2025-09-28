#!/usr/bin/env python3
"""
Clear all data from MongoDB collection and Redis database.
"""

from pymongo import MongoClient
import redis
import config  # make sure your config.py has Mongo + Redis credentials


def clear_mongo():
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db[config.MONGO_COLLECTION]

    # Delete all documents
    result = col.delete_many({})
    print(f"🗑️ Deleted {result.deleted_count} docs from MongoDB collection '{config.MONGO_COLLECTION}'")

    # Optional: Drop collection entirely
    # col.drop()
    # print(f"🔥 Dropped MongoDB collection '{config.MONGO_COLLECTION}'")


def clear_redis():
    r = redis.Redis(
        host=config.REDIS_HOST,
        port=int(config.REDIS_PORT),
        username=getattr(config, "REDIS_USER", None),
        password=config.REDIS_PASS,
        ssl=True,
    )

    # Delete all keys in current Redis DB
    r.flushdb()
    print("🗑️ Deleted all keys from Redis DB")

    # Optional: Clear all DBs in Redis (use with care!)
    # r.flushall()
    # print("🔥 Deleted all keys from ALL Redis DBs")


if __name__ == "__main__":
    print("🚀 Clearing MongoDB and Redis...")
    clear_mongo()
    clear_redis()
    print("✅ Done!")
