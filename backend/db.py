import sqlite3
from sqlite3 import Connection

DB_PATH = "data.db"

def get_connection() -> Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(path: str = DB_PATH):
    """Create tables according to the provided schema.

    Schema implemented:
    - students(usn PK, name, class_name, embedding)
    - classrooms(classroom PK, router_ip)
    - classes(class_name, start_time, subject, classroom)  -- PK (class_name, start_time)
    - attendance(usn, subject, percentage)  -- PK (usn, subject)
    """
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        usn TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        class_name TEXT,
        embedding TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classrooms (
        classroom TEXT PRIMARY KEY,
        router_ip TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        class_name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        subject TEXT,
        classroom TEXT,
        PRIMARY KEY (class_name, start_time),
        FOREIGN KEY(classroom) REFERENCES classrooms(classroom)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        usn TEXT NOT NULL,
        subject TEXT NOT NULL,
        percentage REAL,
        PRIMARY KEY (usn, subject),
        FOREIGN KEY(usn) REFERENCES students(usn)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Initialized database at", DB_PATH)
