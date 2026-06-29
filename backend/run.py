#!/usr/bin/env python
"""
Entry point for running the backend server.
This script ensures the correct event loop policy is set before uvicorn starts.

Usage:
    python run.py              # Development mode (reload disabled on Win+Python3.14+)
    python run.py --reload     # Force reload mode (Playwright will NOT work!)
    python run.py --no-reload  # Production mode without reload

NOTE: On Windows with Python 3.14+, uvicorn's --reload mode uses SelectorEventLoop
which does NOT support subprocess operations. This breaks Playwright.
Reload is automatically disabled on Windows + Python 3.14+ unless forced.
"""
import sys
import os

print(f"[run.py] Python {sys.version}")
print(f"[run.py] Platform: {sys.platform}")

# Check Python version
python_version = sys.version_info
is_windows = sys.platform == "win32"
is_python_314_plus = python_version >= (3, 14)

import uvicorn

if __name__ == "__main__":
    # Get configuration from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Determine reload mode
    force_reload = "--reload" in sys.argv
    force_no_reload = "--no-reload" in sys.argv or os.getenv("RELOAD", "").lower() == "false"
    
    if force_no_reload:
        reload = False
    elif force_reload:
        reload = True
        if is_windows and is_python_314_plus:
            print("[run.py] WARNING: --reload forced on Windows + Python 3.14+")
            print("[run.py] WARNING: Playwright/subprocess operations will FAIL!")
    else:
        # Default behavior: disable reload on Windows + Python 3.14+ due to event loop issues
        if is_windows and is_python_314_plus:
            reload = False
            print("[run.py] Auto-disabled reload on Windows + Python 3.14+ (Playwright compatibility)")
            print("[run.py] Use --reload to force enable (Playwright will NOT work)")
        else:
            reload = True
    
    print(f"[run.py] Starting server on {host}:{port} (reload={reload})")
    
    # Run uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["app"] if reload else None,
    )

