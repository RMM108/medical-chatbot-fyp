#!/usr/bin/env python3
"""
Medical Training Chatbot - Patient Simulator
Simulates depressed patients for medical student training
"""

from patient_generator import PatientGenerator
from rag_client import RAGClient
from llm_handler import LLMHandler
from config import SERVER_URL



class MedicalChatbot:
    """Main chatbot orchestrator"""
    
    def __init__(self):
        self.patient_gen = PatientGenerator()
        self.rag_client = RAGClient()
        self.llm = LLMHandler()
        self.current_patient = None
    
    def start_new_patient(self, severity: str = None):
        """Initialize a new patient simulation"""
        self.current_patient = self.patient_gen.generate_patient(severity)
        self.llm.reset_conversation()
        return self.current_patient
    
    def process_trainee_message(self, message: str) -> str:
        """
        Process trainee's message and generate patient response
        
        Args:
            message: What the medical trainee said
            
        Returns:
            Patient's response
        """
        if not self.current_patient:
            return "[Error: No patient initialized. Start a new patient first.]"
        
        # Get relevant examples from RAG
        rag_context = self.rag_client.get_context_for_question(
            trainee_question=message,
            patient_profile=self.current_patient
        )
        
        # Generate response using LLM
        response = self.llm.generate_response(
            trainee_message=message,
            patient_profile=self.current_patient,
            rag_context=rag_context
        )
        
        return response
    
    def display_patient_info(self):
        """Display current patient information"""
        if not self.current_patient:
            print("No patient currently active.")
            return
        
        p = self.current_patient
        print("\n" + "="*60)
        print("CURRENT PATIENT PROFILE")
        print("="*60)
        print(f"Name: {p['name']}")
        print(f"Age: {p['age']}")
        print(f"Gender: {p['gender']}")
        print(f"Background: {p['backstory']}")
        print(f"Depression Severity: {p['severity']}")
        print(f"PHQ-9 Score: {p['phq9_score']}/27")
        print("="*60 + "\n")

def main():
    """Main CLI interface"""
    
    print("\n" + "="*60)
    print("MEDICAL TRAINING CHATBOT - PATIENT SIMULATOR")
    print("="*60)
    print("\nInitializing system...")
    
    # Initialize chatbot
    bot = MedicalChatbot()
    
    # Check RAG connection
    print("Checking connection to RAG server...")
    if bot.rag_client.check_connection():
        print("✓ Connected to RAG server")
    else:
        print("⚠ Warning: Cannot connect to RAG server")
        print(f"  Make sure SSH tunnel is running:")
        print(f"  ssh -L 8000:localhost:8000 riya@endurance -N")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Start first patient
    print("\nGenerating patient...")
    patient = bot.start_new_patient()
    bot.display_patient_info()
    
    print("You can now begin the interview.")
    print("Commands:")
    print("  /new [severity] - Start with new patient (optional: Mild, Moderate, Severe)")
    print("  /info - Show current patient info")
    print("  /quit - Exit")
    print("\n" + "-"*60 + "\n")
    
    # Main conversation loop
    while True:
        try:
            # Get trainee input
            trainee_input = input("Doctor: ").strip()
            
            if not trainee_input:
                continue
            
            # Handle commands
            if trainee_input.startswith('/'):
                command_parts = trainee_input.split()
                command = command_parts[0].lower()
                
                if command == '/quit':
                    print("\nEnding session. Goodbye!")
                    break
                
                elif command == '/info':
                    bot.display_patient_info()
                    continue
                
                elif command == '/new':
                    severity = command_parts[1] if len(command_parts) > 1 else None
                    if severity and severity not in bot.patient_gen.SEVERITIES:
                        print(f"Invalid severity. Choose from: {', '.join(bot.patient_gen.SEVERITIES)}")
                        continue
                    
                    print("\nGenerating new patient...")
                    patient = bot.start_new_patient(severity)
                    bot.display_patient_info()
                    print("You can now begin the interview.\n")
                    continue
                
                else:
                    print(f"Unknown command: {command}")
                    continue
            
            # Process trainee's message
            print(f"\n{patient['name']}: ", end="", flush=True)
            response = bot.process_trainee_message(trainee_input)
            print(response + "\n")
            
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Continuing...\n")

if __name__ == "__main__":
    main()