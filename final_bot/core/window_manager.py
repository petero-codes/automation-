import ctypes
from ctypes import wintypes
import time
import platform
from core import state
from core.input_driver import hotkey
from core.logger import log

_interactive_desktop_handle = None

def bind_thread_to_interactive_desktop():
    """No-op on interactive desktop sessions to preserve input thread integrity."""
    pass

def get_foreground_title() -> str:
    bind_thread_to_interactive_desktop()
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ''
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if not length:
            return ''
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        log(f"Verification Error: Failed to get foreground title - {e}")
        return ''

def is_window_zoomed(hwnd) -> bool:
    return ctypes.windll.user32.IsZoomed(hwnd) != 0

def wait_for_window(fragments, timeout=18.0) -> bool:
    """
    Waits for a visible window matching ANY fragment to appear, brings it to foreground,
    and verifies active focus.
    """
    bind_thread_to_interactive_desktop()
    if isinstance(fragments, str):
        fragments = [fragments]
        
    log(f"Verification: Waiting for window matching {fragments}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if state.is_stopped(): return False
        
        # 1. Check if already active foreground
        current_title = get_foreground_title().lower()
        for frag in fragments:
            if frag.lower() in current_title:
                log(f"Verification Success: Active foreground window matches '{current_title}'")
                return True
        
        # 2. Search desktop and bring to front
        if focus_window_by_title(fragments):
            log(f"Verification Success: Found and focused window matching {fragments}")
            return True
            
        time.sleep(0.5)
        
    log(f"Verification Failed: Timeout waiting for window {fragments}")
    return False

def focus_window_by_title(fragments) -> bool:
    """
    Finds an existing visible window matching title fragments and brings it to front.
    Uses AttachThreadInput to bypass Windows focus-stealing restrictions.
    """
    bind_thread_to_interactive_desktop()
    if isinstance(fragments, str):
        fragments = [fragments]
        
    found = [False]
    user32 = ctypes.windll.user32

    def cb(hwnd, lparam):
        # Only inspect visible windows
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        current_title = buf.value.lower()
        
        for frag in fragments:
            if frag.lower() in current_title:
                # 1. Restore window if minimized
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9) # SW_RESTORE
                else:
                    user32.ShowWindow(hwnd, 5) # SW_SHOW
                
                # 2. Bring window to top
                user32.BringWindowToTop(hwnd)
                
                # 3. Safe Win32 SetForegroundWindow with Alt-event privilege bypass
                # Grants foreground activation without merging queues or freezing Explorer
                VK_MENU = 0x12
                KEYEVENTF_KEYUP = 0x0002
                user32.keybd_event(VK_MENU, 0, 0, 0)
                user32.SetForegroundWindow(hwnd)
                user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                
                found[0] = True
                return False # Stop enumerating
        return True
        
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    
    if found[0]:
        time.sleep(0.6)
    return found[0]

def maximize_active_window(retries=3) -> bool:
    """
    Attempts to maximize the foreground window using Win32 ShowWindow(SW_MAXIMIZE)
    with keyboard fallback, and verifies if it is zoomed.
    """
    if platform.system() != 'Windows':
        return False
        
    bind_thread_to_interactive_desktop()
    log("Verification: Attempting to maximize active window...")
    for attempt in range(retries):
        if state.is_stopped(): return False
        
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            time.sleep(0.3)
            continue
            
        if is_window_zoomed(hwnd):
            log("Verification Success: Window is already maximized.")
            return True
            
        # 1. Direct Win32 ShowWindow(SW_MAXIMIZE = 3) - instant, zero keystroke injection
        ctypes.windll.user32.ShowWindow(hwnd, 3)
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
