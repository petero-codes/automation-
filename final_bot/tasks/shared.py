import time
import random
from typing import Optional, List
from core import state
from core.logger import log
from core.input_driver import safe_press
from core.human_physics import human_typing
from core.window_manager import focus_window_by_title, maximize_active_window

import winreg
import shutil
import os

VSCODE_PATHS = [
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    r"%ProgramFiles%\Microsoft VS Code\Code.exe",
    r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe",
]

EXCEL_PATHS = [
    r"%ProgramFiles%\Microsoft Office\root\Office16\EXCEL.EXE",
    r"%ProgramFiles(x86)%\Microsoft Office\root\Office16\EXCEL.EXE",
    r"%ProgramFiles%\Microsoft Office\Office16\EXCEL.EXE",
    r"%ProgramFiles(x86)%\Microsoft Office\Office16\EXCEL.EXE",
    r"%ProgramFiles%\Microsoft Office\Office15\EXCEL.EXE",
    r"%ProgramFiles(x86)%\Microsoft Office\Office15\EXCEL.EXE",
]

def get_app_path(exe_name: str, standard_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    Multi-tier discovery for Windows executables:
      1. System PATH via shutil.which
      2. Windows Registry App Paths (HKCU and HKLM, 32-bit and 64-bit views)
      3. Standard ProgramFiles / LocalAppData install directories
    """
    # 1. System PATH
    p = shutil.which(exe_name)
    if p and os.path.isfile(p):
        return os.path.abspath(p)

    # 2. Windows Registry App Paths
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for subkey in (
            rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
            rf"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
        ):
            try:
                with winreg.OpenKey(root, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    if val:
                        cleaned = val.strip('\"\'')
                        if os.path.isfile(cleaned):
                            return os.path.abspath(cleaned)
            except OSError:
                pass

    # 3. Standard paths
    if standard_paths:
        for sp in standard_paths:
            expanded = os.path.expandvars(sp)
            if os.path.isfile(expanded):
                return os.path.abspath(expanded)

    return None

def is_vscode_installed() -> bool:
    """Verifies whether Visual Studio Code is present on this machine."""
    return get_vscode_executable() is not None

def get_vscode_executable() -> Optional[str]:
    """Returns absolute path or command for VS Code executable if installed."""
    reg_or_file = get_app_path("Code.exe", VSCODE_PATHS)
    if reg_or_file:
        return reg_or_file
    for alias in ("code.cmd", "code.exe", "code"):
        w = shutil.which(alias)
        if w:
            return os.path.abspath(w)
    return None

def is_excel_installed() -> bool:
    """Verifies whether Microsoft Excel is present on this machine."""
    return get_excel_executable() is not None

def get_excel_executable() -> Optional[str]:
    """Returns absolute path or command for Microsoft Excel executable if installed."""
    reg_or_file = get_app_path("excel.exe", EXCEL_PATHS)
    if reg_or_file:
        return reg_or_file
    for alias in ("excel.exe", "excel"):
        w = shutil.which(alias)
        if w:
            return os.path.abspath(w)
    return None

def open_app_via_run(app_name: str):
    """Launches an application via the Windows Start Menu search."""
    try:
        log(f"Verification: Pressing Start to open {app_name}")
        safe_press('win')
        time.sleep(random.uniform(0.85, 1.2))
        human_typing(app_name, wpm=random.randint(65, 95), typos=False)
        time.sleep(random.uniform(0.3, 0.5))
        safe_press('enter')
        time.sleep(random.uniform(2.5, 4.0))
    except Exception as e:
        log(f"Error opening app via start menu: {e}")
