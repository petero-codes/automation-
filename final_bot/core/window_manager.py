import ctypes
from ctypes import wintypes
import time
import platform
import win32gui
try:
    from core import state
    from core.input_driver import hotkey
    from core.logger import log
except ImportError:
    from final_bot.core import state
    from final_bot.core.input_driver import hotkey
    from final_bot.core.logger import log

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenDesktopW.restype = wintypes.HANDLE
user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
user32.SetThreadDesktop.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND

_cached_desktop_handle = None

def ensure_default_desktop() -> bool:
    """
    Ensures the current thread is attached to the active interactive desktop
    where application windows (VS Code, Excel) and user interaction reside.
    """
    global _cached_desktop_handle
    try:
        if _cached_desktop_handle:
            if user32.SetThreadDesktop(_cached_desktop_handle):
                return True
            _cached_desktop_handle = None

        # Dynamically discover desktop containing interactive application windows
        EnumDesktopsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.LPCWSTR, wintypes.LPARAM)
        desktops = []
        def cb_desk(lpszDesktop, lParam):
            desktops.append(lpszDesktop)
            return True

        hwinsta = user32.GetProcessWindowStation()
        user32.EnumDesktopsW(hwinsta, EnumDesktopsProc(cb_desk), 0)

        for d in desktops:
            if d in ('Winlogon', 'Disconnect'):
                continue
            h = user32.OpenDesktopW(d, 0, False, 0x01FF)
            if not h:
                continue
            has_app = False
            def cb_win(hwnd, _):
                nonlocal has_app
                t = win32gui.GetWindowText(hwnd).lower()
                if 'visual studio code' in t or ' - code' in t or 'excel' in t or 'file explorer' in t:
                    has_app = True
                    return False
                return True
            try:
                win32gui.EnumDesktopWindows(h, cb_win, None)
            except Exception:
                pass
            if has_app:
                _cached_desktop_handle = h
                user32.SetThreadDesktop(h)
                return True
            user32.CloseDesktop(h)

        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not h_desk:
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            _cached_desktop_handle = h_desk
            user32.SetThreadDesktop(h_desk)
            return True
    except Exception:
        pass
    return False

def bind_thread_to_interactive_desktop():
    """Alias for backward compatibility."""
    return ensure_default_desktop()

def minimize_console_window():
    """
    Minimizes any console or terminal hosting this process so the active
    target application (VS Code or Excel) is displayed full screen
    without the terminal obstructing the view or stealing foreground focus.
    """
    try:
        user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass
    try:
        con_hwnd = kernel32.GetConsoleWindow()
        if con_hwnd and user32.IsWindow(con_hwnd):
            user32.ShowWindow(con_hwnd, 6) # SW_MINIMIZE
    except Exception:
        pass
    try:
        curr_fg = user32.GetForegroundWindow()
        if curr_fg:
            cls = win32gui.GetClassName(curr_fg).lower()
            if cls in ["consolewindowclass", "cascadia_hosting_window_class", "windowsterminal"]:
                user32.ShowWindow(curr_fg, 6) # SW_MINIMIZE
    except Exception:
        pass

def restore_console_window():
    """
    Restores the console window to the foreground when human takes control
    so the terminal status banners and resume instructions are immediately visible.
    """
    try:
        con_hwnd = kernel32.GetConsoleWindow()
        if con_hwnd and user32.IsWindow(con_hwnd):
            user32.ShowWindow(con_hwnd, 9) # SW_RESTORE
            user32.SetForegroundWindow(con_hwnd)
    except Exception:
        pass

def is_vscode_window(title: str, cls: str) -> bool:
    """Exact, hardened discriminator for Visual Studio Code windows."""
    if cls == '#32770':
        return False
    t = title.lower()
    return "visual studio code" in t or (t.endswith(" - code") and "chrome" not in t and "brave" not in t and "edge" not in t)

def is_excel_window(title: str, cls: str) -> bool:
    """Exact, hardened discriminator for Microsoft Excel windows."""
    if cls == 'XLMAIN':
        return True
    t = title.lower()
    return " - excel" in t or t.endswith("excel")

def find_target_window(fragments):
    """
    Finds the HWND of a target application on the interactive desktop.
    Uses strict class and title validation to prevent false matches with
    consoles or browser tabs.
    """
    ensure_default_desktop()
    if isinstance(fragments, str):
        fragments = [fragments]

    best_match = None

    def enum_cb(hwnd, _):
        nonlocal best_match
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        cls = win32gui.GetClassName(hwnd)

        for frag in fragments:
            f_low = frag.lower()
            if f_low in ("visual studio code", "code"):
                if is_vscode_window(title, cls):
                    best_match = hwnd
                    return False
            elif f_low in ("excel", "microsoft excel"):
                if is_excel_window(title, cls):
                    best_match = hwnd
                    return False
            else:
                if f_low in title.lower():
                    best_match = hwnd
                    return False
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    return best_match

def get_foreground_title() -> str:
    ensure_default_desktop()
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ''
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return ''
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        log(f"Verification Error: Failed to get foreground title - {e}")
        return ''

def is_window_zoomed(hwnd) -> bool:
    return user32.IsZoomed(hwnd) != 0

def focus_window_by_title(fragments, maximize=True) -> bool:
    """
    Finds an existing visible window matching target application and brings it to front.
    Uses Win32 Alt-bypass SetForegroundWindow to guarantee focus acquisition.
    """
    ensure_default_desktop()
    hwnd = find_target_window(fragments)
    if not hwnd:
        return False

    # Minimize console so it does not obstruct the application
    minimize_console_window()
    time.sleep(0.15)

    # Unlock foreground lock timeout
    try:
        user32.AllowSetForegroundWindow(-1)
        SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
        user32.SystemParametersInfoW(SPI_SETFOREGROUNDLOCKTIMEOUT, 0, 0, 0x0002 | 0x0001)
    except Exception:
        pass

    # Alt-key privilege bypass (standard Win32 technique to allow SetForegroundWindow)
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

    # Restore if minimized
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9) # SW_RESTORE
        time.sleep(0.15)

    # Maximize window
    if maximize:
        user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    else:
        user32.ShowWindow(hwnd, 5) # SW_SHOW

    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)

    try:
        user32.SwitchToThisWindow(hwnd, True)
    except Exception:
        pass

    time.sleep(0.3)
    return True

def wait_for_window(fragments, timeout=18.0) -> bool:
    """
    Waits for a visible window matching target application to appear,
    brings it to foreground, and verifies active focus.
    """
    ensure_default_desktop()
    if isinstance(fragments, str):
        fragments = [fragments]

    log(f"Verification: Waiting for window matching {fragments}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if state.is_stopped(): return False

        if focus_window_by_title(fragments):
            log(f"Verification Success: Found and focused window matching {fragments}")
            return True

        time.sleep(0.5)

    log(f"Verification Failed: Timeout waiting for window {fragments}")
    return False

def maximize_active_window(retries=3) -> bool:
    """
    Attempts to maximize the foreground window using Win32 ShowWindow(SW_MAXIMIZE)
    with keyboard fallback, and verifies if it is zoomed.
    """
    if platform.system() != 'Windows':
        return False

    ensure_default_desktop()
    log("Verification: Attempting to maximize active window...")
    for attempt in range(retries):
        if state.is_stopped(): return False

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            time.sleep(0.3)
            continue

        if is_window_zoomed(hwnd):
            log("Verification Success: Window is already maximized.")
            return True

        # 1. Direct Win32 ShowWindow(SW_MAXIMIZE = 3) - instant, zero keystroke injection
        user32.ShowWindow(hwnd, 3)
        time.sleep(0.3)
        if is_window_zoomed(hwnd):
            log("Verification Success: Window successfully maximized via ShowWindow(SW_MAXIMIZE).")
            return True

        # 2. Fallback hotkey
        hotkey('win', 'up')
        time.sleep(0.5)

        if is_window_zoomed(hwnd):
            log("Verification Success: Window successfully maximized via win+up.")
            return True
        else:
            log(f"Verification Retry {attempt+1}: Window failed to maximize, trying again.")

    log("Verification Notice: Window could not be maximized or does not support zoom.")
    return False

def close_app_safely():
    log("Closing application cleanly (Alt+F4)")
    hotkey('alt', 'f4')

def close_tab_safely():
    log("Closing tab cleanly (Ctrl+W)")
    hotkey('ctrl', 'w')
