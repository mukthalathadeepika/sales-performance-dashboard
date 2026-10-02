"""
app.py — Root entry point.
Delegates to frontend/app.py.
Run: streamlit run app.py
"""
import sys
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import and run the frontend app
from frontend.app import main
main()
