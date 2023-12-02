import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": ["os", "shutil", "sys", "webbrowser", "subprocess", "platform", "wx", "wx.adv", "PIL", "wx.lib.delayedresult", "wx.lib.buttons"],
    "include_files": [
        ("./img/background2.png", "img/background2.png"),
        ("./img/github_icon.gif", "img/github_icon.gif"),
        ("./img/busy_loading.gif", "img/busy_loading.gif")
    ],
    "excludes": ["tkinter"]  # Exclude tkinter if you're not using it
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="zenWai_Compress_images",
    version="0.3",
    description="Compress images from a source to a destination directory",
    options={"build_exe": build_exe_options},
    executables=[Executable("compress_images.py", base=base, icon="./img/icon.ico")]
)
