import os

from dotenv import load_dotenv
from groq import Groq
from functools import cache

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


@cache
def get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)
