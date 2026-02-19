#!/usr/bin/env python3
"""
Medical Training Chatbot - Patient Simulator
Simulates depressed patients for medical student training
With advanced evaluation: PHQ-9 diagnostic accuracy + LLM-based empathy scoring
"""

from patient_generator import PatientGenerator
from rag_client import RAGClient
from llm_handler import LLMHandler
from evaluator import ConversationEvaluator
from config import SERVER_URL

class MedicalChatbot:
    """Main chatbot orchestrator"""
    
    def __init__(self):
        self.patient_gen = PatientGenerator()
        self.rag_client = RAGClient()
        self.llm = LLMHandler()
        self.current_patient = None
        self.evaluator = None
    
    def start_new_patient(self, severity: str = None):
        """Initialize a new patient simulation"""
        self.current_patient = self.patient_gen.generate_patient(severity)
        self.llm.reset_conversation()
        self.evaluator = ConversationEvaluator()
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
        
        # Log the exchange for evaluation
        self.evaluator.log_exchange(message, response)
        
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
    
    def end_session(self):
        """End the session and show comprehensive evaluation"""
        if not self.current_patient or not self.evaluator:
            print("No active session to evaluate.")
            return
        
        # Check if conversation happened
        if len(self.evaluator.conversation_log) == 0:
            print("\nNo conversation to evaluate. Please conduct an interview first.")
            return
        
        # Generate and display evaluation
        evaluation = self.evaluator.generate_full_evaluation(self.current_patient)
        self.evaluator.display_evaluation(evaluation)

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
    print("\nCommands:")
    print("  /end    - End session and get comprehensive evaluation")
    print("  /new [severity] - Start with new patient (optional: Mild, Moderate, Severe)")
    print("  /info   - Show current patient info again")
    print("  /quit   - Exit without evaluation")
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
                    print("\nExiting without evaluation. Goodbye!")
                    break
                
                elif command == '/info':
                    bot.display_patient_info()
                    continue
                
                elif command == '/end':
                    bot.end_session()
                    
                    # Ask if they want to try another patient
                    response = input("\nStart a new patient? (y/n): ")
                    if response.lower() == 'y':
                        severity = input("Severity (or press Enter for random): ").strip()
                        severity = severity if severity else None
                        
                        print("\nGenerating new patient...")
                        patient = bot.start_new_patient(severity)
                        bot.display_patient_info()
                        print("You can now begin the interview.\n")
                    else:
                        print("\nGoodbye!")
                        break
                    continue
                
                elif command == '/new':
                    severity = command_parts[1] if len(command_parts) > 1 else None
                    if severity and severity not in bot.patient_gen.SEVERITIES:
                        print(f"Invalid severity. Choose from: {', '.join(bot.patient_gen.SEVERITIES)}")
                        continue
                    
                    # Show evaluation for current patient if conversation happened
                    if bot.evaluator and len(bot.evaluator.conversation_log) > 0:
                        print("\nEnding current session first...")
                        bot.end_session()
                    
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
            print("\n\nSession interrupted.")
            if bot.evaluator and len(bot.evaluator.conversation_log) > 0:
                print("Generating evaluation...")
                bot.end_session()
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            print("Continuing...\n")

if __name__ == "__main__":
    main()