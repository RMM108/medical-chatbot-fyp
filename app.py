"""
Medical Training Chatbot with Student Progress Tracking
Chainlit UI with authentication, session tracking, and visualizations
"""

import chainlit as cl
from patient_generator import PatientGenerator
from rag_client import RAGClient
from llm_handler import LLMHandler
from evaluator import ConversationEvaluator
from database import StudentDatabase
from visualizations import ProgressVisualizer
from datetime import datetime

# Initialize components
patient_gen = PatientGenerator()
rag_client = RAGClient()
db = StudentDatabase()
viz = ProgressVisualizer(db)

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Handle login authentication"""
    
    # Check if this is a registration attempt
    # Registration format: username|email|fullname|institution
    if '|' in username:
        parts = username.split('|')
        if len(parts) == 4:
            reg_username, email, full_name, institution = parts
            
            # Attempt registration
            student_id = db.register_student(
                username=reg_username.strip(),
                email=email.strip(),
                password=password,
                full_name=full_name.strip(),
                institution=institution.strip()
            )
            
            if student_id:
                return cl.User(
                    identifier=reg_username,
                    metadata={
                        "student_id": student_id,
                        "full_name": full_name.strip(),
                        "email": email.strip(),
                        "institution": institution.strip(),
                        "new_user": True
                    }
                )
            else:
                # Registration failed (duplicate username/email)
                return None
    
    # Normal login attempt
    student = db.authenticate_student(username, password)
    
    if student:
        return cl.User(
            identifier=username,
            metadata={
                "student_id": student['student_id'],
                "full_name": student['full_name'],
                "email": student['email'],
                "institution": student['institution'],
                "new_user": False
            }
        )
    return None

@cl.on_chat_start
async def start():
    """Initialize chat session with authenticated user"""
    
    # Get authenticated user
    user = cl.user_session.get("user")
    student_id = user.metadata.get("student_id")
    full_name = user.metadata.get("full_name") or user.identifier
    is_new_user = user.metadata.get("new_user", False)
    
    # Welcome message
    if is_new_user:
        welcome_msg = f"""# 🎉 Welcome to Medical Training Chatbot, {full_name}!

Thank you for registering! You're now ready to practice clinical interviewing with AI-simulated patients.

## 🎯 How It Works

1. **Interview Patients**: Practice diagnostic interviews with realistic patient simulations
2. **Get Evaluated**: Receive detailed feedback on your diagnostic accuracy and empathy
3. **Track Progress**: See your improvement over time with interactive charts
4. **Build Skills**: Master clinical interviewing through repeated practice

Let's start your first session!
"""
    else:
        welcome_msg = f"# 🏥 Welcome back, {full_name}!\n\nReady to practice your clinical interviewing skills?"
    
    await cl.Message(content=welcome_msg, author="System").send()
    
    # Show registration instructions for others
    if is_new_user:
        await cl.Message(
            content="""## 📝 Sharing with Colleagues?

Tell them to register using this format in the **Username** field:
```
their_username|email@example.com|Full Name|Institution Name
```
And their desired password in the **Password** field.

Example:
- Username: `john_doe|john@med.edu|John Doe|Stanford Medical`
- Password: `securepass123`
""",
            author="Info"
        ).send()
    
    # Check RAG connection
    if not rag_client.check_connection():
        await cl.Message(
            content="⚠️ **Warning:** RAG server not connected. Responses may be less authentic.",
            author="System"
        ).send()
    
    # Show student stats
    progress_data = db.get_progress_data(student_id)
    
    stats_msg = f"""## Your Stats

**Total Sessions:** {progress_data['total_sessions']}  
**Average Total Score:** {progress_data['avg_overall_score']:.1f}%  

---
"""
    
    await cl.Message(content=stats_msg, author="Stats").send()
    
    # Generate new patient
    await cl.Message(
        content="Generating a patient for you to interview...",
        author="System"
    ).send()
    
    patient = patient_gen.generate_patient()
    llm = LLMHandler()
    evaluator = ConversationEvaluator()
    
    # Create session in database
    session_id = db.create_session(student_id, patient)
    
    # Store in session
    cl.user_session.set("student_id", student_id)
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("patient", patient)
    cl.user_session.set("llm", llm)
    cl.user_session.set("evaluator", evaluator)
    cl.user_session.set("exchange_number", 0)
    cl.user_session.set("session_start", datetime.now())
    
    # Display patient info
    patient_info = f"""## Current Patient
    
**Name:** {patient['name']}  
**Age:** {patient['age']}  
**Gender:** {patient['gender'].capitalize()}  

**Background:**  
{patient['backstory']}

---

**Depression Severity:** {patient['severity']}  
**PHQ-9 Score:** {patient['phq9_score']}/27

---

### 📋 Your Task

Conduct a thorough clinical interview to assess this patient's mental health.

**Remember to:**
- Show empathy and build rapport
- Cover key depression symptoms
"""
    
    await cl.Message(content=patient_info, author="Patient Info").send()
    
    # Patient greeting
    greeting = f"Hello doctor... I'm {patient['name']}. Thanks for seeing me today."
    await cl.Message(content=greeting, author=patient['name']).send()
    
    # Action buttons
    actions = [
        cl.Action(
            name="end_session",
            value="end",
            payload={"action": "end_session"},
            label="📊 End Session & Evaluate"
        ),
        cl.Action(
            name="view_progress",
            value="progress",
            payload={"action": "view_progress"},
            label="📈 View My Progress"
        ),
        cl.Action(
            name="new_patient", 
            value="new",
            payload={"action": "new_patient"},
            label="👤 New Patient"
        )
    ]
    
    await cl.Message(
        content="**Ready!** Start your interview below, or use the buttons above.",
        actions=actions,
        author="System"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    """Handle all incoming messages"""
    
    # Don't process messages if we're in assessment mode (using buttons)
    if cl.user_session.get("awaiting_assessment"):
        return
    
    # Normal conversation
    patient = cl.user_session.get("patient")
    llm = cl.user_session.get("llm")
    evaluator = cl.user_session.get("evaluator")
    session_id = cl.user_session.get("session_id")
    exchange_number = cl.user_session.get("exchange_number", 0)
    
    if not patient or not llm or not evaluator:
        await cl.Message(
            content="❌ Session error. Please refresh.",
            author="System"
        ).send()
        return
    
    # Increment exchange number
    exchange_number += 1
    cl.user_session.set("exchange_number", exchange_number)
    
    # Get RAG context
    rag_context = rag_client.get_context_for_question(
        trainee_question=message.content,
        patient_profile=patient
    )
    
    # Generate response
    response = llm.generate_response(
        trainee_message=message.content,
        patient_profile=patient,
        rag_context=rag_context
    )
    
    # Log to evaluator
    evaluator.log_exchange(message.content, response)
    
    # Log to database
    db.log_conversation_exchange(
        session_id,
        exchange_number,
        message.content,
        response
    )
    
    # Send response with action buttons
    actions = [
        cl.Action(
            name="end_session",
            value="end",
            payload={"action": "end_session"},
            label="📊 End & Evaluate"
        ),
        cl.Action(
            name="view_progress",
            value="progress",
            payload={"action": "view_progress"},
            label="📈 View Progress"
        )
    ]
    
    await cl.Message(
        content=response,
        author=patient['name'],
        actions=actions
    ).send()

@cl.action_callback("end_session")
async def end_session(action: cl.Action):
    """Handle end session and evaluation"""
    
    evaluator = cl.user_session.get("evaluator")
    
    if not evaluator or len(evaluator.conversation_log) == 0:
        await cl.Message(
            content="❌ No conversation to evaluate.",
            author="System"
        ).send()
        return
    
    await cl.Message(
        content="""## 📋 Time for Your Assessment

Based on your interview, what is the patient's depression severity?

**Select the severity level:**""",
        author="System",
        actions=[
            cl.Action(
                name="assess_minimal",
                value="Minimal",
                payload={"severity": "Minimal", "min_score": 0, "max_score": 4},
                label="Minimal (0-4)"
            ),
            cl.Action(
                name="assess_mild",
                value="Mild",
                payload={"severity": "Mild", "min_score": 5, "max_score": 9},
                label="Mild (5-9)"
            ),
            cl.Action(
                name="assess_moderate",
                value="Moderate",
                payload={"severity": "Moderate", "min_score": 10, "max_score": 14},
                label="Moderate (10-14)"
            ),
            cl.Action(
                name="assess_moderately_severe",
                value="Moderately Severe",
                payload={"severity": "Moderately Severe", "min_score": 15, "max_score": 19},
                label="Moderately Severe (15-19)"
            ),
            cl.Action(
                name="assess_severe",
                value="Severe",
                payload={"severity": "Severe", "min_score": 20, "max_score": 27},
                label="Severe (20-27)"
            )
        ]
    ).send()
    
    cl.user_session.set("awaiting_assessment", True)
    cl.user_session.set("assessment_step", "severity")
    await action.remove()

@cl.action_callback("assess_minimal")
@cl.action_callback("assess_mild")
@cl.action_callback("assess_moderate")
@cl.action_callback("assess_moderately_severe")
@cl.action_callback("assess_severe")
async def handle_severity_selection(action: cl.Action):
    """Handle severity selection and ask for PHQ-9 score"""
    
    severity = action.payload["severity"]
    min_score = action.payload["min_score"]
    max_score = action.payload["max_score"]
    
    # Store severity
    cl.user_session.set("selected_severity", severity)
    cl.user_session.set("severity_range", (min_score, max_score))
    
    await cl.Message(
        content=f"""✓ Selected: **{severity}** depression

Now, estimate the specific PHQ-9 score ({min_score}-{max_score}):""",
        author="System",
        actions=[
            cl.Action(
                name=f"score_{i}",
                value=str(i),
                payload={"score": i},
                label=f"Score: {i}"
            )
            for i in range(min_score, max_score + 1)
        ]
    ).send()
    
    cl.user_session.set("assessment_step", "score")
    await action.remove()

@cl.action_callback("score_0")
@cl.action_callback("score_1")
@cl.action_callback("score_2")
@cl.action_callback("score_3")
@cl.action_callback("score_4")
@cl.action_callback("score_5")
@cl.action_callback("score_6")
@cl.action_callback("score_7")
@cl.action_callback("score_8")
@cl.action_callback("score_9")
@cl.action_callback("score_10")
@cl.action_callback("score_11")
@cl.action_callback("score_12")
@cl.action_callback("score_13")
@cl.action_callback("score_14")
@cl.action_callback("score_15")
@cl.action_callback("score_16")
@cl.action_callback("score_17")
@cl.action_callback("score_18")
@cl.action_callback("score_19")
@cl.action_callback("score_20")
@cl.action_callback("score_21")
@cl.action_callback("score_22")
@cl.action_callback("score_23")
@cl.action_callback("score_24")
@cl.action_callback("score_25")
@cl.action_callback("score_26")
@cl.action_callback("score_27")
async def handle_score_selection(action: cl.Action):
    """Handle PHQ-9 score selection and generate evaluation"""
    
    score = action.payload["score"]
    severity = cl.user_session.get("selected_severity")
    
    patient = cl.user_session.get("patient")
    evaluator = cl.user_session.get("evaluator")
    session_id = cl.user_session.get("session_id")
    student_id = cl.user_session.get("student_id")
    
    # Store assessment
    evaluator.doctor_assessment = {
        'severity': severity,
        'score': score
    }
    
    await cl.Message(
        content=f"""✓ Assessment Complete

**Your Diagnosis:**
- Severity: {severity}
- PHQ-9 Score: {score}/27

⏳ Generating comprehensive evaluation... (15-20 seconds)""",
        author="System"
    ).send()
    
    await action.remove()
    
    try:
        # Generate evaluation
        phq9_eval = evaluator.evaluate_phq9_accuracy(
            patient['severity'],
            patient['phq9_score']
        )
        
        empathy_eval = evaluator.evaluate_empathy_with_llm()
        
        # Calculate overall
        if 'error' not in phq9_eval and 'error' not in empathy_eval:
            overall_score = (
                phq9_eval['diagnostic_accuracy'] * 0.5 +
                empathy_eval['overall_score'] * 0.5
            )
        else:
            overall_score = 0
        
        # Save to database
        evaluation = {
            'overall_score': overall_score,
            'phq9_evaluation': phq9_eval,
            'empathy_evaluation': empathy_eval,
            'patient_profile': patient,
            'conversation_length': len(evaluator.conversation_log)
        }
        
        db.save_evaluation(session_id, evaluation)
        
        # Format and display
        report = format_evaluation_report(overall_score, phq9_eval, empathy_eval, patient)
        
        await cl.Message(content=report, author="Evaluation").send()
        
        # Reset
        cl.user_session.set("awaiting_assessment", False)
        cl.user_session.set("assessment_step", None)
        
        # Show updated progress
        progress_data = db.get_progress_data(student_id)
        
        await cl.Message(
            content=f"""## 🎯 Updated Stats

**Total Sessions:** {progress_data['total_sessions']}  
**New Average Score:** {progress_data['avg_overall_score']:.1f}%

Great work! Ready for another patient?
""",
            actions=[
                cl.Action(
                    name="view_progress",
                    value="progress",
                    payload={"action": "view_progress"},
                    label="📈 View Progress Dashboard"
                ),
                cl.Action(
                    name="new_patient",
                    value="new",
                    payload={"action": "new_patient"},
                    label="👤 New Patient"
                )
            ],
            author="System"
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ Error generating evaluation: {str(e)}",
            author="System"
        ).send()

@cl.action_callback("view_progress")
async def view_progress(action: cl.Action):
    """Show student's progress dashboard"""
    
    student_id = cl.user_session.get("student_id")
    
    await cl.Message(
        content="📊 Generating your progress dashboard...",
        author="System"
    ).send()
    
    # Get progress data
    progress_data = db.get_progress_data(student_id)
    sessions = db.get_student_sessions(student_id, limit=5)
    
    # Summary text
    summary = f"""## 📈 Your Progress Summary

**Total Sessions:** {progress_data['total_sessions']}  
**Average Overall Score:** {progress_data['avg_overall_score']:.1f}%  
**Average Diagnostic Accuracy:** {progress_data['avg_diagnostic']:.1f}%  
**Average Empathy Score:** {progress_data['avg_empathy']:.1f}%  
**Total Conversations:** {progress_data['total_exchanges']} exchanges

---

### Recent Sessions:
"""
    
    for i, session in enumerate(sessions, 1):
        if session['overall_score']:
            summary += f"\n{i}. **{session['patient_name']}** ({session['patient_severity']}) - Score: {session['overall_score']:.1f}%"
        else:
            summary += f"\n{i}. **{session['patient_name']}** ({session['patient_severity']}) - Not evaluated"
    
    await cl.Message(content=summary, author="Progress").send()
    
    # Generate charts
    try:
        # Progress timeline
        timeline_fig = viz.create_progress_timeline(student_id)
        elements = [cl.Plotly(name="progress_timeline", figure=timeline_fig, display="inline")]
        
        # Skills radar
        radar_fig = viz.create_skills_radar(student_id)
        elements.append(cl.Plotly(name="skills_radar", figure=radar_fig, display="inline"))
        
        # Severity performance
        severity_fig = viz.create_severity_performance(student_id)
        elements.append(cl.Plotly(name="severity_performance", figure=severity_fig, display="inline"))
        
        await cl.Message(
            content="",
            elements=elements,
            author="Charts"
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ Error generating charts: {str(e)}",
            author="System"
        ).send()

@cl.action_callback("new_patient")
async def new_patient(action: cl.Action):
    """Start new patient interview"""
    
    student_id = cl.user_session.get("student_id")
    
    await cl.Message(
        content="Generating new patient...",
        author="System"
    ).send()
    
    patient = patient_gen.generate_patient()
    llm = LLMHandler()
    evaluator = ConversationEvaluator()
    
    # Create new session
    session_id = db.create_session(student_id, patient)
    
    # Update session
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("patient", patient)
    cl.user_session.set("llm", llm)
    cl.user_session.set("evaluator", evaluator)
    cl.user_session.set("awaiting_assessment", False)
    cl.user_session.set("exchange_number", 0)
    cl.user_session.set("session_start", datetime.now())
    
    # Display patient
    patient_info = f"""## New Patient

**Name:** {patient['name']}  
**Age:** {patient['age']}  
**Gender:** {patient['gender'].capitalize()}  

**Background:** {patient['backstory']}

---

**Severity:** {patient['severity']} | **PHQ-9:** {patient['phq9_score']}/27
"""
    
    await cl.Message(content=patient_info, author="System").send()
    
    greeting = f"Hi... I'm {patient['name']}. Thank you for seeing me."
    await cl.Message(content=greeting, author=patient['name']).send()
    
    await action.remove()

async def handle_assessment_input(message: cl.Message):
    """Process doctor's assessment and generate evaluation"""
    
    patient = cl.user_session.get("patient")
    evaluator = cl.user_session.get("evaluator")
    session_id = cl.user_session.get("session_id")
    student_id = cl.user_session.get("student_id")
    
    try:
        # Parse assessment
        lines = message.content.strip().split('\n')
        severity = None
        score = None
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('severity:'):
                severity = line.split(':', 1)[1].strip()
            elif 'score:' in line.lower():
                score_text = line.split(':', 1)[1].strip()
                score = int(''.join(filter(str.isdigit, score_text)))
        
        if not severity or score is None:
            await cl.Message(
                content="❌ Invalid format. Please try again.",
                author="System"
            ).send()
            return
        
        # Validate
        valid_severities = ["Minimal", "Mild", "Moderate", "Moderately Severe", "Severe"]
        severity_match = next((s for s in valid_severities if s.lower() == severity.lower()), None)
        
        if not severity_match or not (0 <= score <= 27):
            await cl.Message(
                content="❌ Invalid severity or score. Please try again.",
                author="System"
            ).send()
            return
        
        # Store assessment
        evaluator.doctor_assessment = {
            'severity': severity_match,
            'score': score
        }
        
        await cl.Message(
            content="⏳ Generating comprehensive evaluation... (15-20 seconds)",
            author="System"
        ).send()
        
        # Generate evaluation
        phq9_eval = evaluator.evaluate_phq9_accuracy(
            patient['severity'],
            patient['phq9_score']
        )
        
        empathy_eval = evaluator.evaluate_empathy_with_llm()
        
        # Calculate overall
        if 'error' not in phq9_eval and 'error' not in empathy_eval:
            overall_score = (
                phq9_eval['diagnostic_accuracy'] * 0.5 +
                empathy_eval['overall_score'] * 0.5
            )
        else:
            overall_score = 0
        
        # Save to database
        evaluation = {
            'overall_score': overall_score,
            'phq9_evaluation': phq9_eval,
            'empathy_evaluation': empathy_eval,
            'patient_profile': patient,
            'conversation_length': len(evaluator.conversation_log)
        }
        
        db.save_evaluation(session_id, evaluation)
        
        # Format and display
        report = format_evaluation_report(overall_score, phq9_eval, empathy_eval, patient)
        
        await cl.Message(content=report, author="Evaluation").send()
        
        # Reset
        cl.user_session.set("awaiting_assessment", False)
        
        # Show updated progress
        progress_data = db.get_progress_data(student_id)
        
        await cl.Message(
            content=f"""## 🎯 Updated Stats

**Total Sessions:** {progress_data['total_sessions']}  
**New Average Score:** {progress_data['avg_overall_score']:.1f}%

Great work! Ready for another patient?
""",
            actions=[
                cl.Action(
                    name="view_progress",
                    value="progress",
                    payload={"action": "view_progress"},
                    label="📈 View Progress Dashboard"
                ),
                cl.Action(
                    name="new_patient",
                    value="new",
                    payload={"action": "new_patient"},
                    label="👤 New Patient"
                )
            ],
            author="System"
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ Error: {str(e)}",
            author="System"
        ).send()

def format_evaluation_report(overall_score, phq9_eval, empathy_eval, patient):
    """Format evaluation as markdown"""
    
    report = f"""# 📊 Performance Evaluation

## Overall Score: {overall_score:.1f}/100

"""
    
    if overall_score >= 85:
        report += "### ⭐⭐⭐ OUTSTANDING\n\n"
    elif overall_score >= 75:
        report += "### ⭐⭐ VERY GOOD\n\n"
    elif overall_score >= 65:
        report += "### ⭐ GOOD\n\n"
    else:
        report += "### ○ NEEDS IMPROVEMENT\n\n"
    
    report += "---\n\n"
    
    # Diagnostic
    if 'error' not in phq9_eval:
        report += f"""## Part 1: Diagnostic Accuracy ({phq9_eval['diagnostic_accuracy']:.1f}%)

**Your Assessment:** {phq9_eval['doctor_assessment']['severity']} (Score: {phq9_eval['doctor_assessment']['score']})  
**Actual:** {phq9_eval['actual']['severity']} (Score: {phq9_eval['actual']['score']})

{phq9_eval['severity_feedback']}

---

"""
    
    # Empathy
    if 'error' not in empathy_eval:
        report += f"""## Part 2: Empathy & Communication ({empathy_eval['overall_score']:.1f}%)

**Understanding:** {empathy_eval.get('understanding', {}).get('score', 0):.0f}%  
**Communication:** {empathy_eval.get('communication', {}).get('score', 0):.0f}%  
**Intention to Help:** {empathy_eval.get('intention', {}).get('score', 0):.0f}%

"""
        if empathy_eval.get('strengths'):
            report += f"\n✨ **Strengths:** {empathy_eval['strengths']}\n"
        if empathy_eval.get('improvements'):
            report += f"\n📚 **Improve:** {empathy_eval['improvements']}\n"
    
    return report