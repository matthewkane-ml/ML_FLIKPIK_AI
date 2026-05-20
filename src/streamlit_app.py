"""
Entry point for Render deployment.
Render's dashboard is configured to run: streamlit run src/streamlit_app.py
This file simply delegates to the actual app at app/app.py.
"""
import os
import runpy

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "app.py"))
runpy.run_path(APP_PATH, run_name="__main__")
