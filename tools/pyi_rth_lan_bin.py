import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    lib_dir = os.path.join(sys._MEIPASS, "lan-bin", "lib")
    if os.path.isdir(lib_dir):
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            lib_dir + (os.pathsep + prev if prev else "")
        )
