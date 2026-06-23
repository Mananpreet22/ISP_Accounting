import shutil
import os
import sys
from datetime import datetime


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)  # EXE folder
    else:
        return os.path.dirname(__file__)        # Script folder


def backup_database(db_path):
    base_path = get_base_path()

    # ✅ Correct backup folder (same as EXE)
    backup_dir = os.path.join(base_path, "backups")

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # ✅ Timestamped backup file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")

    # ✅ Copy DB safely
    if os.path.exists(db_path):
        shutil.copy(db_path, backup_file)
    else:
        print("⚠️ Database file not found, backup skipped")