"""
Chainlit UI for Medical Training Chatbot
Professional web interface for patient simulation and evaluation
"""

import chainlit as cl
from patient_generator import PatientGenerator
from rag_client import RAGClient
from llm_handler import LLMHandler
from evaluator import ConversationEvaluator

# Initialize components
patient_gen = PatientGenerator()
rag_client = RAGClient()

@cl.on_chat_start
async def start():
    """Initialize chat session with new patient"""
    
    # Welcome message
    await cl.Message(
        content="# 🏥 Medical Training Chatbot\n\nWelcome! I'm here to help you practice clinical interviewing skills.",
        author="System"
    ).send()
    
    # Check RAG connection
    if not rag_client.check_connection():
        await cl.Message(
            content="⚠️ **Warning:** RAG server not connected. Make sure SSH tunnel is running:\n```bash\nssh -L 8000:localhost:8000 riya@endurance -N```",
            author="System"
        ).send()
    
    # Generate random patient immediately
    await cl.Message(
        content="Generating random patient...",
        author="System"
    ).send()
    
    await setup_patient_session(None)

async def setup_patient_session(severity=None):
    """Common setup for a new patient"""
    patient = patient_gen.generate_patient(severity)
    llm = LLMHandler()
    evaluator = ConversationEvaluator()
    
    # Store in session
    cl.user_session.set("patient", patient)
    cl.user_session.set("llm", llm)
    cl.user_session.set("evaluator", evaluator)
    cl.user_session.set("interaction_state", "chatting") # chatting, assessing_severity, assessing_score
    
    # Display patient info
    await show_patient_info(patient)
    
    # Greeting from patient
    greeting = f"Hello doctor... I'm {patient['name']}. Thanks for seeing me today."
    
    await cl.Message(
        content=greeting,
        author=patient['name']
    ).send()
    
    # Update actions
    await update_main_actions()

async def show_patient_info(patient):
    """Display patient info card"""
    patient_info = f"""## Current Patient
    
**Name:** {patient['name']}  
**Age:** {patient['age']}  
**Gender:** {patient['gender'].capitalize()}  

**Background:**  
{patient['backstory']}

---

**Depression Severity:** {patient['severity']}  
**PHQ-9 Score:** {patient['phq9_score']}/27
"""
    await cl.Message(content=patient_info, author="Patient Info").send()

async def update_main_actions():
    """Set the standard action buttons"""
    actions = [
        cl.Action(name="view_info", value="info", payload={"value": "info"}, label="📋 Patient Info"),
        cl.Action(name="end_session", value="end", payload={"value": "end"}, label="📊 End Session"),
        cl.Action(name="new_patient", value="new", payload={"value": "new"}, label="👤 New Patient")
    ]
    # await cl.ChatSettings(actions).send() - REMOVED: Incorrect usage actions are sent in message below

    
    await cl.Message(
        content="**Interview in progress.**",
        actions=actions,
        author="System"
    ).send()

@cl.action_callback("gen_patient")
async def on_gen_patient(action: cl.Action):
    value = action.payload.get("value", "random")
    severity = value if value != "random" else None
    await action.remove()
    
    msg = cl.Message(content=f"Generating {severity if severity else 'random'} patient...", author="System")
    await msg.send()
    
    await setup_patient_session(severity)

@cl.action_callback("view_info")
async def on_view_info(action: cl.Action):
    patient = cl.user_session.get("patient")
    if patient:
        await show_patient_info(patient)
    else:
        await cl.Message(content="No active patient.", author="System").send()

@cl.action_callback("new_patient")
async def on_new_patient(action: cl.Action):
    # Ask for confirmation if in middle of chat? Nah, just show options.
    await cl.Message(
        content="Start a new patient? Select severity:",
        actions=[
            cl.Action(name="gen_patient", value="random", payload={"value": "random"}, label="🎲 Random"),
            cl.Action(name="gen_patient", value="Mild", payload={"value": "Mild"}, label="1️⃣ Mild"),
            cl.Action(name="gen_patient", value="Moderate", payload={"value": "Moderate"}, label="2️⃣ Moderate"),
            cl.Action(name="gen_patient", value="Severe", payload={"value": "Severe"}, label="3️⃣ Severe"),
             cl.Action(name="cancel_new", value="cancel", payload={"value": "cancel"}, label="❌ Cancel")
        ],
        author="System"
    ).send()

@cl.action_callback("cancel_new")
async def on_cancel_new(action: cl.Action):
    await action.remove()
    await cl.Message(content="Cancelled.", author="System").send()

@cl.action_callback("end_session")
async def on_end_session(action: cl.Action):
    evaluator = cl.user_session.get("evaluator")
    if not evaluator or len(evaluator.conversation_log) == 0:
        await cl.Message(
            content="❌ No conversation to evaluate. Please conduct an interview first.",
            author="System"
        ).send()
        return

    # Start assessment flow
    cl.user_session.set("interaction_state", "assessing_severity")
    
    await cl.Message(
        content="## 📋 Assessment: Severity\nBased on your interview, what is the depression severity?",
        actions=[
            cl.Action(name="assess_severity", value="Minimal", payload={"value": "Minimal"}, label="Minimal (0-4)"),
            cl.Action(name="assess_severity", value="Mild", payload={"value": "Mild"}, label="Mild (5-9)"),
            cl.Action(name="assess_severity", value="Moderate", payload={"value": "Moderate"}, label="Moderate (10-14)"),
            cl.Action(name="assess_severity", value="Moderately Severe", payload={"value": "Moderately Severe"}, label="Mod. Severe (15-19)"),
            cl.Action(name="assess_severity", value="Severe", payload={"value": "Severe"}, label="Severe (20-27)")
        ],
        author="System"
    ).send()

@cl.action_callback("assess_severity")
async def on_assess_severity(action: cl.Action):
    severity = action.payload.get("value")
    cl.user_session.set("temp_assessment_severity", severity)
    await action.remove()
    
    cl.user_session.set("interaction_state", "assessing_score")
    
    await cl.Message(
        content=f"**Selected Severity:** {severity}\n\nNow, please enter the estimated **PHQ-9 Score (0-27)** below:",
        author="System"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    """Handle all incoming messages"""
    
    state = cl.user_session.get("interaction_state")
    
    if state == "assessing_score":
        await handle_score_input(message)
        return
        
    if state != "chatting":
        # Ignore or warn if in weird state
        return

    # Normal conversation
    patient = cl.user_session.get("patient")
    llm = cl.user_session.get("llm")
    evaluator = cl.user_session.get("evaluator")
    
    if not patient or not llm or not evaluator:
        await cl.Message(content="❌ Session error. Please refresh.", author="System").send()
        return
    
    # Generate response
    rag_context = rag_client.get_context_for_question(message.content, patient)
    response = llm.generate_response(message.content, patient, rag_context)
    
    evaluator.log_exchange(message.content, response)
    
    # Actions to show after every response
    actions = [
        cl.Action(name="view_info", value="info", payload={"value": "info"}, label="📋 Patient Info"),
        cl.Action(name="end_session", value="end", payload={"value": "end"}, label="📊 End Session"),
        cl.Action(name="new_patient", value="new", payload={"value": "new"}, label="👤 New Patient")
    ]
    
    await cl.Message(content=response, author=patient['name'], actions=actions).send()

async def handle_score_input(message: cl.Message):
    try:
        score_text = ''.join(filter(str.isdigit, message.content))
        if not score_text:
            raise ValueError("No number found")
            
        score = int(score_text)
        if not 0 <= score <= 27:
            await cl.Message(content="❌ Score must be between 0-27. Please try again.", author="System").send()
            return

        # Complete assessment
        severity = cl.user_session.get("temp_assessment_severity")
        evaluator = cl.user_session.get("evaluator")
        patient = cl.user_session.get("patient")
        
        evaluator.doctor_assessment = {'severity': severity, 'score': score}
        
        await cl.Message(content="⏳ Generating evaluation...", author="System").send()
        
        # Run evaluation logic
        phq9_eval = evaluator.evaluate_phq9_accuracy(patient['severity'], patient['phq9_score'])
        empathy_eval = evaluator.evaluate_empathy_with_llm()
        
        overall_score = 0
        if 'error' not in phq9_eval and 'error' not in empathy_eval:
            overall_score = (phq9_eval['diagnostic_accuracy'] * 0.5 + empathy_eval['overall_score'] * 0.5)
            
        report = format_evaluation_report(overall_score, phq9_eval, empathy_eval, patient)
        
        await cl.Message(content=report, author="Evaluation").send()
        
        # Reset state
        cl.user_session.set("interaction_state", "done")
        
        # Offer new patient
        await cl.Message(
            content="Start a new patient?",
            actions=[
                cl.Action(name="new_patient", value="new", payload={"value": "new"}, label="👤 New Patient")
            ],
            author="System"
        ).send()
        
    except ValueError:
        await cl.Message(content="❌ Please enter a valid number (0-27).", author="System").send()

def format_evaluation_report(overall_score, phq9_eval, empathy_eval, patient):
    """Format evaluation as markdown"""
    
    report = f"""# 📊 Performance Evaluation

## Overall Score: {overall_score:.1f}/100

"""
    
    if overall_score >= 85:
        report += "### OUTSTANDING\n\n"
    elif overall_score >= 75:
        report += "### VERY GOOD\n\n"
    elif overall_score >= 65:
        report += "### GOOD\n\n"
    else:
        report += "### NEEDS IMPROVEMENT\n\n"
    
    report += "---\n\n"
    
    # PHQ-9
    if 'error' not in phq9_eval:
        report += f"""## Part 1: Diagnostic Accuracy ({phq9_eval['diagnostic_accuracy']:.1f}%)

**Your Assessment:** {phq9_eval['doctor_assessment']['severity']} (Score: {phq9_eval['doctor_assessment']['score']})  
**Actual:** {phq9_eval['actual']['severity']} (Score: {phq9_eval['actual']['score']})

{phq9_eval['severity_feedback']}

---

"""
    
    # Empathy
    if 'error' not in empathy_eval:
        report += f"""## Part 2: Empathy ({empathy_eval['overall_score']:.1f}%)

**Understanding:** {empathy_eval.get('understanding', {}).get('score', 0):.0f}%  
**Communication:** {empathy_eval.get('communication', {}).get('score', 0):.0f}%  
**Intention to Help:** {empathy_eval.get('intention', {}).get('score', 0):.0f}%

"""
        if empathy_eval.get('strengths'):
            report += f"\n✨ **Strengths:** {empathy_eval['strengths']}\n"
        if empathy_eval.get('improvements'):
            report += f"\n📚 **Improve:** {empathy_eval['improvements']}\n"
    
    return report