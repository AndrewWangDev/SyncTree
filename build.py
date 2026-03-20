import os
import subprocess
import sys

def build():
    print("Building SyncTree application using PyInstaller...")
    
    # Ensure dist and build directories don't cause conflicts
    if os.path.exists("build"):
        print("Cleaning up old build directory...")
        
    if os.path.exists("dist"):
        print("Cleaning up old dist directory...")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", "synctree",
        "--windowed",     # No console window
        "--onefile",      # Single exe
        "--clean",
        "--add-data", f"logo.png{os.pathsep}.",
        "--icon", "logo.png",
        "main.py"
    ]
    
    subprocess.check_call(cmd)
    
    dist_path = os.path.join("dist", "synctree.exe")
    if os.path.exists(dist_path):
        print(f"Build successful! Executable is located at: {dist_path}")
    else:
        print("Build failed. See logs for details.")

if __name__ == "__main__":
    build()
