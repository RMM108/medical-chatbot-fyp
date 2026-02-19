"""Create demo data for testing visualizations"""

from database import StudentDatabase
import random
from datetime import datetime, timedelta

db = StudentDatabase()

# Register demo student
student_id = db.register_student(
    username="test_student",
    email="test@example.com",
    password="test123",
    full_name="Test Student",
    institution="Medical School"
)

print(f"Created student ID: {student_id}")

# Create 10 demo sessions with improving scores
severities = ["Mild", "Moderate", "Moderately Severe", "Severe"]

for i in range(10):
    # Create session
    patient_profile = {
        'name': f"Patient {i+1}",
        'severity': random.choice(severities),
        'phq9_score': random.randint(5, 27)
    }
    
    session_id = db.create_session(student_id, patient_profile)
    
    # Log conversation
    for j in range(random.randint(5, 10)):
        db.log_conversation_exchange(
            session_id, j+1,
            f"Doctor question {j+1}",
            f"Patient response {j+1}"
        )
    
    # Create improving evaluation scores
    base_score = 50 + (i * 3) + random.randint(-5, 5)
    
    evaluation = {
        'overall_score': min(base_score, 95),
        'phq9_evaluation': {
            'diagnostic_accuracy': min(base_score + random.randint(-10, 10), 100),
            'doctor_assessment': {
                'severity': random.choice(severities),
                'score': random.randint(10, 25)
            }
        },
        'empathy_evaluation': {
            'overall_score': min(base_score + random.randint(-5, 5), 100),
            'understanding': {'score': min(base_score, 100)},
            'communication': {'score': min(base_score + 5, 100)},
            'intention': {'score': min(base_score - 5, 100)}
        }
    }
    
    db.save_evaluation(session_id, evaluation)
    print(f"Created session {i+1} with score {evaluation['overall_score']:.1f}")

print("\n✓ Demo data created!")
print("Username: test_riya")
print("Password: riya123")