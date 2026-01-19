import random
from typing import Dict

class PatientGenerator:
    """Generates realistic patient profiles for simulation"""
    
    SEVERITIES = ["Minimal", "Mild", "Moderate", "Moderately Severe", "Severe"]
    
    NAMES = {
        "male": ["James", "Michael", "Robert", "John", "David", "William"],
        "female": ["Mary", "Jennifer", "Linda", "Patricia", "Jessica", "Sarah"]
    }
    
    BACKGROUNDS = [
        "works as a teacher",
        "is a software engineer",
        "works in retail",
        "is a nurse",
        "is unemployed",
        "is a student",
        "works in construction",
        "is retired"
    ]
    
    LIFE_SITUATIONS = [
        "recently went through a divorce",
        "lost a family member last year",
        "has been struggling with work stress",
        "is dealing with financial difficulties",
        "has chronic health issues",
        "is experiencing relationship problems",
        "recently moved to a new city",
        "is caring for an aging parent"
    ]
    
    def __init__(self):
        pass
    
    def generate_patient(self, severity: str = None) -> Dict:
        """Generate a random patient profile"""
        
        if severity is None:
            severity = random.choice(self.SEVERITIES)
        
        gender = random.choice(["male", "female"])
        age = random.randint(25, 65)
        name = random.choice(self.NAMES[gender])
        background = random.choice(self.BACKGROUNDS)
        situation = random.choice(self.LIFE_SITUATIONS)
        
        # Map severity to PHQ-9 score ranges
        phq9_ranges = {
            "Minimal": (0, 4),
            "Mild": (5, 9),
            "Moderate": (10, 14),
            "Moderately Severe": (15, 19),
            "Severe": (20, 27)
        }
        
        min_score, max_score = phq9_ranges[severity]
        phq9_score = random.randint(min_score, max_score)
        
        profile = {
            "name": name,
            "age": age,
            "gender": gender,
            "background": background,
            "situation": situation,
            "severity": severity,
            "phq9_score": phq9_score,
            "backstory": f"{name} is a {age}-year-old {gender} who {background}. {name} {situation}."
        }
        
        return profile
    
    def generate_custom_patient(self, severity: str, phq9_score: int, 
                                age: int = None, gender: str = None) -> Dict:
        """Generate a patient with specific parameters"""
        
        if gender is None:
            gender = random.choice(["male", "female"])
        if age is None:
            age = random.randint(25, 65)
        
        name = random.choice(self.NAMES[gender])
        background = random.choice(self.BACKGROUNDS)
        situation = random.choice(self.LIFE_SITUATIONS)
        
        profile = {
            "name": name,
            "age": age,
            "gender": gender,
            "background": background,
            "situation": situation,
            "severity": severity,
            "phq9_score": phq9_score,
            "backstory": f"{name} is a {age}-year-old {gender} who {background}. {name} {situation}."
        }
        
        return profile