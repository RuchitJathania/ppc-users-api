import os
import psycopg


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        autocommit=False,
        connect_timeout=3,
        options="-c statement_timeout=5000",
    )


def initialize_database():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(1000) NOT NULL CHECK (trim(name) <> ''),
                age SMALLINT NOT NULL CHECK (age >= 0),
                birth_state VARCHAR(15) NOT NULL CHECK (trim(birth_state) <> '')
            )
        """)


def check_database():
    with connect() as conn:
        conn.execute(
            "SELECT id, name, age, birth_state FROM users LIMIT 0"
        )