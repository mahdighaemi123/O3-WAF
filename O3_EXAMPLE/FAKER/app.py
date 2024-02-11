import os
import mysql.connector
import random
import string
import time

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

main_conn = mysql.connector.connect(
    host=mysql_host,
    port=mysql_port,
    user=mysql_user,
    password=mysql_password,
    database=mysql_db
)

if main_conn.is_connected():
    print("Connected to MySQL database")

fake_conn = mysql.connector.connect(
    host=fake_mysql_host,
    port=fake_mysql_port,
    user=fake_mysql_user,
    password=fake_mysql_password,
    database=fake_mysql_db
)
if fake_conn.is_connected():
    print("Connected to Fake MySQL database")


def generate_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def generate_random_password(length):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for i in range(length))


def main():

    print("start...")
    while 1:
        main_cursor = main_conn.cursor(dictionary=True)

        fake_cursor = fake_conn.cursor()

        main_cursor.execute(f"SELECT id, username FROM users")
        users = main_cursor.fetchall()

        for user in users:
            fake_cursor.execute(f"SELECT * FROM users WHERE id = {user['id']}")
            existing_user = fake_cursor.fetchone()

            if not existing_user:
                print("fake user")
                password = generate_random_password(12)
                fake_cursor.execute(
                    f"INSERT INTO users (id, username, password) VALUES ({user['id']}, '{user['username']}', '{password}')")

        fake_conn.commit()

        main_cursor.execute("SELECT id, user_id, document FROM documents")
        documents = main_cursor.fetchall()

        for document in documents:
            fake_cursor.execute(
                "SELECT * FROM documents WHERE id = %s", (document['id'],))
            existing_doc = fake_cursor.fetchone()

            if not existing_doc:
                print("fake doc")
                random_document = generate_random_string(100)

                fake_cursor.execute("INSERT INTO documents (id, user_id, document) VALUES (%s, %s, %s)", (
                    document['id'], document['user_id'], random_document))

        fake_conn.commit()
        print("Data copied and modified successfully.")
        time.sleep(60)


main()
