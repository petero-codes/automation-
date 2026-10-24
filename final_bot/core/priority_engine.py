import ctypes
from ctypes import wintypes
import math
import threading
import time
from typing import Callable, Optional

from core import state
from core.logger import log
from core.input_driver import emergency_cleanup

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ======================================================================
# CONSTANTS & STRUCTURES (WIN32 LOW-LEVEL HOOKS)
# ======================================================================
WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_PAUSE = 0x13
VK_ESCAPE = 0x1B
VK_F8 = 0x77

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('pt', POINT),
        ('mouseData', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulong)
    ]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulong)
    ]

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]


def get_idle_time_ms() -> int:
    """Returns elapsed milliseconds since the last human or system input."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        return kernel32.GetTickCount() - lii.dwTime
    return 0


# ======================================================================
# HUMAN INPUT PRIORITY CONTROLLER (WIN32 LOW-LEVEL INPUT HOOKS)
# ======================================================================
class PriorityEngine:
    """
    User-mode Win32 Low-Level Input Monitor & Priority Controller.
    Instantly yields complete PC control back to human upon:
      - Mouse displacement > 25px
      - Left / Right / Middle mouse button clicks
      - Dedicated toggle key ([PAUSE] or [F8])
      - Double-tap [ESC]
    Measures and logs actual interruption latency via high-resolution performance counters.
    """
    def __init__(self, displacement_threshold: float = 25.0):
        self.displacement_threshold = displacement_threshold
        self.last_mouse_pos: Optional[tuple[int, int]] = None
        self.last_esc_time: float = 0.0
        self.esc_tap_count: int = 0
        self.last_yield_latency_ms: Optional[float] = None
        self._last_yield_reason: str = "Human Input"
        
        self._mouse_hook = None
        self._keyboard_hook = None
        self._hook_thread: Optional[threading.Thread] = None
        self._hook_thread_id: Optional[int] = None
        self._running = False
        
        # Dedicated background cleanup worker to avoid thread spawning overhead in hook callback
        self._cleanup_trigger = threading.Event()
        self._cleanup_worker = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_worker.start()
        
        # Keep references to callbacks to prevent GC collection
        self._mouse_proc = HOOKPROC(self._low_level_mouse_proc)
        self._keyboard_proc = HOOKPROC(self._low_level_keyboard_proc)

    def _cleanup_loop(self):
        """Persistent background worker that safely cleans hardware input and persists logs without blocking hook pump."""
        while True:
            self._cleanup_trigger.wait()
            self._cleanup_trigger.clear()
            reason = self._last_yield_reason or "Human Input"
            try:
                emergency_cleanup()
            except Exception as e:
                pass
            try:
                from core.session_manager import session_mgr
                session_mgr.mark_paused(reason)
            except Exception:
                pass
            lat_str = f" in {self.last_yield_latency_ms:.2f}ms" if self.last_yield_latency_ms is not None else ""
            log(f"[PriorityEngine] Human input detected ({reason}). Automation yielded{lat_str}.")

    def trigger_instant_yield(self, reason: str, event_time_ms: Optional[int] = None) -> float:
        """
        Halts automation immediately upon human input and restores raw human control.
        Executes in microsecond time by delegating I/O and cleanup to background worker.
        """
        t_start = time.perf_counter()
        if not state.automation_active.is_set():
            return 0.0

        # Fast path: immediately halt input injection flags and update session state
        state.request_stop()
        state.automation_active.clear()
        try:
            from core.session_manager import session_mgr, SessionState
            session_mgr.state = SessionState.PAUSED
        except Exception:
            pass

        t_end = time.perf_counter()
        latency_ms = (t_end - t_start) * 1000.0
        self.last_yield_latency_ms = latency_ms
        self._last_yield_reason = reason

        # Signal persistent background worker to release held keys and flush logs to disk
        self._cleanup_trigger.set()

        return latency_ms

    def _is_bot_injecting(self) -> bool:
        """Determines if the active input was generated by the bot."""
        return state.injecting_key.locked()

    def _low_level_mouse_proc(self, nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> int:
        if nCode >= 0:
            # If automation is not active, return immediately with zero calculation overhead
            if not state.automation_active.is_set():
                return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

            if not self._is_bot_injecting():
                info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                # 1. Mouse Button Clicks (Left, Right, Middle)
                if wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                    btn_name = {
                        WM_LBUTTONDOWN: "Left Click",
                        WM_RBUTTONDOWN: "Right Click",
                        WM_MBUTTONDOWN: "Middle Click"
                    }.get(wParam, "Button Click")
                    self.trigger_instant_yield(f"Hardware {btn_name}", event_time_ms=info.time)
                
                # 2. Mouse Displacement (> 25px)
                elif wParam == WM_MOUSEMOVE:
                    cur_pos = (info.pt.x, info.pt.y)
                    if self.last_mouse_pos is not None:
                        dist = math.hypot(cur_pos[0] - self.last_mouse_pos[0], cur_pos[1] - self.last_mouse_pos[1])
                        if dist >= self.displacement_threshold:
                            self.trigger_instant_yield(f"Mouse Displacement ({dist:.1f}px > {self.displacement_threshold}px)", event_time_ms=info.time)
                    self.last_mouse_pos = cur_pos
            else:
                # Update pos during bot moves without tripping displacement check
                info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                self.last_mouse_pos = (info.pt.x, info.pt.y)

        return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

        return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

    def _low_level_keyboard_proc(self, nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> int:
        if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            if not self._is_bot_injecting():
                kb_info = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb_info.vkCode

                # Check modifier keys for Emergency Stop
                ctrl_down = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0   # VK_CONTROL
                shift_down = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0  # VK_SHIFT

                # Emergency Stop: Ctrl+PAUSE, Shift+PAUSE, Ctrl+F8, or VK_CANCEL (0x03 Ctrl+Break)
                if (vk in (VK_PAUSE, VK_F8) and (ctrl_down or shift_down)) or vk == 0x03:
                    log("[PriorityEngine] EMERGENCY STOP triggered via hotkey.")
                    try:
                        from core.session_manager import session_mgr
                        session_mgr.terminate_session("Emergency Stop Hotkey")
                    except Exception as e:
                        log(f"[PriorityEngine] Emergency stop note: {e}")
                    return user32.CallNextHookEx(self._keyboard_hook, nCode, wParam, lParam)

                # 1. Dedicated Toggle Keys: [PAUSE] or [F8] (Toggles Pause / Resume)
                if vk in (VK_PAUSE, VK_F8):
                    key_label = "[PAUSE]" if vk == VK_PAUSE else "[F8]"
                    if state.automation_active.is_set() and not state.is_stopped():
                        self.trigger_instant_yield(f"Dedicated Toggle Key {key_label} (Pause)", event_time_ms=kb_info.time)
                    else:
                        try:
                            from core.session_manager import session_mgr
                            session_mgr.request_resume(f"Dedicated Toggle Key {key_label} (Resume)")
                        except Exception as e:
                            log(f"[PriorityEngine] Resume request note: {e}")

                # 2. Double-tap [ESC]
                elif vk == VK_ESCAPE and state.automation_active.is_set():
                    now = time.monotonic()
                    if now - self.last_esc_time <= 0.8:
                        self.esc_tap_count += 1
                    else:
                        self.esc_tap_count = 1
                    self.last_esc_time = now

                    if self.esc_tap_count >= 2:
                        self.esc_tap_count = 0
                        self.trigger_instant_yield("Double-tap [ESC]", event_time_ms=kb_info.time)

        return user32.CallNextHookEx(self._keyboard_hook, nCode, wParam, lParam)

    def _message_pump(self):
        """Dedicated OS message loop for Windows low-level hook callbacks."""
        self._hook_thread_id = kernel32.GetCurrentThreadId()
        
        self._mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._mouse_proc,
            0,
            0
        )
        self._keyboard_hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._keyboard_proc,
            0,
            0
        )
        
        if not self._mouse_hook or not self._keyboard_hook:
            log("[PriorityEngine] Error setting Windows low-level hooks.")
            return

        log("[PriorityEngine] Windows low-level input hooks installed successfully.")
        
        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
        if self._keyboard_hook:
            user32.UnhookWindowsHookEx(self._keyboard_hook)

    def start(self):
        if self._running:
            return
        self._running = True
        self._hook_thread = threading.Thread(target=self._message_pump, daemon=True)
        self._hook_thread.start()

    def stop(self):
        self._running = False
        if self._hook_thread_id:
            user32.PostThreadMessageW(self._hook_thread_id, 0x0012, 0, 0) # WM_QUIT


# Global singleton instance
priority_engine = PriorityEngine(displacement_threshold=25.0)

def start_priority_engine():
    priority_engine.start()

def stop_priority_engine():
    priority_engine.stop()
