"""
Advanced Evaluation System for Medical Training Chatbot
Includes PHQ-9 diagnostic accuracy and LLM-based empathy scoring
"""

import anthropic
from typing import List, Dict, Tuple
from datetime import datetime
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

class ConversationEvaluator:
    """Evaluates doctor's performance using PHQ-9 accuracy and LLM-based empathy scoring"""
    
    # PHQ-9 severity levels and score ranges
    PHQ9_LEVELS = {
        "Minimal": (0, 4),
        "Mild": (5, 9),
        "Moderate": (10, 14),
        "Moderately Severe": (15, 19),
        "Severe": (20, 27)
    }
    
    def __init__(self):
        self.conversation_log = []
        self.doctor_assessment = None
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def log_exchange(self, doctor_msg: str, patient_msg: str):
        """Log a conversation exchange"""
        self.conversation_log.append({
            'timestamp': datetime.now().isoformat(),
            'doctor': doctor_msg,
            'patient': patient_msg
        })
    
    def get_doctor_assessment(self) -> Tuple[str, int]:
        """
        Prompt doctor for their PHQ-9 assessment
        Returns: (severity_level, phq9_score)
        """
        print("\n" + "="*60)
        print("PLEASE PROVIDE YOUR ASSESSMENT")
        print("="*60)
        print("\nBased on your interview, what is your diagnosis?")
        print("\nDepression Severity Levels:")
        print("  1. Minimal (0-4)")
        print("  2. Mild (5-9)")
        print("  3. Moderate (10-14)")
        print("  4. Moderately Severe (15-19)")
        print("  5. Severe (20-27)")
        
        while True:
            try:
                severity_input = input("\nEnter severity level (1-5): ").strip()
                severity_map = {
                    "1": "Minimal",
                    "2": "Mild", 
                    "3": "Moderate",
                    "4": "Moderately Severe",
                    "5": "Severe"
                }
                
                if severity_input not in severity_map:
                    print("Invalid input. Please enter 1-5.")
                    continue
                
                severity = severity_map[severity_input]
                
                # Get PHQ-9 score
                score_input = input(f"Enter estimated PHQ-9 score (0-27): ").strip()
                score = int(score_input)
                
                if not 0 <= score <= 27:
                    print("Score must be between 0-27.")
                    continue
                
                # Validate score matches severity
                min_score, max_score = self.PHQ9_LEVELS[severity]
                if not min_score <= score <= max_score:
                    print(f"Warning: Score {score} doesn't match {severity} range ({min_score}-{max_score})")
                    confirm = input("Continue anyway? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                
                self.doctor_assessment = {
                    'severity': severity,
                    'score': score
                }
                
                return severity, score
                
            except ValueError:
                print("Invalid input. Please enter numbers only.")
                continue
    
    def evaluate_phq9_accuracy(self, actual_severity: str, actual_score: int) -> Dict:
        """
        Evaluate diagnostic accuracy
        Returns accuracy scores and feedback
        """
        if not self.doctor_assessment:
            return {
                'error': 'No doctor assessment provided'
            }
        
        doc_severity = self.doctor_assessment['severity']
        doc_score = self.doctor_assessment['score']
        
        # Calculate severity accuracy (exact match or one level off)
        severity_levels = list(self.PHQ9_LEVELS.keys())
        actual_idx = severity_levels.index(actual_severity)
        doc_idx = severity_levels.index(doc_severity)
        
        severity_diff = abs(actual_idx - doc_idx)
        
        if severity_diff == 0:
            severity_accuracy = 100
            severity_feedback = "✓ Correct severity level!"
        elif severity_diff == 1:
            severity_accuracy = 75
            severity_feedback = f"○ Close - off by one level ({'higher' if doc_idx > actual_idx else 'lower'} than actual)"
        else:
            severity_accuracy = max(0, 100 - (severity_diff * 25))
            severity_feedback = f"✗ Incorrect - {severity_diff} levels off"
        
        # Calculate score accuracy
        score_diff = abs(doc_score - actual_score)
        score_accuracy = max(0, 100 - (score_diff * 5))  # 5% penalty per point off
        
        if score_diff == 0:
            score_feedback = "✓ Exact score!"
        elif score_diff <= 2:
            score_feedback = f"○ Very close (off by {score_diff})"
        elif score_diff <= 5:
            score_feedback = f"△ Somewhat close (off by {score_diff})"
        else:
            score_feedback = f"✗ Significant difference (off by {score_diff})"
        
        # Overall diagnostic accuracy
        diagnostic_accuracy = (severity_accuracy * 0.6 + score_accuracy * 0.4)
        
        return {
            'diagnostic_accuracy': diagnostic_accuracy,
            'severity_accuracy': severity_accuracy,
            'score_accuracy': score_accuracy,
            'severity_feedback': severity_feedback,
            'score_feedback': score_feedback,
            'doctor_assessment': {
                'severity': doc_severity,
                'score': doc_score
            },
            'actual': {
                'severity': actual_severity,
                'score': actual_score
            }
        }
    
    def evaluate_empathy_with_llm(self) -> Dict:
        """
        Use Claude to evaluate empathy in the conversation
        Analyzes: understanding pain, communicating understanding, intention to help
        """
        
        # Format conversation for analysis
        conversation_text = self._format_conversation_for_analysis()
        
        # Create evaluation prompt
        evaluation_prompt = f"""You are an expert in medical communication and empathy assessment. Analyze this doctor-patient conversation and evaluate the doctor's empathy across three dimensions:

CONVERSATION:
{conversation_text}

Please evaluate the doctor's empathy on these three dimensions (score each 0-100):

1. UNDERSTANDING PAIN & SUFFERING
   - Does the doctor recognize and acknowledge the patient's emotional distress?
   - Do they show awareness of how depression affects the patient's life?
   - Score: 0 (no recognition) to 100 (deep understanding demonstrated)

2. COMMUNICATING UNDERSTANDING  
   - Does the doctor verbally express their understanding to the patient?
   - Do they use reflective listening and validation?
   - Do they avoid dismissive or minimizing language?
   - Score: 0 (no communication of understanding) to 100 (excellent communication)

3. INTENTION TO HELP
   - Does the doctor convey genuine care and concern?
   - Do they offer support or express desire to help?
   - Do they create a safe, non-judgmental space?
   - Score: 0 (no helping intention shown) to 100 (strong helping intention)

Provide your response in this exact format:

UNDERSTANDING_SCORE: [0-100]
UNDERSTANDING_EVIDENCE: [Brief quote or description from conversation]
UNDERSTANDING_FEEDBACK: [One sentence of constructive feedback]

COMMUNICATION_SCORE: [0-100]
COMMUNICATION_EVIDENCE: [Brief quote or description from conversation]
COMMUNICATION_FEEDBACK: [One sentence of constructive feedback]

INTENTION_SCORE: [0-100]
INTENTION_EVIDENCE: [Brief quote or description from conversation]
INTENTION_FEEDBACK: [One sentence of constructive feedback]

OVERALL_EMPATHY_SCORE: [Average of three scores]
STRENGTHS: [What the doctor did well]
AREAS_FOR_IMPROVEMENT: [What could be better]"""

        try:
            # Call Claude for evaluation
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                messages=[{
                    "role": "user",
                    "content": evaluation_prompt
                }]
            )
            
            evaluation_text = response.content[0].text
            
            # Parse the response
            empathy_eval = self._parse_empathy_evaluation(evaluation_text)
            
            return empathy_eval
            
        except Exception as e:
            return {
                'error': f"Empathy evaluation failed: {str(e)}",
                'overall_score': 0
            }
    
    def _format_conversation_for_analysis(self) -> str:
        """Format conversation log for LLM analysis"""
        formatted = []
        for i, exchange in enumerate(self.conversation_log, 1):
            formatted.append(f"Exchange {i}:")
            formatted.append(f"Doctor: {exchange['doctor']}")
            formatted.append(f"Patient: {exchange['patient']}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _parse_empathy_evaluation(self, eval_text: str) -> Dict:
        """Parse Claude's evaluation response"""
        lines = eval_text.strip().split('\n')
        
        result = {
            'understanding': {},
            'communication': {},
            'intention': {},
            'overall_score': 0,
            'strengths': '',
            'improvements': ''
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('UNDERSTANDING_SCORE:'):
                result['understanding']['score'] = self._extract_number(line)
            elif line.startswith('UNDERSTANDING_EVIDENCE:'):
                result['understanding']['evidence'] = line.split(':', 1)[1].strip()
            elif line.startswith('UNDERSTANDING_FEEDBACK:'):
                result['understanding']['feedback'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('COMMUNICATION_SCORE:'):
                result['communication']['score'] = self._extract_number(line)
            elif line.startswith('COMMUNICATION_EVIDENCE:'):
                result['communication']['evidence'] = line.split(':', 1)[1].strip()
            elif line.startswith('COMMUNICATION_FEEDBACK:'):
                result['communication']['feedback'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('INTENTION_SCORE:'):
                result['intention']['score'] = self._extract_number(line)
            elif line.startswith('INTENTION_EVIDENCE:'):
                result['intention']['evidence'] = line.split(':', 1)[1].strip()
            elif line.startswith('INTENTION_FEEDBACK:'):
                result['intention']['feedback'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('OVERALL_EMPATHY_SCORE:'):
                result['overall_score'] = self._extract_number(line)
            elif line.startswith('STRENGTHS:'):
                result['strengths'] = line.split(':', 1)[1].strip()
            elif line.startswith('AREAS_FOR_IMPROVEMENT:'):
                result['improvements'] = line.split(':', 1)[1].strip()
        
        return result
    
    def _extract_number(self, text: str) -> float:
        """Extract number from text like 'SCORE: 85'"""
        try:
            parts = text.split(':')
            if len(parts) > 1:
                # Extract just the number, handling ranges like "85-90" or text
                num_text = parts[1].strip().split()[0]
                # Remove any non-numeric characters except decimal point
                num_text = ''.join(c for c in num_text if c.isdigit() or c == '.')
                return float(num_text) if num_text else 0
        except:
            pass
        return 0
    
    def generate_full_evaluation(self, patient_profile: Dict) -> Dict:
        """
        Generate complete evaluation report
        Combines PHQ-9 accuracy and empathy scoring
        """
        
        # Get doctor's assessment
        print("\n" + "="*60)
        print("TIME FOR YOUR ASSESSMENT")
        print("="*60)
        doc_severity, doc_score = self.get_doctor_assessment()
        
        # Evaluate diagnostic accuracy
        print("\n⏳ Evaluating diagnostic accuracy...")
        phq9_eval = self.evaluate_phq9_accuracy(
            patient_profile['severity'],
            patient_profile['phq9_score']
        )
        
        # Evaluate empathy using LLM
        print("⏳ Analyzing empathy and communication (this may take 10-15 seconds)...")
        empathy_eval = self.evaluate_empathy_with_llm()
        
        # Calculate overall score
        if 'error' not in phq9_eval and 'error' not in empathy_eval:
            overall_score = (
                phq9_eval['diagnostic_accuracy'] * 0.5 +  # 50% weight
                empathy_eval['overall_score'] * 0.5        # 50% weight
            )
        else:
            overall_score = 0
        
        return {
            'overall_score': overall_score,
            'phq9_evaluation': phq9_eval,
            'empathy_evaluation': empathy_eval,
            'patient_profile': patient_profile,
            'conversation_length': len(self.conversation_log)
        }
    
    def display_evaluation(self, evaluation: Dict):
        """Display comprehensive evaluation report"""
        
        print("\n" + "="*70)
        print("              COMPREHENSIVE PERFORMANCE EVALUATION")
        print("="*70)
        
        # Overall Score
        overall = evaluation['overall_score']
        print(f"\n🎯 OVERALL PERFORMANCE: {overall:.1f}/100\n")
        
        if overall >= 85:
            print("   ⭐⭐⭐ OUTSTANDING - Excellent diagnostic and interpersonal skills")
        elif overall >= 75:
            print("   ⭐⭐ VERY GOOD - Strong performance with minor areas to improve")
        elif overall >= 65:
            print("   ⭐ GOOD - Solid foundation, some skill development needed")
        elif overall >= 50:
            print("   ○ SATISFACTORY - Basic competency, significant improvement needed")
        else:
            print("   △ NEEDS IMPROVEMENT - Requires focused skill development")
        
        print("\n" + "="*70)
        
        # Part 1: PHQ-9 Diagnostic Accuracy
        phq9 = evaluation['phq9_evaluation']
        
        if 'error' not in phq9:
            print("\n📋 PART 1: DIAGNOSTIC ACCURACY")
            print("-"*70)
            print(f"\nOverall Diagnostic Score: {phq9['diagnostic_accuracy']:.1f}/100\n")
            
            print("Your Assessment:")
            print(f"  Severity: {phq9['doctor_assessment']['severity']}")
            print(f"  PHQ-9 Score: {phq9['doctor_assessment']['score']}/27")
            
            print("\nActual Patient Profile:")
            print(f"  Severity: {phq9['actual']['severity']}")
            print(f"  PHQ-9 Score: {phq9['actual']['score']}/27")
            
            print(f"\nSeverity Assessment: {phq9['severity_accuracy']:.0f}%")
            print(f"  {phq9['severity_feedback']}")
            
            print(f"\nScore Estimation: {phq9['score_accuracy']:.0f}%")
            print(f"  {phq9['score_feedback']}")
        
        # Part 2: Empathy Evaluation
        empathy = evaluation['empathy_evaluation']
        
        if 'error' not in empathy:
            print("\n" + "="*70)
            print("\n💚 PART 2: EMPATHY & COMMUNICATION")
            print("-"*70)
            print(f"\nOverall Empathy Score: {empathy['overall_score']:.1f}/100\n")
            
            # Understanding Pain & Suffering
            if 'understanding' in empathy and empathy['understanding']:
                print(f"1️⃣  Understanding Pain & Suffering: {empathy['understanding'].get('score', 0):.0f}/100")
                if 'evidence' in empathy['understanding']:
                    print(f"   Evidence: {empathy['understanding']['evidence']}")
                if 'feedback' in empathy['understanding']:
                    print(f"   💡 {empathy['understanding']['feedback']}")
                print()
            
            # Communicating Understanding
            if 'communication' in empathy and empathy['communication']:
                print(f"2️⃣  Communicating Understanding: {empathy['communication'].get('score', 0):.0f}/100")
                if 'evidence' in empathy['communication']:
                    print(f"   Evidence: {empathy['communication']['evidence']}")
                if 'feedback' in empathy['communication']:
                    print(f"   💡 {empathy['communication']['feedback']}")
                print()
            
            # Intention to Help
            if 'intention' in empathy and empathy['intention']:
                print(f"3️⃣  Intention to Help: {empathy['intention'].get('score', 0):.0f}/100")
                if 'evidence' in empathy['intention']:
                    print(f"   Evidence: {empathy['intention']['evidence']}")
                if 'feedback' in empathy['intention']:
                    print(f"   💡 {empathy['intention']['feedback']}")
                print()
            
            # Strengths and Improvements
            if empathy.get('strengths'):
                print("-"*70)
                print("\n✨ YOUR STRENGTHS:")
                print(f"   {empathy['strengths']}")
            
            if empathy.get('improvements'):
                print("\n📚 AREAS FOR IMPROVEMENT:")
                print(f"   {empathy['improvements']}")
        
        # Summary
        print("\n" + "="*70)
        print(f"\n📊 Session Statistics:")
        print(f"   Conversation length: {evaluation['conversation_length']} exchanges")
        print(f"   Patient severity: {evaluation['patient_profile']['severity']}")
        print(f"   Diagnostic accuracy: {phq9.get('diagnostic_accuracy', 0):.1f}%")
        print(f"   Empathy score: {empathy.get('overall_score', 0):.1f}%")
        
        print("\n" + "="*70)
        print()
