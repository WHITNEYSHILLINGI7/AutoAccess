#!/usr/bin/env python3
"""
AutoAccess Production Runner

This script starts both the Flask web application and Streamlit dashboard
for production deployment.

Usage:
    python run_production.py

Environment:
    - Set environment variables in .env file
    - Ensure all dependencies are installed: pip install -r requirements.txt
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path('.env')
    if env_file.exists():
        print("Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("Environment variables loaded.")
    else:
        print("No .env file found. Using system environment variables.")

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        import streamlit
        import pandas
        import sqlalchemy
        print("✓ All dependencies are installed.")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def start_flask_app():
    """Start the Flask web application."""
    print("Starting Flask web application on http://localhost:5000...")
    try:
        # Import here to ensure environment is loaded
        from app import create_app
        app = create_app()
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        sys.exit(1)

def start_streamlit_dashboard():
    """Start the Streamlit dashboard."""
    print("Starting Streamlit dashboard on http://localhost:8501...")
    try:
        # Use subprocess to run Streamlit in background
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 'dashboard.py',
            '--server.port', '8501',
            '--server.headless', 'true',
            '--server.address', '0.0.0.0'
        ]
        subprocess.Popen(cmd, cwd=str(Path(__file__).parent))
        print("✓ Streamlit dashboard started.")
    except Exception as e:
        print(f"Failed to start Streamlit dashboard: {e}")

def main():
    """Main production runner."""
    print("🚀 AutoAccess Production Deployment")
    print("=" * 40)

    # Load environment
    load_env_file()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Start services
    try:
        # Start Streamlit dashboard first (non-blocking)
        start_streamlit_dashboard()

        # Give Streamlit time to start
        time.sleep(3)

        # Start Flask app (blocking)
        start_flask_app()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down AutoAccess...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
