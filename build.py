import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def convert_png_to_ico():
    try:
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        logo_png = os.path.join(BASE_DIR, "logo.png")
        logo_ico = os.path.join(BASE_DIR, "logo.ico")
        img = QImage(logo_png)
        if not img.isNull():
            img.save(logo_ico, "ICO")
            print("Successfully converted logo.png to logo.ico")
        else:
            print("Failed to load logo.png, fallback to original if possible.")
    except Exception as e:
        print(f"Warning: Icon conversion failed: {e}")

def build():
    print("Building SyncTree application using PyInstaller...")
    
    # 彻底清理旧的构建残留（绝对路径锚定，防止误删调用者工作区）
    for dir_name in ["build", "dist"]:
        target_dir = os.path.join(BASE_DIR, dir_name)
        if os.path.exists(target_dir):
            print(f"Cleaning up old {target_dir} directory...")
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                print(f"Warning: Could not remove {target_dir}: {e}")

    convert_png_to_ico()
    logo_ico = os.path.join(BASE_DIR, "logo.ico")
    logo_png = os.path.join(BASE_DIR, "logo.png")
    icon_file = logo_ico if os.path.exists(logo_ico) else logo_png

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", "synctree",
        "--distpath", os.path.join(BASE_DIR, "dist"),
        "--workpath", os.path.join(BASE_DIR, "build"),
        "--specpath", BASE_DIR,
        "--windowed",     # No console window
        "--onefile",      # Single file
        "--clean",
        "--add-data", f"{logo_png}{os.pathsep}.",
        "--icon", icon_file,
        os.path.join(BASE_DIR, "main.py")
    ]
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code: {e.returncode}")
        return

    exe_name = "synctree.exe" if sys.platform == 'win32' else "synctree"
    dist_path = os.path.join(BASE_DIR, "dist", exe_name)
    if os.path.exists(dist_path):
        print(f"Build successful! Executable is located at: {dist_path}")
    else:
        print("Build finished, check dist directory for outputs.")

if __name__ == "__main__":
    build()
