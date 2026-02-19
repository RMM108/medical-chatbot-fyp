"""Check what's in the database"""

from database import StudentDatabase

db = StudentDatabase()

# List all students
import sqlite3
conn = sqlite3.connect('student_progress.db')
cursor = conn.cursor()

print("=== ALL STUDENTS ===")
cursor.execute("SELECT student_id, username, email FROM students")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")

print("\n=== SESSIONS ===")
cursor.execute("""
    SELECT s.session_id, s.student_id, st.username, s.patient_name, e.overall_score
    FROM sessions s
    JOIN students st ON s.student_id = st.student_id
    LEFT JOIN evaluations e ON s.session_id = e.session_id
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"Session {row[0]}: Student {row[1]} ({row[2]}) - Patient: {row[3]}, Score: {row[4]}")

conn.close()

