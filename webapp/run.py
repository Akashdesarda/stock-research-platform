import os
import subprocess
import sys

from app import setup
from stocksense.config import get_settings

if __name__ == "__main__":
    setup()
    settings = get_settings()
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(settings.app.port)
    try:
        result = subprocess.run(["streamlit", "run", "main.py"], env=env, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"Streamlit failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("Streamlit server interrupted by user.")
        sys.exit(0)
