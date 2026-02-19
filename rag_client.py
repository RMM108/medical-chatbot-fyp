import requests
from typing import List, Dict, Optional
from config import SERVER_URL, RAG_LIMIT, MIN_RELEVANCE_SCORE


class RAGClient:
    """Client for querying the RAG system"""
    
    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url
    
    def get_relevant_examples(self, 
                             query: str,
                             patient_profile: Dict,
                             limit: int = RAG_LIMIT) -> List[Dict]:
        """
        Get relevant patient dialogue examples from RAG system
        
        Args:
            query: The trainee's question or topic
            patient_profile: Current patient's profile (for filtering)
            limit: Number of examples to retrieve
            
        Returns:
            List of relevant dialogue examples
        """
        try:
            search_data = {
                "query": query,
                "severity": patient_profile['severity'],
                "limit": limit,
                "chunk_type": "chunk"
            }
            
            response = requests.post(
                f"{self.server_url}/search",
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Filter by relevance score
                filtered_results = [
                    r for r in results 
                    if r['score'] >= MIN_RELEVANCE_SCORE
                ]
                
                return filtered_results
            else:
                print(f"Warning: RAG search failed with status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Warning: RAG query failed: {e}")
            return []
    
    def format_examples_for_prompt(self, examples: List[Dict]) -> str:
        """Format RAG examples for inclusion in LLM prompt"""
        
        if not examples:
            return "No specific examples available."
        
        formatted = "Here are examples of how similar patients respond:\n\n"
        
        for i, ex in enumerate(examples, 1):
            formatted += f"Example {i} (Patient {ex['participant_id']}, PHQ-9: {ex['phq9_total']}):\n"
            formatted += f'"{ex["text"][:300]}..."\n\n'
        
        return formatted
    
    def get_context_for_question(self, 
                                 trainee_question: str,
                                 patient_profile: Dict) -> str:
        """
        Get formatted RAG context for a specific trainee question
        
        Returns formatted string ready for LLM prompt
        """
        examples = self.get_relevant_examples(
            query=trainee_question,
            patient_profile=patient_profile
        )
        
        return self.format_examples_for_prompt(examples)
    
    def check_connection(self) -> bool:
        """Check if RAG server is accessible"""
        try:
            response = requests.get(f"{self.server_url}/", timeout=5)
            return response.status_code == 200
        except:
            return False