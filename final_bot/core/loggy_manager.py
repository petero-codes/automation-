import ctypes
from ctypes import wintypes
import time
from core.logger import log

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE = 0
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def _bind_to_interactive_desktop():
    GENERIC_ALL = 0x10000000
    desk = user32.OpenInputDesktop(0, False, GENERIC_ALL)
    if desk:
        user32.SetThreadDesktop(desk)
        user32.CloseDesktop(desk)
        return True
    return False

def _press_vk(vk):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(vk, 0, 0x0002, 0)

def find_loggy_window():
    """Finds the main window handle (HWND) for Loggy3."""
    _bind_to_interactive_desktop()
    found_hwnd = [None]

    def cb(hwnd, _):
        if user32.IsWindow(hwnd):
            l = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, buf, l + 1)
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)

            title = buf.value.lower()
            cls_name = cls_buf.value

            if buf.value == "Loggy3" and "Tauri" in cls_name:
                found_hwnd[0] = hwnd
                return False
            elif "loggy3" in title and "recorder" not in title:
                found_hwnd[0] = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found_hwnd[0]

def launch_loggy_via_start():
    """Launches Loggy3 via the Windows Start Menu route."""
    log("[Loggy3] Launching Loggy3 via Start Menu...")
    _press_vk(0x5B) # Win key
    time.sleep(1.0)

    for ch in "loggy3":
        vk = user32.VkKeyScanW(ord(ch)) & 0xFF
        _press_vk(vk)
        time.sleep(0.06)

    time.sleep(0.5)
    _press_vk(0x0D) # Enter key
    time.sleep(3.0)

def focus_and_maximize_loggy(hwnd):
    """Brings Loggy3 to the front and maximizes it."""
    _bind_to_interactive_desktop()
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.5)
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    time.sleep(0.8)

    fg_hwnd = user32.GetForegroundWindow()
    if fg_hwnd != hwnd:
        fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
        target_tid = user32.GetWindowThreadProcessId(hwnd, None)
        if fg_tid and target_tid and fg_tid != target_tid:
            user32.AttachThreadInput(target_tid, fg_tid, True)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(target_tid, fg_tid, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
    time.sleep(0.8)

def click_loggy_record_button(hwnd):
    """
    Clicks the bottom-left action button in Loggy3:
    Checks if red button is already active (recording). If not, clicks it.
    """
    _bind_to_interactive_desktop()
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    left = max(0, rect.left)
    top = max(0, rect.top)
    width = min(screen_w, rect.right - left)
    height = min(screen_h, rect.bottom - top)

    click_x = left + int(width * 0.055)
    click_y = top + int(height * 0.967)

    # Check if already recording (red button color check)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(click_x - 5, click_y - 5, click_x + 5, click_y + 5))
        r, g, b = img.getpixel((5, 5))[:3]
        if r > 160 and g < 90 and b < 90:
            log("[Loggy3] Red button detected — Loggy3 is already actively recording.")
            return True
    except Exception:
        pass

    log(f"[Loggy3] Clicking Start Recording button at ({click_x}, {click_y})...")
    user32.SetCursorPos(click_x, click_y)
    time.sleep(0.25)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.12)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(1.0)
    log("[Loggy3] Record button clicked successfully.")
    return True

def minimize_loggy(hwnd):
    """Minimizes the Loggy3 window to keep desktop clean."""
    _bind_to_interactive_desktop()
    user32.ShowWindow(hwnd, SW_MINIMIZE)
    time.sleep(1.0)
    log("[Loggy3] Window minimized to background.")

def ensure_loggy_running(wait_timeout=25):
    """
    Verifies Loggy3 is open and recording.
    If not open, launches it, waits for initialization, starts recording, and minimizes it.
    """
    log("[Loggy3] Checking Loggy3 application status...")
    hwnd = find_loggy_window()

    if not hwnd:
        log("[Loggy3] Loggy3 not detected. Auto-launching...")
        launch_loggy_via_start()

        # Wait for window to register
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            hwnd = find_loggy_window()
            if hwnd:
                log(f"[Loggy3] Loggy3 window detected (HWND={hwnd}).")
                # Give it a short pause to finish UI rendering
                time.sleep(3.0)
                break
            time.sleep(1.5)

    if hwnd:
        focus_and_maximize_loggy(hwnd)
        time.sleep(1.0)
        click_loggy_record_button(hwnd)
        time.sleep(1.0)
        minimize_loggy(hwnd)
        log("[Loggy3] Loggy3 is ready and actively running in the background.")
        return True
    else:
        log("[Loggy3] Warning: Loggy3 window could not be detected. Proceeding with bot automation.")
        return False
