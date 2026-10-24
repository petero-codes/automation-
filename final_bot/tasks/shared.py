import os
import sys
import time
import glob
import random
import shutil
import winreg
import subprocess
import ctypes
from typing import Optional, List

from core import state
from core.logger import log
from core.input_driver import safe_press, hotkey
from core.human_physics import human_typing
from core.window_manager import (
    ensure_default_desktop,
    find_target_window,
    focus_window_by_title,
    wait_for_window,
    maximize_active_window,
    minimize_console_window,
)

VSCODE_PATHS = [
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    r"%ProgramFiles%\Microsoft VS Code\Code.exe",
    r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe",
]

EXCEL_PATHS = [
    r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
    r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
    r"C:\Program Files\Microsoft Office\Office15\EXCEL.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office15\EXCEL.EXE",
]

def get_app_path(exe_name: str, standard_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    Multi-tier discovery for Windows executables:
      1. Standard ProgramFiles / LocalAppData install directories (deterministic)
      2. Windows Registry App Paths (HKCU and HKLM, 32-bit and 64-bit views)
      3. System PATH via shutil.which
    """
    # 1. Standard paths first (fastest and most deterministic)
    if standard_paths:
        for sp in standard_paths:
            expanded = os.path.expandvars(sp)
            if os.path.isfile(expanded):
                return os.path.abspath(expanded)

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

    # 3. System PATH
    p = shutil.which(exe_name)
    if p and os.path.isfile(p):
        return os.path.abspath(p)

    return None

def is_vscode_installed() -> bool:
    """Verifies whether Visual Studio Code is present on this machine."""
    return get_vscode_executable() is not None

def get_vscode_executable() -> Optional[str]:
    """Returns absolute path for VS Code executable if installed."""
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
    """Returns absolute path for Microsoft Excel executable if installed."""
    reg_or_file = get_app_path("EXCEL.EXE", EXCEL_PATHS)
    if reg_or_file:
        return reg_or_file
    for alias in ("excel.exe", "excel"):
        w = shutil.which(alias)
        if w:
            return os.path.abspath(w)
    return None

def launch_code_process(args: list) -> subprocess.Popen:
    """
    Launches VS Code process detached with redirected I/O to prevent console pollution
    and guarantees it attaches to the interactive user desktop.
    """
    flags = 0
    si = None
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        si = subprocess.STARTUPINFO()
        si.lpDesktop = r"Winsta0\Default"
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        startupinfo=si
    )

def launch_excel_process(args: list) -> subprocess.Popen:
    """
    Launches Excel process detached with redirected I/O to prevent console pollution
    and guarantees it attaches to the interactive user desktop.
    """
    flags = 0
    si = None
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        si = subprocess.STARTUPINFO()
        si.lpDesktop = r"Winsta0\Default"
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        startupinfo=si
    )

def sanitize_excel_environment(workspace: Optional[str] = None):
    """
    Zero-Trust Excel Pre-Launch Sanitizer:
    1. Removes stale temporary lock files (~$*.xlsx) in workspace directory.
    2. Detects and terminates orphaned headless/zombie EXCEL.EXE processes that have no visible window.
    3. Guarantees fresh, interactive startup.
    """
    # 1. Terminate headless zombie EXCEL.EXE processes if no GUI Excel window is active
    if not find_target_window(["Excel", "Microsoft Excel"]):
        try:
            subprocess.run(["taskkill", "/f", "/im", "excel.exe"], capture_output=True, text=True)
            time.sleep(0.3)
        except Exception:
            pass

    # 2. Purge stale lock files
    if workspace and os.path.exists(workspace):
        for lock in glob.glob(os.path.join(workspace, "~$*.xlsx")):
            try:
                os.remove(lock)
                log(f"[CLEANUP] Purged stale Excel lock file: {os.path.basename(lock)}")
            except Exception:
                pass

def launch_or_focus_vscode(
    workspace_dir: str,
    file_path: Optional[str] = None,
    line: int = 1,
    col: int = 1
) -> bool:
    """
    Bulletproof VS Code launcher and workspace/file restoration engine:
    1. Checks if a real Visual Studio Code window is already visible on the interactive desktop.
    2. If running: reuses existing window via `code -r <workspace_dir>` and brings to front.
    3. If not running: directly executes `code <workspace_dir>` via detached subprocess.
    4. Ensures file exists on disk and opens via `code -r -g <file_path>:<line>:<col>`.
    5. Maximizes active window full-screen.
    """
    ensure_default_desktop()
    target_titles = ["Visual Studio Code"]
    vscode_exe = get_vscode_executable()
    if not vscode_exe:
        log("[Software Engineering] VS Code executable not detected on machine.")
        return False

    # Pre-create workspace directory
    if workspace_dir:
        os.makedirs(workspace_dir, exist_ok=True)

    # Pre-create file on disk if specified
    if file_path:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    pass
            except Exception as e:
                log(f"[Software Engineering] File pre-creation notice: {e}")

    # Check if VS Code is already open
    if focus_window_by_title(target_titles):
        log("[Software Engineering] Visual Studio Code is running; bringing to foreground.")
        if file_path and os.path.isfile(file_path):
            try:
                launch_code_process([vscode_exe, "-r", "-g", f"{file_path}:{line}:{col}"])
                time.sleep(1.0)
            except Exception as e:
                log(f"[Software Engineering] CLI file open notice: {e}")
        elif workspace_dir:
            try:
                launch_code_process([vscode_exe, "-r", workspace_dir])
                time.sleep(1.0)
            except Exception as e:
                log(f"[Software Engineering] CLI workspace reuse notice: {e}")
        maximize_active_window()
        return True

    # Fresh launch
    log(f"[Software Engineering] Launching clean Visual Studio Code via {vscode_exe}...")
    minimize_console_window()
    try:
        if file_path and os.path.isfile(file_path):
            launch_code_process([vscode_exe, workspace_dir, "-g", f"{file_path}:{line}:{col}"])
        elif workspace_dir:
            launch_code_process([vscode_exe, workspace_dir])
        else:
            launch_code_process([vscode_exe])
    except Exception as e:
        log(f"[Software Engineering] Process spawn failed: {e}")
        return False

    # Wait for window to initialize, focus, and maximize
    if wait_for_window(target_titles, timeout=18.0):
        time.sleep(1.0)
        maximize_active_window()
        log("Verification Success: Visual Studio Code opened and maximized in foreground.")
        return True

    log("[Software Engineering] Verification Failed: VS Code window did not appear.")
    return False

def launch_or_focus_excel(workbook_path: Optional[str] = None) -> bool:
    """
    Bulletproof Microsoft Excel launcher and workbook restoration engine:
    1. Sanitizes environment (clears stale lock files, terminates zombie headless processes).
    2. Focuses existing session if active and writable.
    3. Launches interactive instance via COM Dispatch (Visible=True, WindowState=xlMaximized)
       or directly spawns EXCEL.EXE process.
    4. Guarantees window is maximized and in the foreground.
    """
    ensure_default_desktop()
    target_titles = ["Excel", "Microsoft Excel"]
    workspace = os.path.dirname(workbook_path) if workbook_path else None
    sanitize_excel_environment(workspace)
    minimize_console_window()

    excel_exe = get_excel_executable()
    if not excel_exe:
        log("[Financial Modeling] Microsoft Excel executable not detected on machine.")
        return False

    # Check if Excel is already running
    if focus_window_by_title(target_titles):
        log("[Financial Modeling] Microsoft Excel is already running; bringing to foreground.")
        maximize_active_window()
        return True

    log(f"[Financial Modeling] Launching Microsoft Excel via COM / {excel_exe}...")

    # Method 1: Try COM Dispatch (creates clean, visible, maximized instance instantly)
    com_launched = False
    try:
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        if xl:
            xl.Visible = True
            try:
                xl.WindowState = -4137 # xlMaximized
            except Exception:
                pass

            if workbook_path and os.path.exists(workbook_path):
                wb = xl.Workbooks.Open(workbook_path)
            elif workbook_path:
                os.makedirs(os.path.dirname(os.path.abspath(workbook_path)), exist_ok=True)
                wb = xl.Workbooks.Add()
                try:
                    wb.SaveAs(workbook_path)
                except Exception:
                    pass
            else:
                wb = xl.Workbooks.Add()

            com_launched = True
            time.sleep(1.0)
    except Exception as e:
        log(f"[Financial Modeling] COM dispatch note: {e}")

    # Method 2: Process spawn fallback
    if not com_launched:
        try:
            if workbook_path and os.path.exists(workbook_path):
                launch_excel_process([excel_exe, workbook_path])
            else:
                launch_excel_process([excel_exe])
        except Exception as e:
            log(f"[Financial Modeling] Direct launch failed: {e}")
            return False

    # Wait for window, focus, and maximize
    if wait_for_window(target_titles, timeout=18.0):
        time.sleep(0.5)
        maximize_active_window()
        log("Verification Success: Microsoft Excel opened and maximized in foreground.")
        return True

    log("[Financial Modeling] Verification Failed: Excel window did not appear.")
    return False

def excel_go_to_cell(cell_ref: str) -> bool:
    """
    Uses Excel's native 'Go To' dialog (F5) to jump directly to target cell (e.g. 'B4', 'C12').
    Guarantees 100% cell coordinate alignment without accumulating arrow key drift.
    """
    target_titles = ["Excel", "Microsoft Excel"]
    if not focus_window_by_title(target_titles):
        return False

    safe_press('f5')
    time.sleep(0.35)
    human_typing(cell_ref, wpm=120, typos=False)
    time.sleep(0.2)
    safe_press('enter')
    time.sleep(0.3)
    return True

def open_app_via_run(app_name: str):
    """Legacy helper maintained for backward compatibility."""
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
