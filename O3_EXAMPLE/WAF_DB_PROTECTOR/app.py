from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import requests
import os
import time
import redis
import json
from transformers import AutoTokenizer
from werkzeug.middleware.proxy_fix import ProxyFix
from pymongo import MongoClient

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

mongo_client = MongoClient("mongodb://mongo:27017/")
db = mongo_client["O3"]
attacks_collection = db["ATTACKS"]

port = os.environ.get("PORT", 5051)

mysql_host = os.environ.get("MYSQL_HOST", "localhost")
mysql_port = os.environ.get("MYSQL_PORT", 3306)
mysql_user = os.environ.get("MYSQL_USER", "your_username")
mysql_password = os.environ.get("MYSQL_PASSWORD", "your_password")
mysql_db = os.environ.get("MYSQL_DB", "doc_app")

fake_mysql_host = os.environ.get("FAKE_MYSQL_HOST", "localhost")
fake_mysql_port = os.environ.get("FAKE_MYSQL_PORT", 3307)
fake_mysql_user = os.environ.get("FAKE_MYSQL_USER", "your_username")
fake_mysql_password = os.environ.get("FAKE_MYSQL_PASSWORD", "your_password")
fake_mysql_db = os.environ.get("FAKE_MYSQL_DB", "doc_app")


redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
redis_client = redis.StrictRedis(host=redis_host, port=6379, db=0)

model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)



def create_tables(conn):
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                document TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()

    except Exception as e:
        app.logger.error("Error creating tables:", e)
        if cursor:
            cursor.close()
        conn.rollback()
    finally:
        if cursor:
            cursor.close()



def predict_is_from_attacker(input_text):
    inputs = tokenizer(input_text)

    input_ids = list(inputs['input_ids'])
    attention_mask = list(inputs['attention_mask'])

    url = "http://ai_model:8501/v1/models/waf_db_protector:predict"

    data = json.dumps({"signature_name": "serving_default",
                       "inputs": {"input_ids": [input_ids],
                                  "attention_mask": [attention_mask]}})

    response = requests.post(url, data=data)
    id2label = {
        0: "NORMAL",
        1: "ATTACKER",
    }

    if response.status_code == 200:
        predictions = json.loads(response.text)['outputs'][0]
        predicted_class_id = predictions.index(max(predictions))
        label = id2label[predicted_class_id]
        app.logger.warning((input_text, label, predictions))
        return label == "ATTACKER"
    else:
        app.logger.warning("Error:", response.status_code)



def is_attack(url, datas):
    ip_address = request.headers.get('X-Real-IP', request.remote_addr)
    app.logger.warning(f"ip_address -> {ip_address}")

    cached_result = redis_client.get(ip_address)
    if cached_result is not None:
        attacks_collection.insert_one(
            {"ip": ip_address, "url": url, "time": time.time(), "content": datas, "detector": "last_attack", "logger": "db"})
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
            {"ip": ip_address, "url": url, "time": time.time(), "content": datas, "detector": "db", "logger": "db"})

    return result


try:
    conn = mysql.connector.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db
    )
    if conn.is_connected():
        print("Connected to MySQL database")
        create_tables(conn)
except Error as e:
    app.logger.error("Error connecting to MySQL database:", e)

try:
    fake_conn = mysql.connector.connect(
        host=fake_mysql_host,
        port=fake_mysql_port,
        user=fake_mysql_user,
        password=fake_mysql_password,
        database=fake_mysql_db
    )
    if fake_conn.is_connected():
        print("Connected to FAKE MySQL database")
        create_tables(fake_conn)
except Error as e:
    app.logger.error("Error connecting to FAKE MySQL database:", e)



@app.route('/execute', methods=['POST'])
def execute():
    app.logger.warning('/execute')

    data = request.json
    query = data.get('query', None)

    app.logger.warning(str((query)))

    cursor = None
    try:
        if is_attack(request.url, {"query": query}):
            cursor = fake_conn.cursor(dictionary=True)
        else:
            cursor = conn.cursor(dictionary=True)

        cursor.execute(query)
        cursor.fetchall()

        if is_attack(request.url, {"query": query}):
            fake_conn.commit()
        else:
            conn.commit()

        return jsonify({"message": "Query executed successfully", "result": "ok"}), 200

    except Exception as e:
        app.logger.error("Error executing query:", e)
        if cursor:
            cursor.close()
        if is_attack(request.url, {"query": query}):
            fake_conn.rollback()
        else:
            conn.rollback()
        return jsonify({"error": "Failed to execute query"}), 500

    finally:
        if cursor:
            cursor.close()



@app.route('/fetchall', methods=['POST'])
def fetch_all():
    app.logger.warning('/fetchall')

    data = request.json
    query = data.get('query', None)

    app.logger.warning(str((query)))

    cursor = None
    try:
        if is_attack(request.url, {"query": query}):
            cursor = fake_conn.cursor(dictionary=True)
        else:
            cursor = conn.cursor(dictionary=True)

        cursor.execute(query)
        result = cursor.fetchall()
        return jsonify({"result": result}), 200

    except Exception as e:
        app.logger.error("Error fetching all:", e)
        return jsonify({"error": "Failed to fetch all"}), 500

    finally:
        if cursor:
            cursor.close()



@app.route('/fetchone', methods=['POST'])
def fetch_one():
    app.logger.warning('/fetchone')

    data = request.json
    query = data.get('query', None)

    app.logger.warning(str((query)))

    cursor = None
    try:
        if is_attack(request.url, {"query": query}):
            cursor = fake_conn.cursor(dictionary=True)
        else:
            cursor = conn.cursor(dictionary=True)

        cursor.execute(query)

        result = cursor.fetchone()
        cursor.fetchall()

        app.logger.warn(cursor.statement)
        return jsonify({"result": result}), 200

    except Exception as e:
        app.logger.error("Error fetching one:", e)
        return jsonify({"error": "Failed to fetch one"}), 500

    finally:
        if cursor:
            cursor.close()



@app.route('/rowcount', methods=['POST'])
def rowcount():
    app.logger.warning('/rowcount')

    data = request.json
    query = data.get('query', None)

    app.logger.warning(str((query)))

    cursor = None
    try:
        if is_attack(request.url, {"query": query}):
            cursor = fake_conn.cursor(dictionary=True)
        else:
            cursor = conn.cursor(dictionary=True)

        cursor.execute(query)
        cursor.fetchall()

        result = result = len(cursor.fetchall())
        return jsonify({"result": result}), 200

    except Exception as e:
        app.logger.error("Error fetching one:", e)
        return jsonify({"error": "Failed to fetch one"}), 500

    finally:
        if cursor:
            cursor.close()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)
