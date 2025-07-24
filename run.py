# AIDEV-SECTION: Run script for Bio Agent
"""
Simple script to run both backend and frontend
"""
import subprocess
import sys
import time
import os

def main():
    print("🧬 Starting Bio Agent...")
    print("-" * 50)
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️  No .env file found. Creating from .env.example...")
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print("📝 Created .env file. Please edit it with your API keys!")
            print("   Especially set your AZURE_OPENAI_API_KEY")
            return
        else:
            print("❌ No .env.example found!")
            return
    
    # Start backend
    print("🚀 Starting backend API...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "src.orchestrator.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for backend to start
    time.sleep(3)
    
    # Start frontend
    print("🎨 Starting Streamlit frontend...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("-" * 50)
    print("✅ Bio Agent is running!")
    print("🌐 Backend API: http://localhost:8000")
    print("🖥️  Frontend: http://localhost:8501")
    print("-" * 50)
    print("Press Ctrl+C to stop")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend.terminate()
        frontend.terminate()
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()