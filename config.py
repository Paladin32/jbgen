# language: Python, file: config.py
# Reads from environment (Railway) with local fallback

import os

TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")
PREFIX = os.environ.get("PREFIX", "%")
