"""
Student Progress Tracking Database
SQLite database for storing student sessions, evaluations, and progress
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import secrets

class StudentDatabase:
    """Manage student accounts, sessions, and progress tracking"""
    
    def __init__(self, db_path: str = "student_progress.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                institution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                patient_name TEXT,
                patient_severity TEXT,
                patient_phq9_score INTEGER,
                session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                conversation_length INTEGER,
                duration_minutes INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        """)
        
        # Evaluations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                overall_score REAL,
                diagnostic_accuracy REAL,
                empathy_score REAL,
                understanding_score REAL,
                communication_score REAL,
                intention_score REAL,
                doctor_severity_assessment TEXT,
                doctor_phq9_assessment INTEGER,
                severity_correct BOOLEAN,
                evaluation_data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        
        # Conversation logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exchange_number INTEGER,
                doctor_message TEXT,
                patient_response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✓ Database initialized")
    
    # ==================== STUDENT MANAGEMENT ====================
    
    def register_student(self, username: str, email: str, password: str, 
                        full_name: str = "", institution: str = "") -> Optional[int]:
        """Register a new student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO students (username, email, password_hash, full_name, institution)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, password_hash, full_name, institution))
            
            student_id = cursor.lastrowid
            conn.commit()
            print(f"✓ Student registered: {username}")
            return student_id
            
        except sqlite3.IntegrityError as e:
            print(f"✗ Registration failed: {e}")
            return None
        finally:
            conn.close()
    
    def authenticate_student(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate student login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("""
            SELECT student_id, username, email, full_name, institution
            FROM students
            WHERE username = ? AND password_hash = ?
        """, (username, password_hash))
        
        result = cursor.fetchone()
        
        if result:
            # Update last login
            cursor.execute("""
                UPDATE students SET last_login = CURRENT_TIMESTAMP
                WHERE student_id = ?
            """, (result[0],))
            conn.commit()
            
            student = {
                'student_id': result[0],
                'username': result[1],
                'email': result[2],
                'full_name': result[3],
                'institution': result[4]
            }
            conn.close()
            return student
        
        conn.close()
        return None
    
    def get_student_profile(self, student_id: int) -> Optional[Dict]:
        """Get student profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, email, full_name, institution, created_at, last_login
            FROM students
            WHERE student_id = ?
        """, (student_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'username': result[0],
                'email': result[1],
                'full_name': result[2],
                'institution': result[3],
                'created_at': result[4],
                'last_login': result[5]
            }
        return None
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, student_id: int, patient_profile: Dict) -> int:
        """Create a new interview session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (
                student_id, patient_name, patient_severity, patient_phq9_score
            ) VALUES (?, ?, ?, ?)
        """, (
            student_id,
            patient_profile['name'],
            patient_profile['severity'],
            patient_profile['phq9_score']
        ))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def log_conversation_exchange(self, session_id: int, exchange_number: int,
                                 doctor_msg: str, patient_msg: str):
        """Log a single conversation exchange"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_logs (
                session_id, exchange_number, doctor_message, patient_response
            ) VALUES (?, ?, ?, ?)
        """, (session_id, exchange_number, doctor_msg, patient_msg))
        
        conn.commit()
        conn.close()
    
    def save_evaluation(self, session_id: int, evaluation: Dict):
        """Save evaluation results for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        phq9_eval = evaluation.get('phq9_evaluation', {})
        empathy_eval = evaluation.get('empathy_evaluation', {})
        
        cursor.execute("""
            INSERT INTO evaluations (
                session_id, overall_score, diagnostic_accuracy, empathy_score,
                understanding_score, communication_score, intention_score,
                doctor_severity_assessment, doctor_phq9_assessment,
                severity_correct, evaluation_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            evaluation.get('overall_score', 0),
            phq9_eval.get('diagnostic_accuracy', 0),
            empathy_eval.get('overall_score', 0),
            empathy_eval.get('understanding', {}).get('score', 0),
            empathy_eval.get('communication', {}).get('score', 0),
            empathy_eval.get('intention', {}).get('score', 0),
            phq9_eval.get('doctor_assessment', {}).get('severity', ''),
            phq9_eval.get('doctor_assessment', {}).get('score', 0),
            phq9_eval.get('severity_accuracy', 0) == 100,
            json.dumps(evaluation)
        ))
        
        # Update session with conversation length
        cursor.execute("""
            UPDATE sessions
            SET conversation_length = (
                SELECT COUNT(*) FROM conversation_logs WHERE session_id = ?
            )
            WHERE session_id = ?
        """, (session_id, session_id))
        
        conn.commit()
        conn.close()
    
    # ==================== PROGRESS TRACKING ====================
    
    def get_student_sessions(self, student_id: int, limit: int = 10) -> List[Dict]:
        """Get recent EVALUATED sessions for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                s.session_id, s.patient_name, s.patient_severity, 
                s.patient_phq9_score, s.session_date, s.conversation_length,
                e.overall_score, e.diagnostic_accuracy, e.empathy_score
            FROM sessions s
            INNER JOIN evaluations e ON s.session_id = e.session_id
            WHERE s.student_id = ?
            ORDER BY s.session_date DESC
            LIMIT ?
        """, (student_id, limit))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'patient_name': row[1],
                'patient_severity': row[2],
                'patient_phq9_score': row[3],
                'session_date': row[4],
                'conversation_length': row[5],
                'overall_score': row[6],
                'diagnostic_accuracy': row[7],
                'empathy_score': row[8]
            })
        
        conn.close()
        return sessions
    
    def get_progress_data(self, student_id: int) -> Dict:
        """Get comprehensive progress data for graphing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall statistics - ONLY COUNT EVALUATED SESSIONS
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                AVG(e.overall_score) as avg_score,
                AVG(e.diagnostic_accuracy) as avg_diagnostic,
                AVG(e.empathy_score) as avg_empathy,
                SUM(s.conversation_length) as total_exchanges
            FROM sessions s
            INNER JOIN evaluations e ON s.session_id = e.session_id
            WHERE s.student_id = ?
        """, (student_id,))
        
        stats = cursor.fetchone()
        
        # Progress over time - ONLY EVALUATED SESSIONS
        cursor.execute("""
            SELECT 
                s.session_date,
                e.overall_score,
                e.diagnostic_accuracy,
                e.empathy_score,
                s.patient_severity
            FROM sessions s
            INNER JOIN evaluations e ON s.session_id = e.session_id
            WHERE s.student_id = ?
            ORDER BY s.session_date ASC
        """, (student_id,))
        
        progress = []
        for row in cursor.fetchall():
            progress.append({
                'date': row[0],
                'overall_score': row[1],
                'diagnostic_accuracy': row[2],
                'empathy_score': row[3],
                'severity': row[4]
            })
        
        # Performance by severity - ONLY EVALUATED SESSIONS
        cursor.execute("""
            SELECT 
                s.patient_severity,
                COUNT(*) as count,
                AVG(e.overall_score) as avg_score
            FROM sessions s
            INNER JOIN evaluations e ON s.session_id = e.session_id
            WHERE s.student_id = ?
            GROUP BY s.patient_severity
        """, (student_id,))
        
        by_severity = {}
        for row in cursor.fetchall():
            by_severity[row[0]] = {
                'count': row[1],
                'avg_score': row[2]
            }
        
        conn.close()
        
        return {
            'total_sessions': stats[0] or 0,
            'avg_overall_score': stats[1] or 0,
            'avg_diagnostic': stats[2] or 0,
            'avg_empathy': stats[3] or 0,
            'total_exchanges': stats[4] or 0,
            'progress_timeline': progress,
            'performance_by_severity': by_severity
        }
    
    def get_session_details(self, session_id: int) -> Optional[Dict]:
        """Get detailed information about a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Session info
        cursor.execute("""
            SELECT 
                s.patient_name, s.patient_severity, s.patient_phq9_score,
                s.session_date, s.conversation_length,
                e.evaluation_data
            FROM sessions s
            LEFT JOIN evaluations e ON s.session_id = e.session_id
            WHERE s.session_id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        
        if not session:
            conn.close()
            return None
        
        # Conversation log
        cursor.execute("""
            SELECT exchange_number, doctor_message, patient_response, timestamp
            FROM conversation_logs
            WHERE session_id = ?
            ORDER BY exchange_number ASC
        """, (session_id,))
        
        conversation = []
        for row in cursor.fetchall():
            conversation.append({
                'exchange_number': row[0],
                'doctor': row[1],
                'patient': row[2],
                'timestamp': row[3]
            })
        
        conn.close()
        
        evaluation_data = json.loads(session[5]) if session[5] else {}
        
        return {
            'patient_name': session[0],
            'patient_severity': session[1],
            'patient_phq9_score': session[2],
            'session_date': session[3],
            'conversation_length': session[4],
            'evaluation': evaluation_data,
            'conversation': conversation
        }
    
    # ==================== ANALYTICS ====================
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top performing students"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                st.username, st.full_name, st.institution,
                COUNT(s.session_id) as total_sessions,
                AVG(e.overall_score) as avg_score
            FROM students st
            JOIN sessions s ON st.student_id = s.student_id
            LEFT JOIN evaluations e ON s.session_id = e.session_id
            GROUP BY st.student_id
            ORDER BY avg_score DESC
            LIMIT ?
        """, (limit,))
        
        leaderboard = []
        for row in cursor.fetchall():
            leaderboard.append({
                'username': row[0],
                'full_name': row[1],
                'institution': row[2],
                'total_sessions': row[3],
                'avg_score': row[4]
            })
        
        conn.close()
        return leaderboard

# Utility functions
def create_demo_data(db: StudentDatabase):
    """Create demo student and sessions for testing"""
    # Register demo student
    student_id = db.register_student(
        username="demo_student",
        email="demo@example.com",
        password="demo123",
        full_name="Demo Student",
        institution="Medical School"
    )
    
    if student_id:
        print(f"Created demo student (ID: {student_id})")
        print("Login: demo_student / demo123")

if __name__ == "__main__":
    # Initialize database
    db = StudentDatabase()
    
    # Create demo data
    create_demo_data(db)
    
    print("\n✓ Database setup complete!")
    print("\nYou can now:")
    print("1. Register students")
    print("2. Track session progress")
    print("3. Generate improvement graphs")