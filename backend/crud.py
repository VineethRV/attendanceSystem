from typing import Optional, List, Dict, Any
import db

def _row_to_dict(cursor, row) -> Dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# Students
def add_student(usn: str, name: str, class_name: str = None, embedding: str = None) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students(usn, name, class_name, embedding) VALUES (?, ?, ?, ?)",
        (usn, name, class_name, embedding),
    )
    conn.commit()
    conn.close()

def get_student(usn: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE usn = ?", (usn,))
    row = cur.fetchone()
    result = None
    if row:
        result = _row_to_dict(cur, row)
    conn.close()
    return result

def update_student_embedding(usn: str, embedding: str) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE students SET embedding = ? WHERE usn = ?", (embedding, usn))
    conn.commit()
    conn.close()

def delete_student(usn: str) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE usn = ?", (usn,))
    conn.commit()
    conn.close()

def list_students() -> List[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    rows = cur.fetchall()
    results = [_row_to_dict(cur, r) for r in rows]
    conn.close()
    return results

# Classrooms
def add_classroom(classroom: str, router_ip: str = None) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO classrooms(classroom, router_ip) VALUES (?, ?)", (classroom, router_ip))
    conn.commit()
    conn.close()

def get_classroom(classroom: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classrooms WHERE classroom = ?", (classroom,))
    row = cur.fetchone()
    result = _row_to_dict(cur, row) if row else None
    conn.close()
    return result

def list_classrooms() -> List[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classrooms")
    rows = cur.fetchall()
    results = [_row_to_dict(cur, r) for r in rows]
    conn.close()
    return results

# Class schedules
def add_class_schedule(class_name: str, start_time: str, subject: str = None, classroom: str = None) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO classes(class_name, start_time, subject, classroom) VALUES (?, ?, ?, ?)",
        (class_name, start_time, subject, classroom),
    )
    conn.commit()
    conn.close()

def get_class_schedule(class_name: str, start_time: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes WHERE class_name = ? AND start_time = ?", (class_name, start_time))
    row = cur.fetchone()
    result = _row_to_dict(cur, row) if row else None
    conn.close()
    return result

def list_schedules_for_class(class_name: str) -> List[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes WHERE class_name = ? ORDER BY start_time", (class_name,))
    rows = cur.fetchall()
    results = [_row_to_dict(cur, r) for r in rows]
    conn.close()
    return results

# Attendance
def set_attendance(usn: str, subject: str, percentage: float) -> None:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO attendance(usn, subject, percentage) VALUES (?, ?, ?)",
        (usn, subject, percentage),
    )
    conn.commit()
    conn.close()

def get_attendance(usn: str, subject: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance WHERE usn = ? AND subject = ?", (usn, subject))
    row = cur.fetchone()
    result = _row_to_dict(cur, row) if row else None
    conn.close()
    return result

def list_attendance_for_usn(usn: str) -> List[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance WHERE usn = ?", (usn,))
    rows = cur.fetchall()
    results = [_row_to_dict(cur, r) for r in rows]
    conn.close()
    return results

if __name__ == "__main__":
    print("This module provides CRUD helper functions. Import and use them from your app.")
