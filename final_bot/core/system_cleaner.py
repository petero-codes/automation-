"""
Nextgen Autonomous Workforce Engine - Legacy System Cleaner
Scans host machine for obsolete files, legacy shortcuts, and artifacts from previous
versions or Nimrod's compiled binaries, cleanly deleting and replacing them.
"""

import os
import glob
from pathlib import Path
from typing import List
from core.logger import log

def purge_legacy_system_artifacts() -> List[str]:
    """
    Detects and removes all residual files, shortcuts, and logs from older
    automation systems (e.g. Nimrod's old Nextgen_Workforce.exe, Loggy3, legacy desktop shortcuts).
    Returns list of deleted paths.
    """
    purged: List[str] = []

    user_profile = os.environ.get("USERPROFILE", "")
    appdata = os.environ.get("APPDATA", "")
    all_users_profile = os.environ.get("ALLUSERSPROFILE", r"C:\ProgramData")

    # 1. Desktop directories (User & Public)
    desktop_dirs = [
        os.path.join(user_profile, "Desktop"),
        r"C:\Users\Public\Desktop",
    ]

    shortcut_patterns = [
        "*loggy*.lnk",
        "*Loggy*.lnk",
        "*LOGGY*.lnk",
        "*nextgen*.lnk",
        "*Nextgen*.lnk",
        "*NEXTGEN*.lnk",
    ]

    for d in desktop_dirs:
        if os.path.isdir(d):
            for pat in shortcut_patterns:
                for match in glob.glob(os.path.join(d, pat)):
                    try:
                        if os.path.isfile(match):
                            os.remove(match)
                            purged.append(match)
                            log(f"[SystemCleaner] Removed legacy desktop shortcut: {match}")
                    except Exception as e:
                        log(f"[SystemCleaner] Notice removing {match}: {e}")

    # 2. Windows Startup folder
    startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    if os.path.isdir(startup_dir):
        for pat in ["*loggy*.*", "*nextgen*.*", "*Loggy*.*", "*Nextgen*.*"]:
            for match in glob.glob(os.path.join(startup_dir, pat)):
                try:
                    if os.path.isfile(match):
                        os.remove(match)
                        purged.append(match)
                        log(f"[SystemCleaner] Removed legacy startup entry: {match}")
                except Exception as e:
                    log(f"[SystemCleaner] Notice removing {match}: {e}")

    # 3. Project and Parent Directory Executables & Logs
    base_dir = Path(__file__).resolve().parent.parent  # final_bot
    parent_dir = base_dir.parent                      # python-automation
    grandparent_dir = parent_dir.parent               # workspace root

    legacy_files = [
        parent_dir / "Nextgen_Workforce.exe",
        parent_dir / "Nextgen_Workforce.zip",
        grandparent_dir / "Nextgen_Workforce.exe",
        base_dir / "idle_shorts.log",
        base_dir / "idle_firefox.log",
        base_dir / ".test_checkpoint.bin",
        base_dir / ".session_lifecycle_test.bin",
        parent_dir / "startup_crash.log",
        base_dir / "startup_crash.log",
    ]

    for f in legacy_files:
        try:
            if f.is_file():
                f.unlink()
                purged.append(str(f))
                log(f"[SystemCleaner] Removed obsolete system file: {f.name}")
        except Exception as e:
            log(f"[SystemCleaner] Notice removing {f}: {e}")

    # 4. Clean Stale Temporary Excel Lock Files & Dangling Temp Artifacts
    stale_dirs = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Desktop", "Workspaces"),
        os.path.join(user_profile, "Desktop", "Financial_Models"),
    ]
    for s_dir in stale_dirs:
        if os.path.isdir(s_dir):
            for pattern in ["~$*.xlsx", "*.tmp"]:
                for stale in glob.glob(os.path.join(s_dir, pattern)):
                    try:
                        if os.path.isfile(stale):
                            os.remove(stale)
                            purged.append(stale)
                            log(f"[SystemCleaner] Purged stale temporary file: {os.path.basename(stale)}")
                    except Exception:
                        pass

    # 5. Prevent Log Bloat and Disk I/O Lag (Keep log healthy and fast)
    main_log = base_dir / "idle_automation.log"
    if main_log.is_file():
        try:
            if main_log.stat().st_size > 512 * 1024:  # > 512 KB
                with open(main_log, "r", encoding="utf-8", errors="ignore") as lf:
                    lines = lf.readlines()
                recent_lines = lines[-250:] if len(lines) > 250 else lines
                with open(main_log, "w", encoding="utf-8") as lf:
                    lf.writelines(recent_lines)
                log("[SystemCleaner] Compacted idle_automation.log to recent 250 entries to eliminate disk lag.")
        except Exception:
            pass

    if purged:
        log(f"[SystemCleaner] Purged {len(purged)} legacy artifact(s). System environment updated cleanly.")
    return purged
