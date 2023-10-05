import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": ["os", "shutil", "sys", "webbrowser", "wx", "wx.adv", "PIL"],
    "include_files": [
        ("./img/background.jpg", "img/background.jpg"),
        ("./img/github_icon.gif", "img/github_icon.gif"),
        ("./img/busy_loading.gif", "img/busy_loading.gif")
    ],
    "excludes": ["tkinter"]  # Exclude tkinter if you're not using it
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="YourAppName",
    version="0.1",
    description="Your application description",
    options={"build_exe": build_exe_options},
    executables=[Executable("compress_images.py", base=base, icon="./img/icon.ico")]
)
