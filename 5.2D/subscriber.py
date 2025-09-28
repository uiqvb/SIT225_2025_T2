#!/usr/bin/env python3
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pymongo import MongoClient

import config  # your credentials

# ---------- MongoDB ----------
mongo_client = MongoClient(config.MONGO_URI)
mongo_db = mongo_client[config.MONGO_DB]
mongo_col = mongo_db[config.MONGO_COLLECTION]

# ---------- Optional Redis ----------
use_redis = all(
    hasattr(config, k) for k in ("REDIS_HOST", "REDIS_PORT", "REDIS_USER", "REDIS_PASS")
)
rclient = None
if use_redis:
    try:
        import redis
        # Try TLS first
        rclient = redis.Redis(
            host=config.REDIS_HOST,
            port=int(config.REDIS_PORT),
            username=getattr(config, "REDIS_USER", None),
            password=config.REDIS_PASS,
            ssl=True,
            ssl_cert_reqs=None,      # helps on Windows/OpenSSL combos
            socket_timeout=3,
        )
        rclient.ping()
        print("🟥 Redis connected (TLS).")
    except Exception as e_tls:
        print(f"⚠️ TLS Redis connect failed: {e_tls}. Trying non-TLS…")
        try:
            rclient = redis.Redis(
                host=config.REDIS_HOST,
                port=int(config.REDIS_PORT),
                username=getattr(config, "REDIS_USER", None),
                password=config.REDIS_PASS,
                ssl=False,
                socket_timeout=3,
            )
            rclient.ping()
            print("🟥 Redis connected (non-TLS).")
        except Exception as e_plain:
            print(f"❌ Redis connect failed (non-TLS): {e_plain}")
            rclient = None
            use_redis = False

def save_to_mongo(doc: dict) -> dict:
    """Insert a copy into Mongo. Return a JSON-serializable copy with _id as str."""
    to_insert = dict(doc)
    result = mongo_col.insert_one(to_insert)
    safe = dict(to_insert)
    safe["_id"] = str(result.inserted_id)
    return safe

def save_to_redis(doc: dict) -> None:
    if not (use_redis and rclient):
        return
    # Avoid ObjectId; ensure JSON always works
    rclient.set(doc["ts_iso"], json.dumps(doc, default=str))

# ---------- MQTT callbacks (API v2) ----------
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ Connected to HiveMQ")
        client.subscribe(config.MQTT_TOPIC, qos=1)
        print(f"📡 Subscribed to: {config.MQTT_TOPIC}")
    else:
        print(f"❌ MQTT connect failed (code={reason_code})")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8", errors="replace").strip()
        data = json.loads(payload)

        # Validate
        for k in ("x", "y", "z"):
            if k not in data:
                raise ValueError(f"Missing '{k}' in payload: {payload}")

        # Coerce to float
        x = float(data["x"]); y = float(data["y"]); z = float(data["z"])

        ts_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        base_doc = {"ts_iso": ts_iso, "x": x, "y": y, "z": z}

        # 1) Mongo
        safe_doc = save_to_mongo(base_doc)

        # 2) Redis (store without _id to keep it simple)
        if use_redis:
            redis_doc = {"ts_iso": ts_iso, "x": x, "y": y, "z": z}
            save_to_redis(redis_doc)
            dests = "MongoDB & Redis"
        else:
            dests = "MongoDB"

        print(f"💾 Saved to {dests}: {safe_doc}")

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")

def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"🔌 Disconnected (code={reason_code})")

# ---------- MQTT client (API v2) ----------
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
mqtt_client.tls_set()  # HiveMQ Cloud requires TLS

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect

print("🚀 Connecting to HiveMQ…")
mqtt_client.connect(config.MQTT_BROKER, int(config.MQTT_PORT), keepalive=60)

try:
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Stopping subscriber…")
finally:
    try:
        mqtt_client.disconnect()
    except Exception:
        pass
    mongo_client.close()
