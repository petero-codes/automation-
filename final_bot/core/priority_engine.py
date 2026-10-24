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
    Non-invasive Hardware Input Priority Monitor & Yield Controller.
    Uses asynchronous 100Hz hardware input polling (GetCursorPos & GetAsyncKeyState)
    to monitor human interaction without dangerous low-level OS hooks (WH_MOUSE_LL / WH_KEYBOARD_LL),
    guaranteeing zero system lag, zero input interception deadlocks, and zero desktop freezes.
    
    Instantly yields complete PC control back to human (< 10ms) upon:
      - Mouse displacement > 25px
      - Left / Right / Middle mouse button clicks
      - Dedicated toggle key ([PAUSE] or [F8])
      - Double-tap [ESC]
      - Emergency Stop: [Ctrl+PAUSE], [Shift+PAUSE], [Ctrl+F8]
    """
    def __init__(self, displacement_threshold: float = 25.0):
        self.displacement_threshold = displacement_threshold
        self.last_mouse_pos: Optional[tuple[int, int]] = None
        self.last_esc_time: float = 0.0
        self.esc_tap_count: int = 0
        self.last_yield_latency_ms: Optional[float] = None
        self._last_yield_reason: str = "Human Input"
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Dedicated background cleanup worker
        self._cleanup_trigger = threading.Event()
        self._cleanup_worker = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_worker.start()

    def _cleanup_loop(self):
        """Persistent background worker that safely cleans hardware input and persists logs without blocking user input."""
        while True:
            self._cleanup_trigger.wait()
            self._cleanup_trigger.clear()
            reason = self._last_yield_reason or "Human Input"
            try:
                emergency_cleanup()
            except Exception:
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
        Executes in microsecond time by immediately updating state flags and delegating
        I/O and key cleanup to the background worker.
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

        # Signal background worker to release held keys and flush logs to disk
        self._cleanup_trigger.set()

        return latency_ms

    def _is_bot_injecting(self) -> bool:
        """Determines if the active input was generated by the bot."""
        return state.injecting_key.locked()

    def _monitor_loop(self):
        """
        100Hz non-invasive hardware input monitor thread.
        Never intercepts OS message queues, never attaches to Explorer, and never causes system freezes.
        """
        VK_LBUTTON = 0x01
        VK_RBUTTON = 0x02
        VK_MBUTTON = 0x04
        VK_PAUSE   = 0x13
        VK_ESCAPE  = 0x1B
        VK_F8      = 0x77
        VK_CONTROL = 0x11
        VK_SHIFT   = 0x10

        pt = POINT()

        while self._running:
            time.sleep(0.01) # 10ms polling interval

            # 1. Emergency Stop: Ctrl+PAUSE, Shift+PAUSE, or Ctrl+F8
            ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
            shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
            f8_state = user32.GetAsyncKeyState(VK_F8)
            pause_state = user32.GetAsyncKeyState(VK_PAUSE)
            
            f8_just_pressed = (f8_state & 0x0001) != 0
            pause_just_pressed = (pause_state & 0x0001) != 0

            if (pause_just_pressed and (ctrl_down or shift_down)) or (f8_just_pressed and ctrl_down):
                log("[PriorityEngine] EMERGENCY STOP triggered via hotkey.")
                try:
                    from core.session_manager import session_mgr
                    session_mgr.terminate_session("Emergency Stop Hotkey")
                except Exception:
                    pass
                continue

            # 2. Dedicated Toggle Keys: [F8] or [PAUSE]
            if f8_just_pressed or pause_just_pressed:
                key_label = "[F8]" if f8_just_pressed else "[PAUSE]"
                if state.automation_active.is_set() and not state.is_stopped():
                    self.trigger_instant_yield(f"Dedicated Toggle Key {key_label} (Pause)")
                else:
                    try:
                        from core.session_manager import session_mgr
                        session_mgr.request_resume(f"Dedicated Toggle Key {key_label} (Resume)")
                    except Exception:
                        pass
                continue

            # 3. Double-tap [ESC]
            esc_state = user32.GetAsyncKeyState(VK_ESCAPE)
            if (esc_state & 0x0001) != 0 and state.automation_active.is_set():
                now = time.monotonic()
                if now - self.last_esc_time <= 0.8:
                    self.esc_tap_count += 1
                else:
                    self.esc_tap_count = 1
                self.last_esc_time = now

                if self.esc_tap_count >= 2:
                    self.esc_tap_count = 0
                    self.trigger_instant_yield("Double-tap [ESC]")
                continue

            # 4. Inactive automation: keep last mouse position updated with zero overhead
            if not state.automation_active.is_set():
                if user32.GetCursorPos(ctypes.byref(pt)):
                    self.last_mouse_pos = (pt.x, pt.y)
                continue

            # 5. Active automation: detect human physical mouse interaction
            if not self._is_bot_injecting():
                # Mouse button clicks
                if (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) or \
                   (user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000) or \
                   (user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000):
                    self.trigger_instant_yield("Hardware Mouse Click")
                    continue

                # Mouse displacement (> 25px)
                if user32.GetCursorPos(ctypes.byref(pt)):
                    cur_pos = (pt.x, pt.y)
                    if self.last_mouse_pos is not None:
                        dist = math.hypot(cur_pos[0] - self.last_mouse_pos[0], cur_pos[1] - self.last_mouse_pos[1])
                        if dist >= self.displacement_threshold:
                            self.trigger_instant_yield(f"Hardware Mouse Displacement ({dist:.1f}px > {self.displacement_threshold}px)")
                    self.last_mouse_pos = cur_pos
            else:
                if user32.GetCursorPos(ctypes.byref(pt)):
                    self.last_mouse_pos = (pt.x, pt.y)

    def start(self):
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        log("[PriorityEngine] Non-invasive hardware input priority monitor started.")

    def stop(self):
        self._running = False


# Global singleton instance
priority_engine = PriorityEngine(displacement_threshold=25.0)

def start_priority_engine():
    priority_engine.start()

def stop_priority_engine():
    priority_engine.stop()
