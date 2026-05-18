import logging
import os
import threading
from urllib.parse import urlparse, urlunparse

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv()

_init_lock = threading.Lock()
_db_initialized = False


class DatabaseConfigError(RuntimeError):
    pass


class DatabaseConnectionError(RuntimeError):
    pass


def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.strip()

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "studentdb")

    if user and password is not None:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    return None


def _normalize_database_url(database_url):
    if not database_url:
        raise DatabaseConfigError(
            "DATABASE_URL is missing. For local development, create a .env file with "
            "DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/studentdb. "
            "On Render, link DATABASE_URL from your PostgreSQL service."
        )

    parsed = urlparse(database_url)
    if parsed.scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql")
    return urlunparse(parsed)


class PostgresRow:
    def __init__(self, values, description):
        self.values = tuple(values)
        self.columns = [column.name for column in description]
        self.index = {column: position for position, column in enumerate(self.columns)}

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.values[self.index[key]]
        return self.values[key]

    def __iter__(self):
        return iter(zip(self.columns, self.values))

    def __len__(self):
        return len(self.values)

    def keys(self):
        return self.columns


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        self.cursor.execute(query, params)
        return self

    def executemany(self, query, param_seq):
        self.cursor.executemany(query, param_seq)
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return PostgresRow(row, self.cursor.description)

    def fetchall(self):
        return [PostgresRow(row, self.cursor.description) for row in self.cursor.fetchall()]

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def cursor(self):
        return PostgresCursor(self.connection.cursor())

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        self.close()

    def __getattr__(self, name):
        return getattr(self.connection, name)


def get_connection():
    database_url = _normalize_database_url(get_database_url())
    try:
        connection = psycopg.connect(
            database_url,
            connect_timeout=10,
            autocommit=False,
        )
    except psycopg.OperationalError as error:
        raise DatabaseConnectionError(
            "Could not connect to PostgreSQL. Verify DATABASE_URL and that the database is reachable."
        ) from error
    return PostgresConnection(connection)


def _identifier(name):
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def _add_column_if_not_exists(cursor, table_name, column_name, column_def):
    _identifier(table_name)
    _identifier(column_name)
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    columns = {row["column_name"] for row in cursor.fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def _create_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            roll_number TEXT UNIQUE,
            name TEXT,
            password TEXT,
            department TEXT,
            course_name TEXT,
            age INTEGER,
            section TEXT,
            father_name TEXT,
            father_phone TEXT,
            mother_name TEXT,
            mother_phone TEXT,
            phone TEXT,
            year INTEGER DEFAULT 1,
            semester INTEGER DEFAULT 1,
            address TEXT,
            photo_filename TEXT
        )
        """
    )

    _add_column_if_not_exists(cursor, "students", "section", "TEXT")
    _add_column_if_not_exists(cursor, "students", "father_phone", "TEXT")
    _add_column_if_not_exists(cursor, "students", "mother_phone", "TEXT")
    _add_column_if_not_exists(cursor, "students", "phone", "TEXT")
    _add_column_if_not_exists(cursor, "students", "year", "INTEGER DEFAULT 1")
    _add_column_if_not_exists(cursor, "students", "semester", "INTEGER DEFAULT 1")
    _add_column_if_not_exists(cursor, "students", "photo_filename", "TEXT")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
        """
    )

    _add_column_if_not_exists(cursor, "admins", "email", "TEXT")

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_email
        ON admins (email)
        WHERE email IS NOT NULL
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS institution (
            id SERIAL PRIMARY KEY,
            college_name TEXT,
            about_college TEXT,
            vision TEXT,
            mission TEXT,
            principal_message TEXT,
            address TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            accreditation TEXT,
            placements TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            staff_id TEXT UNIQUE,
            name TEXT,
            password TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subject_allocation (
            id SERIAL PRIMARY KEY,
            subject_name TEXT,
            year INTEGER,
            semester INTEGER,
            branch TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_roll TEXT,
            subject_name TEXT,
            year INTEGER,
            semester INTEGER,
            branch TEXT,
            section TEXT,
            date TEXT,
            status TEXT,
            staff_id TEXT
        )
        """
    )


def _seed_default_admin(cursor):
    cursor.execute(
        """
        INSERT INTO admins (username, email, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """,
        ("admin", "admin@example.com", "admin123"),
    )


def init_db(force=False):
    """Create all application tables and seed default data if missing."""
    global _db_initialized

    with _init_lock:
        if _db_initialized and not force:
            return

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            _create_tables(cursor)
            conn.commit()

            _seed_default_admin(cursor)
            conn.commit()

            _db_initialized = True
            logger.info("Database initialized successfully.")
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()


def create_database():
    """Backward-compatible alias used by Procfile and older imports."""
    init_db(force=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        init_db(force=True)
        print("Database tables are ready.")
    except (DatabaseConfigError, DatabaseConnectionError) as error:
        print(error)
        raise SystemExit(1) from error
