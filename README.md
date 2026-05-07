# Medical Training Chatbot

A clinical-interviewing trainer for medical students. Students practice
PHQ-9 depression assessments against AI-simulated patients, get scored on
diagnostic accuracy and empathy, and track their progress over time.

Built with [Chainlit](https://chainlit.io) and the Anthropic Claude API.

> **Status — teaching prototype (final-year project).** Authentication uses
> unsalted SHA-256, the database is a single SQLite file, and conversation
> logs are stored verbatim. Fine for classroom use; **not** production-grade.
> See [ARCHITECTURE > Known Issues](docs/ARCHITECTURE.md#known-issues--improvement-areas)
> before deploying outside a course.

---

## Requirements

- **Python 3.10 – 3.13.** Python 3.14 is *not* supported — the
  `anyio`/`starlette` stack used by Chainlit 2.11 trips a
  `NoEventLoopError` when serving static assets, leaving the page
  blank. Use 3.13 (`brew install python@3.13` on macOS) until that's
  resolved upstream.
- An [Anthropic API key](https://console.anthropic.com/).
- (Optional) A reachable RAG server. The app degrades gracefully when
  it isn't.

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/RMM108/medical-chatbot.git
cd medical-chatbot

# 2. Create a virtual environment and install dependencies
#    Use Python 3.10–3.13. Python 3.14 is currently broken (see note below).
python3.13 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
chainlit create-secret            # paste the output into CHAINLIT_AUTH_SECRET
# add your ANTHROPIC_API_KEY to .env

# 4. (Optional) Seed a demo account with sample sessions
python create_demo_data.py

# 5. Run
chainlit run app.py -w
```

Then open <http://localhost:8000>. The `-w` flag enables auto-reload on
file changes.

### Default test accounts

| Username       | Password   | Notes                                  |
| -------------- | ---------- | -------------------------------------- |
| `test_student` | `test123`  | Created by `create_demo_data.py`, has 10 sample sessions for chart testing |
| `student1`     | `pass123`  | Created by `register_Students.py`      |

---

## Configuration

All runtime configuration is read from environment variables (loaded from
`.env` via `python-dotenv`). See [`.env.example`](.env.example) for the
full list.

| Variable               | Required | Purpose                                            |
| ---------------------- | -------- | -------------------------------------------------- |
| `ANTHROPIC_API_KEY`    | yes      | Patient simulation + LLM-based evaluation          |
| `CHAINLIT_AUTH_SECRET` | yes      | Required by Chainlit's password auth flow          |
| `SERVER_URL`           | no       | RAG server URL. Defaults to `http://localhost:8000`. The app shows a warning banner and falls back to no-RAG context when unreachable. |

Model selection, token limits, and RAG thresholds live in
[`config.py`](config.py).

UI theming and Chainlit feature flags live in
[`.chainlit/config.toml`](.chainlit/config.toml).

---

## Project Layout

| File                       | Role                                                            |
| -------------------------- | --------------------------------------------------------------- |
| [`app.py`](app.py)         | Chainlit entry point — auth, chat flow, action buttons, evaluation reports |
| [`patient_generator.py`](patient_generator.py) | Generates randomized patient profiles per severity     |
| [`llm_handler.py`](llm_handler.py)             | Wraps the Anthropic client; builds the patient-simulation system prompt |
| [`rag_client.py`](rag_client.py)               | HTTP client for the external RAG server                |
| [`evaluator.py`](evaluator.py)                 | PHQ-9 diagnostic scoring + LLM-judge empathy scoring   |
| [`database.py`](database.py)                   | SQLite layer (students, sessions, conversations, evaluations) |
| [`visualizations.py`](visualizations.py)       | Plotly charts for the progress dashboard               |
| [`config.py`](config.py)                       | Loads env vars, model + RAG constants                  |
| [`chainlit.md`](chainlit.md)                   | Login-screen welcome copy                              |
| `.chainlit/config.toml`    | Chainlit UI/feature configuration                                |
| `student_progress.db`      | SQLite database (created on first run)                          |

Helper scripts:

- [`create_demo_data.py`](create_demo_data.py) — seeds `test_student` with 10 sample sessions
- [`register_Students.py`](register_Students.py) — registers a single named student
- [`check_student_data.py`](check_student_data.py) — quick DB inspection
- [`rag_experiment.py`](rag_experiment.py) — offline experiment for tuning RAG thresholds (writes `rag_threshold_*.{json,csv}` artifacts)

---

## How a Session Works

1. **Login** — Chainlit's password auth callback hits
   `db.authenticate_student()` ([`app.py:21`](app.py:21)).
   New users register by typing `username|email|name|institution` into
   the username field with their desired password.
2. **Briefing** — A PHQ-9 reference card is shown
   ([`app.py:73`](app.py:73)).
3. **Patient generated** — `PatientGenerator.generate_patient()` returns
   a randomized profile with a severity-band-aligned PHQ-9 score.
4. **Interview loop** — every student message goes through:
   `student → RAGClient.get_context_for_question() → LLMHandler.generate_response() → patient reply`.
   Each exchange is persisted to the `conversations` table.
5. **Evaluation** — clicking *End Session* prompts the student for their
   diagnosis (severity + score), then `ConversationEvaluator` runs
   diagnostic accuracy + LLM-judged empathy scoring.
6. **Progress dashboard** — Plotly charts in `visualizations.py` render
   the timeline, skills radar, and severity-performance breakdown.

---

## Development

### Common tasks

```bash
# Reset the database (⚠️ destroys all sessions)
rm student_progress.db

# Re-seed demo data
python create_demo_data.py

# Inspect the schema
sqlite3 student_progress.db '.schema'
```

### UI work without a live RAG server

`RAGClient.check_connection()` already returns `False` on any error and
the app shows a "RAG server not connected" banner — interviews still
work, they just lack retrieved context. No code changes are needed for
local UI development.

### Customizing the look

- **CSS** — uncomment `custom_css = "/public/test.css"` in
  `.chainlit/config.toml` and add the file under `public/`.
- **JS** — same idea with `custom_js`.
- **Theme** — `default_theme` in `.chainlit/config.toml`
  (`"dark"` or `"light"`).
- **Login welcome** — edit [`chainlit.md`](chainlit.md).

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — component breakdown,
  data flow, and database schema.
- [`docs/UI_GUIDE.md`](docs/UI_GUIDE.md) — Chainlit-specific notes for
  contributors working on the UI.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| ------- | ------------------ |
| Blank page after `chainlit run` | Running on Python 3.14 — downgrade to 3.10–3.13. |
| `chainlit: command not found` or `create-secret` not found | Activate the venv first: `source venv/bin/activate`. |
| "RAG server not connected" banner | Expected when `SERVER_URL` is unreachable. Interviews still work without retrieved context. |
| "Incorrect username or password" right after registering | The username field needs four `\|`-separated pieces (`username\|email\|name\|institution`). See [chainlit.md](chainlit.md). |
| Port 8000 already in use | Stop the other service or run `chainlit run app.py -w --port 8001`. |
| Want to reset everything | `rm student_progress.db` then re-run `python create_demo_data.py`. |

---

## License

Add a license here when ready.
