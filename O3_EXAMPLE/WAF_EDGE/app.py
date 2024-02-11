from flask import Flask, request, jsonify
import requests
import os
import redis
import json
import time
from transformers import AutoTokenizer
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient


mongo_client = MongoClient("mongodb://mongo:27017/")
db = mongo_client["O3"]
attacks_collection = db["ATTACKS"]

redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
redis_client = redis.StrictRedis(host=redis_host, port=6379, db=0)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)


server = os.environ.get("SERVER", "127.0.0.1")
server_port = os.environ.get("SERVER_PORT", "8080")
fake_server = os.environ.get("FAKE_SERVER", "127.0.0.1")
fake_server_port = os.environ.get("FAKE_SERVER_PORT", "8081")

model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)


def predict_is_from_attacker(input_text):
    inputs = tokenizer(input_text)

    input_ids = list(inputs['input_ids'])
    attention_mask = list(inputs['attention_mask'])

    url = "http://ai_model:8501/v1/models/waf_edge:predict"

    data = json.dumps({"signature_name": "serving_default",
                       "inputs": {"input_ids": [input_ids],
                                  "attention_mask": [attention_mask]}})

    response = requests.post(url, data=data)
    id2label = {0: "NORMAL", 1: "ATTACKER"}
    if response.status_code == 200:
        predictions = response.json()["outputs"][0]
        predicted_class_id = predictions.index(max(predictions))
        label = id2label[predicted_class_id]
        app.logger.warning((input_text, label, predictions))
        return label == "ATTACKER"
    else:
        app.logger.warning(f"Error: {response.status_code}")
        return False


def is_attack(url, datas):
    ip_address = request.headers.get('X-Real-IP', request.remote_addr)
    app.logger.warning(f"ip_address -> {ip_address}")

    cached_result = redis_client.get(ip_address)
    if cached_result is not None:
        attacks_collection.insert_one(
            {"ip": ip_address, "url": url, "time": time.time(), "content": datas, "detector": "last_attack", "logger": "edge"})
        return True
    result = False

    for key, value in datas.items():
        if value is None:
            value = "NONE"
        is_from_attacker = predict_is_from_attacker(value)
        result = is_from_attacker or result

    if result:
        redis_client.set(ip_address, "ATTACKER", ex=3600)
        attacks_collection.insert_one(
            {"ip": ip_address, "url": url, "time": time.time(), "content": datas, "detector": "edge", "logger": "edge"})

    return result


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    url = f'http://{server}:{server_port}/{path}'
    client_ip = request.headers.get('X-Real-IP', request.remote_addr)
    app.logger.warning(f"client_ip -> {client_ip}")

    if request.method in ['GET', 'DELETE', 'OPTIONS', 'HEAD']:
        params = request.args
        if is_attack(request.url, params):
            url = f'http://{fake_server}:{fake_server_port}/{path}'

    elif request.method in ['POST', 'PUT', 'PATCH']:
        data = request.json
        if is_attack(request.url, data):
            url = f'http://{fake_server}:{fake_server_port}/{path}'

    headers = {key: value for (key, value)
               in request.headers if key != 'Host'}
    headers['X-Real-IP'] = client_ip

    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    excluded_headers = ['content-encoding',
                        'content-length', 'transfer-encoding', 'connection']

    headers = resp.raw.headers.copy()

    headers = [(name, value) for (name, value) in headers.items()
               if name.lower() not in excluded_headers]
    response = app.response_class(
        response=resp.content,
        status=resp.status_code,
        headers=headers,
    )
    return response


if __name__ == '__main__':
    app.run(port=5050, host="0.0.0.0")
