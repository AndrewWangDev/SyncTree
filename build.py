import os
import subprocess
import sys

def convert_png_to_ico():
    try:
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        img = QImage("logo.png")
        if not img.isNull():
            img.save("logo.ico", "ICO")
            print("Successfully converted logo.png to logo.ico")
        else:
            print("Failed to load logo.png, fallback to original if possible.")
    except Exception as e:
        print(f"Warning: Icon conversion failed: {e}")

def build():
    print("Building SyncTree application using PyInstaller...")
    
    # Ensure dist and build directories don't cause conflicts
    if os.path.exists("build"):
        print("Cleaning up old build directory...")
        
    if os.path.exists("dist"):
        print("Cleaning up old dist directory...")

    convert_png_to_ico()
    icon_file = "logo.ico" if os.path.exists("logo.ico") else "logo.png"

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", "synctree",
        "--windowed",     # No console window
        "--onefile",      # Single exe
        "--clean",
        "--add-data", f"logo.png{os.pathsep}.",
        "--icon", icon_file,
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
