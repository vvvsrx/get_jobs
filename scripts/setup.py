#!/usr/bin/env python3
"""Cross-platform setup script for GetJobs."""
import os
import sys
import subprocess
import platform


def run(cmd, cwd=None):
    print(f">>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: command failed with code {result.returncode}")
        sys.exit(1)


def main():
    print(f"Setting up GetJobs on {platform.system()}...")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Check Python version
    if sys.version_info < (3, 10):
        print("Error: Python 3.10+ required")
        sys.exit(1)

    # 2. Install Python dependencies
    print("\n[1/4] Installing Python dependencies...")
    run(f"{sys.executable} -m pip install -e '{root}'")

    # 3. Install Playwright browsers
    print("\n[2/4] Installing Playwright browsers...")
    run(f"{sys.executable} -m playwright install")

    # 4. Build frontend
    print("\n[3/4] Building frontend...")
    frontend_dir = os.path.join(root, "frontend")
    if os.path.exists(frontend_dir):
        run("npm install", cwd=frontend_dir)
        run("npm run build", cwd=frontend_dir)
        # Copy build output to static/
        static_dir = os.path.join(root, "static")
        out_dir = os.path.join(frontend_dir, "out")
        if os.path.exists(out_dir):
            import shutil
            if os.path.exists(static_dir):
                shutil.rmtree(static_dir)
            shutil.copytree(out_dir, static_dir)
            print(f"Frontend built to {static_dir}")
    else:
        print("Warning: frontend directory not found")

    # 5. Create runtime directories
    print("\n[4/4] Creating runtime directories...")
    os.makedirs(os.path.join(root, "db"), exist_ok=True)
    os.makedirs(os.path.join(root, "data", "options"), exist_ok=True)

    # 6. Create .env if not exists
    env_file = os.path.join(root, ".env")
    env_example = os.path.join(root, ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        import shutil
        shutil.copy(env_example, env_file)
        print("Created .env from .env.example")

    print("\nSetup complete! Run the server with:")
    print("  python run.py")
    print("Or:")
    print("  ./scripts/run.sh    (Linux/macOS)")
    print("  scripts\\run.bat     (Windows)")


if __name__ == "__main__":
    main()
