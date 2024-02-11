from flask import Flask, request, jsonify, redirect, send_from_directory, make_response
import os
import jwt
import requests
from datetime import timedelta

app = Flask(__name__)

app.config.update(
    PORT=os.environ.get("PORT", 8080),
    DB_PROXY=os.environ.get("DB_PROXY", "127.0.0.1"),
    DB_PROXY_PORT=os.environ.get("DB_PROXY_PORT", 5051),
    JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "jwt_secret_key"),
    JWT_ALGORITHM=os.environ.get("JWT_ALGORITHM", "HS256"),
    JWT_EXPIRATION_DELTA=timedelta(hours=1)
)

DB_PROXY_URL = f"http://{app.config['DB_PROXY']}:{app.config['DB_PROXY_PORT']}"

def execute_query(query, forwarded_for=None):
    payload = {"query": query}
    headers = {'X-Real-IP': forwarded_for} if forwarded_for else {}
    response = requests.post(
        f"{DB_PROXY_URL}/execute", json=payload, headers=headers)
    return response.json()["result"]


def fetch_all(query, forwarded_for=None):
    payload = {"query": query}
    headers = {'X-Real-IP': forwarded_for} if forwarded_for else {}
    response = requests.post(
        f"{DB_PROXY_URL}/fetchall", json=payload, headers=headers)
    return response.json()["result"]


def fetch_one(query, forwarded_for=None):
    payload = {"query": query}
    headers = {'X-Real-IP': forwarded_for} if forwarded_for else {}
    response = requests.post(
        f"{DB_PROXY_URL}/fetchone", json=payload, headers=headers)
    return response.json()["result"]


def row_count(query, forwarded_for=None):
    payload = {"query": query}
    headers = {'X-Real-IP': forwarded_for} if forwarded_for else {}
    response = requests.post(
        f"{DB_PROXY_URL}/rowcount", json=payload, headers=headers)
    return response.json()


@app.route('/')
def index():
    token = request.cookies.get('jwt_token')
    if token:
        try:
            payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[
                                 app.config['JWT_ALGORITHM']])
            return redirect('/documents.html')
        except jwt.ExpiredSignatureError:
            pass  
        except jwt.InvalidTokenError:
            pass 
    return redirect('/login_register.html')


@app.route('/register', methods=['POST'])
def register():
    forwarded_for = request.headers.get('X-Real-IP', request.remote_addr)
    username = request.json.get('username')
    password = request.json.get('password')

    if not (username and password):
        return jsonify({"error": "Username and password are required"}), 400

    query = f"SELECT * FROM users WHERE username = '{username}'"
    result = fetch_one(query, forwarded_for=forwarded_for)

    if result:
        return jsonify({"error": "Username already exists"}), 400

    query = f"INSERT INTO users (username, password) VALUES ('{username}','{password}')"
    execute_query(query, forwarded_for=forwarded_for)

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    forwarded_for = request.headers.get('X-Real-IP', request.remote_addr)
    username = request.json.get('username')
    password = request.json.get('password')

    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    result = fetch_one(query, forwarded_for=forwarded_for)
    print(result)
    if result:
        payload = {'id': result["id"], 'username': username}
        token = jwt.encode(
            payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
        response = make_response(jsonify({"message": "Login successful"}), 200)
        response.set_cookie('jwt_token', token, httponly=True)
        return response
    else:
        return jsonify({"error": "Invalid username or password"}), 401


@app.route('/logout')
def logout():
    response = make_response(
        jsonify({"message": "Logged out successfully"}), 200)
    response.set_cookie('jwt_token', '', expires=0, httponly=True)
    return response


@app.route('/documents', methods=['GET'])
def get_documents():
    forwarded_for = request.headers.get('X-Real-IP', request.remote_addr)
    token = request.cookies.get('jwt_token')

    if not token:
        return jsonify({"error": "Unauthorized access"}), 401

    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[
                             app.config['JWT_ALGORITHM']])
        id = payload['id']
        username = payload['username']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    query = f"SELECT id, document FROM documents WHERE user_id = {id}"
    documents_list = fetch_all(query, forwarded_for=forwarded_for)
    return jsonify(documents_list), 200


@app.route('/documents', methods=['POST'])
def add_document():
    forwarded_for = request.headers.get('X-Real-IP', request.remote_addr)
    token = request.cookies.get('jwt_token')

    if not token:
        return jsonify({"error": "Unauthorized access"}), 401

    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[
                             app.config['JWT_ALGORITHM']])
        id = payload['id']
        username = payload['username']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    document = request.json.get('document')

    if not document:
        return jsonify({"error": "Document is required"}), 400

    query = f"INSERT INTO documents (user_id, document) VALUES ({id}, '{document}')"
    execute_query(query, forwarded_for=forwarded_for)
    return jsonify({"message": "Document added successfully"}), 201


@app.route('/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    forwarded_for = request.headers.get('X-Real-IP', request.remote_addr)
    token = request.cookies.get('jwt_token')

    if not token:
        return jsonify({"error": "Unauthorized access"}), 401

    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[
                             app.config['JWT_ALGORITHM']])
        id = payload['id']
        username = payload['username']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    query = f"DELETE FROM documents WHERE id = {document_id} AND user_id = {id}"
    execute_query(query, forwarded_for=forwarded_for)

    return jsonify({"message": "Document deleted successfully"}), 200


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=app.config['PORT'])
