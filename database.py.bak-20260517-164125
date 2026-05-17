import sqlite3

def add_column_if_not_exists(cursor, table_name, column_name, column_def):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def create_database():

    conn = sqlite3.connect("student.db")
    cursor = conn.cursor()

    # ================= STUDENT TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

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
    """)

    add_column_if_not_exists(cursor, "students", "section", "TEXT")
    add_column_if_not_exists(cursor, "students", "father_phone", "TEXT")
    add_column_if_not_exists(cursor, "students", "mother_phone", "TEXT")
    add_column_if_not_exists(cursor, "students", "phone", "TEXT")
    add_column_if_not_exists(cursor, "students", "year", "INTEGER DEFAULT 1")
    add_column_if_not_exists(cursor, "students", "semester", "INTEGER DEFAULT 1")
    add_column_if_not_exists(cursor, "students", "photo_filename", "TEXT")

    # ================= ADMIN TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT

    )
    """)

    add_column_if_not_exists(cursor, "admins", "email", "TEXT")

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_email
        ON admins(email)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_email
        ON admins(email)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_email
        ON admins(email)
    """)

    # Keep the original hardcoded admin credentials available in the database
    # so existing username login continues to work after adding email login.
    cursor.execute("""
        INSERT OR IGNORE INTO admins (username, email, password)
        VALUES (?, ?, ?)
    """, ("admin", "admin@example.com", "admin123"))

    
    # ================= INSTITUTION TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS institution (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

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
    """)

    # ================= STAFF TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id TEXT UNIQUE,
        name TEXT,
        password TEXT

    )
    """)

    # ================= SUBJECT ALLOCATION TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subject_allocation (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT,
        year INTEGER,
        semester INTEGER,
        branch TEXT

    )
    """)

    # ================= ATTENDANCE TABLE =================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)


    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
