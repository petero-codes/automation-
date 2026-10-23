import time
import random
from typing import Optional, Tuple, List
from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing
from core.window_manager import focus_window_by_title, maximize_active_window

import winreg
import shutil
import os

SUPPORTED_BROWSERS = ['Brave', 'Firefox', 'Chrome', 'Edge', 'Microsoft Edge', 'Google Chrome']

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

BROWSER_CANDIDATES = [
    ('brave', 'Brave', ['Brave'], [
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]),
    ('chrome', 'Google Chrome', ['Google Chrome', 'Chrome'], [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ]),
    ('firefox', 'Firefox', ['Firefox'], [
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
    ]),
    ('msedge', 'Microsoft Edge', ['Microsoft Edge', 'Edge'], [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ]),
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

def get_installed_browsers() -> List[Tuple[str, str, str]]:
    """Returns a list of (browser_id, display_title, exe_path) for all installed browsers."""
    installed = []
    for exe_id, title, _, paths in BROWSER_CANDIDATES:
        exe_file = f"{exe_id}.exe"
        resolved = get_app_path(exe_file, paths) or shutil.which(exe_id)
        if resolved:
            installed.append((exe_id, title, resolved))
    return installed

def detect_best_browser() -> Tuple[str, str]:
    """Detects which supported browser is installed on the machine with automatic fallback."""
    installed = get_installed_browsers()
    if installed:
        return installed[0][0], installed[0][1]

    # Fallback to StartMenuInternet registry check
    installed_keys = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, r"SOFTWARE\Clients\StartMenuInternet") as key:
                i = 0
                while True:
                    try:
                        installed_keys.append(winreg.EnumKey(key, i).lower())
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass

    for exe_name, title, key_matches, _ in BROWSER_CANDIDATES:
        for k in installed_keys:
            if any(m.lower() in k for m in key_matches):
                return exe_name, title

    return 'msedge', 'Microsoft Edge'

def open_app_via_run(app_name):
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

def open_browser(browser_exe='brave', browser_title='Brave'):
    """Open a browser or focus it if already running, ensuring it is maximized."""
    targets = [browser_title] + [b for b in SUPPORTED_BROWSERS if b != browser_title]
    if focus_window_by_title(targets):
        log(f"Verification Success: Browser already running and brought to front.")
        time.sleep(0.5)
        maximize_active_window()
        return

    detected_exe, detected_title = detect_best_browser()
    requested_installed = get_app_path(f"{browser_exe}.exe") or shutil.which(browser_exe)
    actual_exe = browser_exe if requested_installed else detected_exe
    actual_title = browser_title if requested_installed else detected_title

    try:
        log(f"Verification: Browser not found. Launching '{actual_exe}' via Start menu.")
        safe_press('win')
        time.sleep(random.uniform(0.85, 1.2))
        human_typing(actual_exe, wpm=85, typos=False)
        time.sleep(0.4)
        safe_press('enter')
        time.sleep(random.uniform(3.5, 5.5))
        focus_window_by_title(targets + [actual_title])
        maximize_active_window()
    except Exception as e:
        log(f"Error launching browser: {e}")

def _open_url(url):
    """Open a new tab, navigate cleanly to url, and yield focus to the webpage body."""
    log(f"Opening URL: {url}")
    try:
        # Snap the browser to the front before typing
        focus_window_by_title(SUPPORTED_BROWSERS)
        time.sleep(0.5)

        # Open clean new tab
        hotkey('ctrl', 't')
        time.sleep(random.uniform(0.4, 0.7))

        # Focus address bar
        hotkey('ctrl', 'l')
        time.sleep(random.uniform(0.25, 0.45))

        # Type URL with zero typos for guaranteed navigation accuracy
        human_typing(url, wpm=90, typos=False)
        if state.is_stopped(): return False

        # Submit navigation
        safe_press('enter')
        time.sleep(random.uniform(3.0, 4.5))

        # Drop address bar focus to the webpage body so scrolling & hotkeys work reliably
        safe_press('esc')
        time.sleep(0.4)
        return True
    except Exception as e:
        log(f"Error navigating to URL: {e}")
        return False
