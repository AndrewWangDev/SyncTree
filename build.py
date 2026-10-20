import os
import shutil
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
    
    # 彻底清理旧的构建残留
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            print(f"Cleaning up old {dir_name} directory...")
            try:
                shutil.rmtree(dir_name)
            except Exception as e:
                print(f"Warning: Could not remove {dir_name}: {e}")

    convert_png_to_ico()
    icon_file = "logo.ico" if os.path.exists("logo.ico") else "logo.png"

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", "synctree",
        "--windowed",     # No console window
        "--onefile",      # Single file
        "--clean",
        "--add-data", f"logo.png{os.pathsep}.",
        "--icon", icon_file,
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code: {e.returncode}")
        return

    exe_name = "synctree.exe" if sys.platform == 'win32' else "synctree"
    dist_path = os.path.join("dist", exe_name)
    if os.path.exists(dist_path):
        print(f"Build successful! Executable is located at: {dist_path}")
    else:
        print("Build finished, check dist directory for outputs.")

if __name__ == "__main__":
    build()
