"""
app.py
Root launcher for Sales Performance Dashboard.
Enables running 'streamlit run app.py' directly from the root workspace directory
or 'streamlit run frontend/app.py' as specified in the PRD.
"""

import sys
import runpy
from pathlib import Path

# Ensure root directory is on python path
ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Delegate to frontend/app.py
target_script = Path(__file__).parent / "frontend" / "app.py"
runpy.run_path(str(target_script), run_name="__main__")
