from pathlib import Path
from dotenv import load_dotenv
import os

_ROOT = Path(__file__).parent
load_dotenv(dotenv_path=_ROOT / '.env')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
GEMINI_API_URL = os.getenv('GEMINI_API_URL')
# Default model to use with Google Generative Language API when only API key is present
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'models/text-bison-001')
