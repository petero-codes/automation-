import time
import random
from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing
from core.window_manager import focus_window_by_title, maximize_active_window

import winreg
import shutil
import os

SUPPORTED_BROWSERS = ['Brave', 'Firefox', 'Chrome', 'Edge']

def detect_best_browser():
    """Detects which supported browser is installed on the machine."""
    candidates = [
        ('brave', 'Brave', ['Brave']),
        ('chrome', 'Google Chrome', ['Google Chrome', 'Chrome']),
        ('firefox', 'Firefox', ['Firefox']),
        ('msedge', 'Edge', ['Microsoft Edge', 'Edge']),
    ]
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

    for exe_name, title, key_matches in candidates:
        for k in installed_keys:
            if any(m.lower() in k for m in key_matches):
                return exe_name, title
        if shutil.which(exe_name):
            return exe_name, title

    return 'msedge', 'Edge'

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
    actual_exe = browser_exe if shutil.which(browser_exe) else detected_exe
    actual_title = browser_title if actual_exe == browser_exe else detected_title

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
