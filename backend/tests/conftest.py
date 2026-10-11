from pathlib import Path

from dotenv import load_dotenv


# Load the test target before application settings are instantiated by test imports.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")