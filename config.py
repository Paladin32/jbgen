# language: Python, file: config.py
# Environment-driven config (Railway / local)

import os

TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")
PREFIX = os.environ.get("PREFIX", "%")

# Groq (OpenAI-compatible)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
