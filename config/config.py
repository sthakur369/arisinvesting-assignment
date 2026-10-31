import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Gets the project root directory by stepping up two levels (out of the config folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Load environment variables from the .env file in the project root
load_dotenv(BASE_DIR / ".env")

# 3. Safely join the paths to reach the data folder
DB_PATH = BASE_DIR / "database" / "aris_lite.db"

# 4. Read the loaded variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL")

# 10 exchanges = 20 messages (10 user + 10 assistant).
CONVERSATION_THRESHOLD = 20