

# API Keys
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
# Model settings
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Latest Sonnet
MAX_TOKENS = 1000
TEMPERATURE = 0.7

# RAG settings
RAG_LIMIT = 3  # Number of examples to retrieve
MIN_RELEVANCE_SCORE = 0.4  # Minimum similarity score