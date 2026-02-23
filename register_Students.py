from database import StudentDatabase

db = StudentDatabase()

# Register students
students = [
    ("student1", "student1@med.edu", "pass123", "Guang", "NTU"),
]

for username, email, password, name, institution in students:
    student_id = db.register_student(username, email, password, name, institution)
    if student_id:
        print(f"✓ Created: {username} (ID: {student_id})")

print("\nYou can now login with:")
print("Username: student1, Password: pass123")
