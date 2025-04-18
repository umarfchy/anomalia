import os
import time
import json
import requests
import joblib
import numpy as np
import faust

# config via env
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
LOKI_URL     = os.getenv('LOKI_URL')

# Faust app instance
app = faust.App(
    'anomaly-detector',
    broker=KAFKA_BROKER,
    value_serializer='json',
)

# define the input record schema (adjust fields to your logs)
class LogEvent(faust.Record, serializer='json'):
    timestamp: float
    level: str
    message: str
    # add any other fields your Filebeat injects

# consume from all your topics (or define multiple agents)
logs_topic = app.topic('logs.app', value_type=LogEvent)

# load your pre‑trained model
model = joblib.load('model.joblib')
# define your detection threshold
THRESHOLD = 0.5

def send_to_loki(alert: dict):
    payload = {
        "streams": [{
            "stream": {"job": "anomaly-detector", "level": "warn"},
            "values": [[str(int(time.time() * 1e9)), json.dumps(alert)]]
        }]
    }
    resp = requests.post(LOKI_URL, json=payload)
    resp.raise_for_status()

def extract_features(event: LogEvent) -> np.ndarray:
    # placeholder: build a feature vector from your event
    # e.g. [len(event.message), event.level == 'ERROR', ...]
    return np.array([len(event.message), 1 if event.level == 'ERROR' else 0])

@app.agent(logs_topic)
async def process(stream):
    async for event in stream:
        features = extract_features(event)
        score = model.decision_function([features])[0]
        if score > THRESHOLD:
            alert = {
                "timestamp": event.timestamp,
                "score": float(score),
                "message": event.message,
            }
            send_to_loki(alert)

if __name__ == '__main__':
    app.main()
