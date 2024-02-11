import os
import mysql.connector
import random
import string
import time

# Function to generate a random string


def generate_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))

# Function to generate a random password


def generate_random_password(length):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for i in range(length))


# Retrieve environment variables
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

# Connect to main MySQL database
main_conn = mysql.connector.connect(
    host=mysql_host,
    port=mysql_port,
    user=mysql_user,
    password=mysql_password,
    database=mysql_db
)

if main_conn.is_connected():
    print("Connected to MySQL database")

# Connect to fake MySQL database
fake_conn = mysql.connector.connect(
    host=fake_mysql_host,
    port=fake_mysql_port,
    user=fake_mysql_user,
    password=fake_mysql_password,
    database=fake_mysql_db
)
if fake_conn.is_connected():
    print("Connected to Fake MySQL database")


print("start...")
while 1:
    # Create cursor for main database
    main_cursor = main_conn.cursor(dictionary=True)

    # Create cursor for fake database
    fake_cursor = fake_conn.cursor()

    # Copy users from main to fake database
    main_cursor.execute("SELECT id, username FROM users")
    users = main_cursor.fetchall()

    for user in users:
        # Check if user already exists in fake database
        fake_cursor.execute("SELECT * FROM users WHERE id = %s", (user['id'],))
        existing_user = fake_cursor.fetchone()

        if not existing_user:
            print("fake user")

            # Generate random password for each user
            password = generate_random_password(12)

            # Insert user into fake database with same ID and username and random password
            fake_cursor.execute("INSERT INTO users (id, username, password) VALUES (%s, %s, %s)", (
                user['id'], user['username'], password))

    # Commit changes to fake database
    fake_conn.commit()

    # Copy documents from main to fake database
    main_cursor.execute("SELECT id, user_id, document FROM documents")
    documents = main_cursor.fetchall()

    for document in documents:
        # Check if document already exists in fake database
        fake_cursor.execute(
            "SELECT * FROM documents WHERE id = %s", (document['id'],))
        existing_doc = fake_cursor.fetchone()

        if not existing_doc:
            print("fake doc")
            # Generate random document for each document
            random_document = generate_random_string(100)

            # Insert document into fake database with same ID and user_id and random document
            fake_cursor.execute("INSERT INTO documents (id, user_id, document) VALUES (%s, %s, %s)", (
                document['id'], document['user_id'], random_document))

    # Commit changes to fake database
    fake_conn.commit()
    print("Data copied and modified successfully.")
    time.sleep(60)
