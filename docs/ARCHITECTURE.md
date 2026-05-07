# Architecture

A bird's-eye view of how the Medical Training Chatbot is wired together.

## Goals

- Let medical students rehearse PHQ-9 depression screening interviews
  against AI-simulated patients.
- Score each interview on **diagnostic accuracy** and **empathy**.
- Track per-student progress over time.

## High-Level Components

```
                     ┌────────────────────────┐
                     │      Browser (UI)      │
                     │     Chainlit React     │
                     └───────────┬────────────┘
                                 │ websocket
                     ┌───────────▼────────────┐
                     │        app.py          │
                     │  (Chainlit handlers)   │
                     └─┬────────┬────────┬────┘
                       │        │        │
              ┌────────▼─┐ ┌────▼────┐ ┌─▼──────────────┐
              │ patient_ │ │  llm_   │ │  rag_client    │
              │ generator│ │ handler │ │   (HTTP)       │
              └──────────┘ └────┬────┘ └─┬──────────────┘
                                │        │
                                ▼        ▼
                          Anthropic   External RAG
                            API         server
                                │
                  ┌─────────────┴─────────────┐
                  │                           │
            ┌─────▼──────┐            ┌───────▼──────┐
            │ evaluator  │            │   database   │
            │ (PHQ-9 +   │◄───────────┤  (SQLite,    │
            │  empathy)  │            │  4 tables)   │
            └────────────┘            └──────────────┘
                                              │
                                       ┌──────▼─────────┐
                                       │ visualizations │
                                       │   (Plotly)     │
                                       └────────────────┘
```

| Module                                 | Responsibility                                                    |
| -------------------------------------- | ----------------------------------------------------------------- |
| [`app.py`](../app.py)                  | Chainlit handlers, action callbacks, evaluation report formatting |
| [`patient_generator.py`](../patient_generator.py) | Random patient profiles per severity band              |
| [`llm_handler.py`](../llm_handler.py)  | Anthropic client + patient-simulation system prompt               |
| [`rag_client.py`](../rag_client.py)    | HTTP client for the external RAG server                           |
| [`evaluator.py`](../evaluator.py)      | PHQ-9 diagnostic scoring + LLM-judge empathy scoring              |
| [`database.py`](../database.py)        | SQLite layer (students, sessions, conversations, evaluations)     |
| [`visualizations.py`](../visualizations.py) | Plotly charts for the progress dashboard                     |

## Data Flow: One Interview Turn

1. Student types a message; Chainlit calls the `@cl.on_message` handler
   in [`app.py`](../app.py).
2. `RAGClient.get_context_for_question()` issues a `POST /search` to the
   external RAG server with the student's question and the patient
   severity. Failures are caught and produce empty context — the app
   keeps working.
3. `LLMHandler.generate_response()` builds a system prompt with the
   patient profile + RAG context and calls the Anthropic Messages API,
   maintaining `conversation_history` in memory for the session.
4. The patient reply is logged via
   `ConversationEvaluator.log_exchange()` and persisted via
   `StudentDatabase.log_conversation_exchange()`.
5. Chainlit renders the reply with action buttons (End, History,
   Progress).

## Data Flow: Evaluation

1. Student clicks **End Session & Evaluate**.
2. UI walks the student through a severity selector, then a PHQ-9 score
   selector (action buttons).
3. `ConversationEvaluator.evaluate_phq9_accuracy()` scores diagnostic
   accuracy by comparing the student's assessment to the simulated
   patient's actual values.
4. `ConversationEvaluator.evaluate_empathy_with_llm()` calls Claude as
   a judge over the full conversation log, returning sub-scores for
   understanding, communication, and intention to help.
5. The combined evaluation is written to the `evaluations` table.

## Database Schema

SQLite, file: `student_progress.db` (created on first run).

```sql
students(
  student_id INTEGER PRIMARY KEY,
  username TEXT UNIQUE,
  email TEXT UNIQUE,
  password_hash TEXT,           -- sha256 (see security note)
  full_name TEXT,
  institution TEXT,
  created_at TIMESTAMP,
  last_login TIMESTAMP
)

sessions(
  session_id INTEGER PRIMARY KEY,
  student_id INTEGER REFERENCES students,
  patient_name TEXT,
  patient_severity TEXT,
  patient_phq9_score INTEGER,
  session_date TIMESTAMP,
  conversation_length INTEGER,
  duration_minutes INTEGER
)

conversation_logs(
  log_id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions,
  exchange_number INTEGER,
  doctor_message TEXT,
  patient_response TEXT,
  timestamp TIMESTAMP
)

evaluations(
  evaluation_id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions,
  overall_score REAL,
  diagnostic_accuracy REAL,
  empathy_score REAL,
  understanding_score REAL,
  communication_score REAL,
  intention_score REAL,
  doctor_severity_assessment TEXT,
  doctor_phq9_assessment INTEGER,
  severity_correct BOOLEAN,
  evaluation_data TEXT             -- full JSON blob
)
```

The "evaluated session" filter — used for stats and the progress
dashboard — is `sessions INNER JOIN evaluations`.

## Configuration

- `.env` supplies secrets and the RAG URL.
- [`config.py`](../config.py) exposes constants:
  `CLAUDE_MODEL`, `MAX_TOKENS`, `TEMPERATURE`, `RAG_LIMIT`,
  `MIN_RELEVANCE_SCORE`.
- [`.chainlit/config.toml`](../.chainlit/config.toml) controls UI
  features, theme, and CSS/JS hooks.

## Decisions / Trade-offs

- **Chainlit over a custom React frontend** — fastest path to a working
  authenticated chat UI with action buttons and Plotly embedding. The
  trade-off is limited layout flexibility; see
  [`UI_GUIDE.md`](UI_GUIDE.md) for what's actually customizable.
- **SQLite over Postgres** — single-file, zero-deploy, fits a per-class
  cohort. Move to Postgres if multi-instance or concurrent-write
  requirements appear.
- **External RAG server** — the chatbot depends on a separately deployed
  retrieval service rather than embedding documents in-process. Local
  development works without it (graceful warning banner).
- **Claude as both actor and judge** — the same model simulates the
  patient and grades empathy. This is convenient but introduces a known
  bias; document any change of judge model in the evaluator if you swap
  it.

## Known Issues / Improvement Areas

- Password hashing is plain SHA-256 with no salt
  ([`database.py:100`](../database.py:100)). Replace with `bcrypt`,
  `argon2`, or `passlib` before any non-classroom deployment.
- Registration is bolted onto the login form via a pipe-delimited
  username string ([`app.py:27`](../app.py:27)) — works, but UX is
  rough.
- `app.py` is ~1200 lines; the message handler is now a single normal
  branch (history/analyze became button callbacks), but the file would
  still benefit from being split by concern (auth, interview loop,
  evaluation, history/analyze).
