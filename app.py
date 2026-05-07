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


def get_phq9_briefing() -> str:
    """Returns PHQ-9 educational briefing shown before each patient interview"""
    return """## 📋 PHQ-9 Clinical Reference Guide

The **Patient Health Questionnaire-9 (PHQ-9)** is a 9-item self-report tool used to screen for and measure the severity of depression. Each item asks how often the patient has been bothered by a specific symptom **over the last 2 weeks**.

---

### 🔢 The 9 Questions

Each question is scored: **0** = Not at all · **1** = Several days · **2** = More than half the days · **3** = Nearly every day

| # | Symptom Domain | What to Listen For |
|---|---------------|-------------------|
| 1 | **Anhedonia** | Loss of interest or pleasure in activities they used to enjoy |
| 2 | **Depressed Mood** | Feeling down, hopeless, or empty most of the time |
| 3 | **Sleep Disturbance** | Trouble falling/staying asleep, or sleeping too much |
| 4 | **Fatigue** | Low energy, feeling tired even without much activity |
| 5 | **Appetite Changes** | Eating much less or more than usual, weight changes |
| 6 | **Guilt / Worthlessness** | Feeling like a failure, letting people down, self-blame |
| 7 | **Concentration** | Difficulty focusing, reading, making decisions |
| 8 | **Psychomotor Changes** | Moving/speaking slowly, or being noticeably restless/fidgety |
| 9 | **Suicidal Ideation** | Thoughts of being better off dead, or of self-harm |

---

### 📊 Severity Bands

| Score | Severity | Recommended Action |
|-------|----------|--------------------|
| 0 – 4 | **Minimal** | Monitor, may not require treatment |
| 5 – 9 | **Mild** | Watchful waiting, consider counselling |
| 10 – 14 | **Moderate** | Consider counselling and/or medication |
| 15 – 19 | **Moderately Severe** | Active treatment with medication and/or therapy |
| 20 – 27 | **Severe** | Immediate treatment, consider specialist referral |

---

### 💡 Interview Tips

- **Start open-ended** — let the patient describe their experience before asking targeted questions
- **Cover all 9 domains** — patients may not volunteer information unless asked
- **Ask about duration** — symptoms must be present for at least 2 weeks to count
- **Always assess Question 9** — never skip suicidal ideation, even if the patient seems mild
- **Show empathy** — acknowledge what the patient shares before moving to the next question

---

*Your goal is to gather enough information to estimate the patient's PHQ-9 score and severity level.*
"""

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
    
    stats_msg = f"""## 📊 Your Progress

**Total Sessions:** {progress_data['total_sessions']}  
**Average Score:** {progress_data['avg_overall_score']:.1f}%  
**Total Conversations:** {progress_data['total_exchanges']} exchanges

---
"""
    
    await cl.Message(content=stats_msg, author="Stats").send()
    
    # Show PHQ-9 briefing before patient is generated
    await cl.Message(
        content=get_phq9_briefing(),
        author="PHQ-9 Guide"
    ).send()

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



### 📋 Your Task

Conduct a thorough clinical interview to assess this patient's mental health.

**Remember to:**
- Show empathy and build rapport
- Ask open-ended questions
- Assess suicide risk
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
            name="session_history",
            value="history",
            payload={"action": "session_history"},
            label="📚 Session History"
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
    
    # Check if in analyze mode
    if cl.user_session.get("analyze_mode"):
        try:
            exchange_num = int(message.content.strip())
            exchanges = cl.user_session.get("current_session_exchanges", [])
            patient_info = cl.user_session.get("current_session_patient", {})
            
            if exchange_num < 1 or exchange_num > len(exchanges):
                await cl.Message(
                    content=f"Invalid exchange number. Please enter a number between 1 and {len(exchanges)}.",
                    author="System"
                ).send()
                return
            
            # Get the specific exchange
            exchange = exchanges[exchange_num - 1]
            
            await cl.Message(
                content=f"🔍 Analyzing Exchange {exchange_num}... (this may take 10-15 seconds)",
                author="System"
            ).send()
            
            # Use LLM to analyze the exchange
            from llm_handler import LLMHandler
            analyzer = LLMHandler()
            
            analysis_prompt = f"""You are an expert clinical supervisor evaluating a medical student's interview technique.

**Patient Context:**
- Name: {patient_info.get('name', 'Unknown')}
- Depression Severity: {patient_info.get('severity', 'Unknown')}
- PHQ-9 Score: {patient_info.get('phq9_score', 'Unknown')}/27

**Exchange to Analyze:**

Doctor's Question: "{exchange['doctor']}"

Patient's Response: "{exchange['patient']}"

---

Provide a comprehensive analysis of this exchange. Structure your feedback as follows:

**✅ STRENGTHS (What the doctor did well):**
[List 2-3 specific positive aspects]

**⚠️ AREAS FOR IMPROVEMENT:**
[List 2-3 specific areas that could be better]

**💡 ALTERNATIVE APPROACHES:**
[Suggest 1-2 alternative ways to phrase the question or approach the topic]

**🎯 CLINICAL BEST PRACTICES:**
[Brief note on relevant clinical interviewing principles]

Be specific, constructive, and educational. Focus on empathy, open-ended questioning, and rapport building."""

            analysis = analyzer.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            analysis_text = analysis.content[0].text
            
            # Display analysis
            await cl.Message(
                content=f"""## 🔍 Analysis: Exchange {exchange_num}

**Doctor:** {exchange['doctor']}

**Patient:** {exchange['patient']}

---

{analysis_text}
""",
                author="Analysis"
            ).send()
            
            # Exit analyze mode
            cl.user_session.set("analyze_mode", False)
            
            # Offer to analyze another or exit
            await cl.Message(
                content="",
                actions=[
                    cl.Action(
                        name="analyze_mode",
                        value="analyze",
                        payload={"action": "analyze"},
                        label="🔍 Analyze Another Exchange"
                    ),
                    cl.Action(
                        name="session_history",
                        value="history",
                        payload={"action": "session_history"},
                        label="📚 Session History"
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
            
            return
            
        except ValueError:
            cl.user_session.set("analyze_mode", False)
        except Exception as e:
            await cl.Message(
                content=f"Error analyzing exchange: {str(e)}",
                author="System"
            ).send()
            cl.user_session.set("analyze_mode", False)
            return
    
    # Check if in history mode (viewing past sessions)
    if cl.user_session.get("history_mode"):
        try:
            display_number = int(message.content.strip())
            session_mapping = cl.user_session.get("session_mapping", {})
            
            if display_number not in session_mapping:
                await cl.Message(
                    content=f"Invalid session number. Please enter a number between 1 and {len(session_mapping)}.",
                    author="System"
                ).send()
                return
            
            # Get the actual session_id from the mapping
            session_id = session_mapping[display_number]
            
            # Get session details
            session = db.get_session_details(session_id)
            
            if not session:
                await cl.Message(
                    content="❌ Session not found.",
                    author="System"
                ).send()
                return
            
            # Format session details
            details = f"""## 📋 Session {session_id} Details

**Patient:** {session['patient_name']}  
**Severity:** {session['patient_severity']} (PHQ-9: {session['patient_phq9_score']})  
**Date:** {session['session_date']}  
**Exchanges:** {session['conversation_length']} turns

---

### 💬 Conversation Transcript

"""
            
            # Add conversation with exchange numbers
            for idx, exchange in enumerate(session['conversation'], 1):
                details += f"""**Exchange {idx}**

🩺 **Doctor:** {exchange['doctor']}

👤 **Patient ({session['patient_name']}):** {exchange['patient']}

---

"""
            
            # Store exchanges for analysis
            cl.user_session.set("current_session_exchanges", session['conversation'])
            cl.user_session.set("current_session_patient", {
                'name': session['patient_name'],
                'severity': session['patient_severity'],
                'phq9_score': session['patient_phq9_score']
            })
            
            # Add evaluation summary
            if session.get('evaluation'):
                eval_data = session['evaluation']
                phq9 = eval_data.get('phq9_evaluation', {})
                empathy = eval_data.get('empathy_evaluation', {})
                
                details += f"""### 📊 Your Performance

**Overall Score:** {eval_data.get('overall_score', 0):.1f}%

**Diagnostic Accuracy:** {phq9.get('diagnostic_accuracy', 0):.1f}%
- Your Assessment: {phq9.get('doctor_assessment', {}).get('severity', 'N/A')} (Score: {phq9.get('doctor_assessment', {}).get('score', 'N/A')})
- Actual: {eval_data.get('patient_profile', {}).get('severity', 'N/A')} (Score: {eval_data.get('patient_profile', {}).get('phq9_score', 'N/A')})

**Empathy Score:** {empathy.get('overall_score', 0):.1f}%
- Understanding: {empathy.get('understanding', {}).get('score', 0):.0f}%
- Communication: {empathy.get('communication', {}).get('score', 0):.0f}%
- Intention to Help: {empathy.get('intention', {}).get('score', 0):.0f}%
"""
            
            await cl.Message(
                content=details,
                author="Session Details"
            ).send()
            
            # Exit history mode
            cl.user_session.set("history_mode", False)
            
            # Add action buttons including analyze option
            await cl.Message(
                content="💡 **Want feedback on a specific exchange?** Type the exchange number to get AI analysis (e.g., type `1` for Exchange 1).",
                actions=[
                    cl.Action(
                        name="analyze_mode",
                        value="analyze",
                        payload={"action": "analyze"},
                        label="🔍 Analyze an Exchange"
                    ),
                    cl.Action(
                        name="session_history",
                        value="history",
                        payload={"action": "session_history"},
                        label="📚 View Another Session"
                    ),
                    cl.Action(
                        name="view_progress",
                        value="progress",
                        payload={"action": "view_progress"},
                        label="📈 View Progress"
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
            
            return
            
        except ValueError:
            # Not a valid number, treat as normal conversation
            cl.user_session.set("history_mode", False)
    
    # Normal conversation
    patient = cl.user_session.get("patient")
    llm = cl.user_session.get("llm")
    evaluator = cl.user_session.get("evaluator")
    session_id = cl.user_session.get("session_id")
    exchange_number = cl.user_session.get("exchange_number", 0)
    
    if not patient or not llm or not evaluator:
        await cl.Message(
            content="Session error. Please refresh.",
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
            name="session_history",
            value="history",
            payload={"action": "session_history"},
            label="📚 History"
        ),
        cl.Action(
            name="view_progress",
            value="progress",
            payload={"action": "view_progress"},
            label="📈 Progress"
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

@cl.action_callback("session_history")
async def session_history(action: cl.Action):
    """Show student's session history"""
    
    student_id = cl.user_session.get("student_id")
    
    await cl.Message(
        content="📚 Loading your session history...",
        author="System"
    ).send()
    
    # Get all evaluated sessions
    sessions = db.get_student_sessions(student_id, limit=20)
    
    if not sessions:
        await cl.Message(
            content="No completed sessions yet. Complete an interview and evaluation to see it here!",
            author="System"
        ).send()
        return
    
    # Create a mapping of display number to session_id
    session_mapping = {}
    for i, session in enumerate(sessions, 1):
        session_mapping[i] = session['session_id']
    
    # Store mapping in user session
    cl.user_session.set("session_mapping", session_mapping)
    
    # Format session list
    history_text = f"""## 📚 Your Session History

**Total Evaluated Sessions:** {len(sessions)}

---

"""
    
    for i, session in enumerate(sessions, 1):
        date = session['session_date'].split()[0] if session['session_date'] else 'Unknown'
        
        history_text += f"""**{i}.** {session['patient_name']} ({date})
- Severity: {session['patient_severity']} | Your Score: {session['overall_score']:.1f}%
- Diagnostic: {session['diagnostic_accuracy']:.1f}% | Empathy: {session['empathy_score']:.1f}%

"""
    
    await cl.Message(
        content=history_text,
        author="History"
    ).send()
    
    # Instruct user to send session number
    await cl.Message(
        content="💡 **To view a session:** Type the session number (e.g., `1`, `2`, `3`) to see the full conversation.",
        author="System"
    ).send()
    
    # Set a flag that we're in history mode
    cl.user_session.set("history_mode", True)

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
        
        # Add action buttons
        await cl.Message(
            content="",
            actions=[
                cl.Action(
                    name="session_history",
                    value="history",
                    payload={"action": "session_history"},
                    label="📚 Session History"
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
            content=f"❌ Error generating charts: {str(e)}",
            author="System"
        ).send()

@cl.action_callback("analyze_mode")
async def analyze_mode(action: cl.Action):
    """Enable exchange analysis mode"""
    
    exchanges = cl.user_session.get("current_session_exchanges", [])
    
    if not exchanges:
        await cl.Message(
            content="❌ No exchanges available to analyze. Please view a session first.",
            author="System"
        ).send()
        return
    
    # Create buttons for each exchange (limit to 10 for UI)
    exchange_actions = []
    for i in range(min(len(exchanges), 10)):
        exchange_actions.append(
            cl.Action(
                name=f"analyze_exchange",
                value=str(i + 1),
                payload={"exchange_num": i + 1},
                label=f"Exchange {i + 1}"
            )
        )
    
    message = f"""## 🔍 Exchange Analysis

**Available exchanges:** {len(exchanges)} total

Select an exchange to analyze:
"""
    
    if len(exchanges) > 10:
        message += f"\n💡 *Showing first 10 exchanges. Type a number (1-{len(exchanges)}) for others.*"
    
    await cl.Message(
        content=message,
        actions=exchange_actions,
        author="System"
    ).send()
    
    # Also enable typing for exchanges beyond 10
    if len(exchanges) > 10:
        cl.user_session.set("analyze_mode", True)
    
    await action.remove()

@cl.action_callback("analyze_exchange")
async def analyze_exchange(action: cl.Action):
    """Analyze a specific exchange from button click"""
    
    exchange_num = action.payload["exchange_num"]
    exchanges = cl.user_session.get("current_session_exchanges", [])
    patient_info = cl.user_session.get("current_session_patient", {})
    
    if exchange_num < 1 or exchange_num > len(exchanges):
        await cl.Message(
            content=f"❌ Invalid exchange number.",
            author="System"
        ).send()
        return
    
    # Get the specific exchange
    exchange = exchanges[exchange_num - 1]
    
    await cl.Message(
        content=f"🔍 Analyzing Exchange {exchange_num}... (this may take 10-15 seconds)",
        author="System"
    ).send()
    
    # Use LLM to analyze the exchange
    from llm_handler import LLMHandler
    analyzer = LLMHandler()
    
    analysis_prompt = f"""You are an expert clinical supervisor evaluating a medical student's interview technique.

**Patient Context:**
- Name: {patient_info.get('name', 'Unknown')}
- Depression Severity: {patient_info.get('severity', 'Unknown')}
- PHQ-9 Score: {patient_info.get('phq9_score', 'Unknown')}/27

**Exchange to Analyze:**

Doctor's Question: "{exchange['doctor']}"

Patient's Response: "{exchange['patient']}"

---

Provide a comprehensive analysis of this exchange. Structure your feedback as follows:

**✅ STRENGTHS (What the doctor did well):**
[List 2-3 specific positive aspects]

**⚠️ AREAS FOR IMPROVEMENT:**
[List 2-3 specific areas that could be better]

**💡 ALTERNATIVE APPROACHES:**
[Suggest 1-2 alternative ways to phrase the question or approach the topic]

**🎯 CLINICAL BEST PRACTICES:**
[Brief note on relevant clinical interviewing principles]

Be specific, constructive, and educational. Focus on empathy, open-ended questioning, and rapport building."""

    analysis = analyzer.client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        temperature=0.3,
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    
    analysis_text = analysis.content[0].text
    
    # Display analysis
    await cl.Message(
        content=f"""## 🔍 Analysis: Exchange {exchange_num}

**Doctor:** {exchange['doctor']}

**Patient:** {exchange['patient']}

---

{analysis_text}
""",
        author="Analysis"
    ).send()
    
    # Offer to analyze another or exit
    await cl.Message(
        content="",
        actions=[
            cl.Action(
                name="analyze_mode",
                value="analyze",
                payload={"action": "analyze"},
                label="🔍 Analyze Another Exchange"
            ),
            cl.Action(
                name="session_history",
                value="history",
                payload={"action": "session_history"},
                label="📚 Session History"
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
    
    await action.remove()

@cl.action_callback("new_patient")
async def new_patient(action: cl.Action):
    """Start new patient interview"""
    
    student_id = cl.user_session.get("student_id")
    current_session_id = cl.user_session.get("session_id")
    evaluator = cl.user_session.get("evaluator")
    
    # Check if current session has conversation but no evaluation
    if evaluator and len(evaluator.conversation_log) > 0:
        # Check if this session was evaluated
        import sqlite3
        conn = sqlite3.connect('student_progress.db')
        cursor = conn.cursor()
        cursor.execute("SELECT evaluation_id FROM evaluations WHERE session_id = ?", (current_session_id,))
        has_evaluation = cursor.fetchone() is not None
        conn.close()
        
        if not has_evaluation:
            await cl.Message(
                content="""⚠️ **Current Session Not Evaluated**

You have an ongoing interview that hasn't been evaluated yet.

**Would you like to:**""",
                actions=[
                    cl.Action(
                        name="end_session",
                        value="end",
                        payload={"action": "end_session"},
                        label="📊 Evaluate Current Session First"
                    ),
                    cl.Action(
                        name="skip_and_new",
                        value="skip",
                        payload={"action": "skip_and_new"},
                        label="⏭️ Skip & Start New Patient"
                    )
                ],
                author="System"
            ).send()
            await action.remove()
            return
    
    await cl.Message(
        content="Generating new patient...",
        author="System"
    ).send()

    # Show PHQ-9 briefing before new patient
    await cl.Message(
        content=get_phq9_briefing(),
        author="PHQ-9 Guide"
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
    
    # Send greeting with action buttons
    await cl.Message(
        content=greeting,
        author=patient['name'],
        actions=[
            cl.Action(
                name="end_session",
                value="end",
                payload={"action": "end_session"},
                label="📊 End & Evaluate"
            ),
            cl.Action(
                name="session_history",
                value="history",
                payload={"action": "session_history"},
                label="📚 History"
            ),
            cl.Action(
                name="view_progress",
                value="progress",
                payload={"action": "view_progress"},
                label="📈 Progress"
            )
        ]
    ).send()
    
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