import anthropic
from typing import List, Dict
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS, TEMPERATURE


class LLMHandler:
    """Handles interaction with Claude API"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history = []
    
    def create_system_prompt(self, patient_profile: Dict, rag_context: str = "") -> str:
        """Create system prompt for patient simulation"""
        
        prompt = f"""You are simulating a patient in a medical training scenario. You must stay completely in character as this patient.

PATIENT PROFILE:
- Name: {patient_profile['name']}
- Age: {patient_profile['age']}
- Gender: {patient_profile['gender']}
- Background: {patient_profile['backstory']}
- Depression Severity: {patient_profile['severity']}
- PHQ-9 Score: {patient_profile['phq9_score']}/27

{rag_context}

INSTRUCTIONS:
1. Respond naturally as this patient would
2. Show symptoms consistent with {patient_profile['severity']} depression
3. Be authentic, don't be overly clinical or rehearsed
4. Show appropriate emotions based on the topic
5. Sometimes be hesitant or vague if the topic is difficult
6. Build rapport gradually, don't share everything immediately
7. Keep responses conversational, not too long (2-4 sentences usually)
8. Use natural speech patterns, including filler words occasionally

Remember: You ARE the patient. Don't break character or explain your responses."""
        
        return prompt
    
    def generate_response(self, 
                         trainee_message: str,
                         patient_profile: Dict,
                         rag_context: str = "") -> str:
        """
        Generate patient response to trainee's question
        
        Args:
            trainee_message: What the medical trainee said
            patient_profile: Current patient's profile
            rag_context: RAG examples (optional)
            
        Returns:
            Patient's response
        """
        
        # Add trainee message to history
        self.conversation_history.append({
            "role": "user",
            "content": trainee_message
        })
        
        # Create system prompt
        system_prompt = self.create_system_prompt(patient_profile, rag_context)
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=self.conversation_history
            )
            
            # Extract response text
            patient_response = response.content[0].text
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": patient_response
            })
            
            return patient_response
            
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    def reset_conversation(self):
        """Clear conversation history for new patient"""
        self.conversation_history = []