from dotenv import load_dotenv
import os

load_dotenv()


# -- PyRIT Attacker LLM --
PYRIT_ATTACKER_ENDPOINT =os.getenv("PYRIT_ATTACKER_ENDPOINT","")
PYRIT_ATTACKER_MODEL= os.getenv("PYRIT_ATTACKER_MODEL","")
PYRIT_ATTACKER_API_KEY= os.getenv("PYRIT_ATTACKER_API_KEY","")

# -- PyRIT Scorer LLM --
PYRIT_SCORER_ENDPOINT= os.getenv("PYRIT_SCORER_ENDPOINT","")
PYRIT_SCORER_MODEL= os.getenv("PYRIT_SCORER_MODEL","")
PYRIT_SCORER_API_KEY= os.getenv("PYRIT_SCORER_API_KEY","")

# -- PyRIT Runtime --
PYRIT_DB_PATH= os.getenv("PYRIT_DB_PATH","")

# -- Target --
DEFAULT_TARGET_URL= os.getenv("DEFAULT_TARGET_URL","")

# -- Reports --
JSON_REPORTS_DIR= os.getenv("JSON_REPORTS_DIR","")

# -- Garak --
GARAK_REPORTS_DIR= os.getenv("GARAK_REPORTS_DIR","")
GARAK_CONFIG_PATH= os.getenv("GARAK_CONFIG_PATH","")