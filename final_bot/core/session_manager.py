import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

from core.logger import log
from core import state
from core.input_driver import emergency_cleanup
from core.checkpoint_manager import checkpoint_mgr

class SessionState(Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"

# Windows Console Control Handler definitions
PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6

class SessionManager:
    """
    Session Manager:
      - Distinguishes paused sessions from permanently terminated sessions.
      - Intercepts Windows console close events (SetConsoleCtrlHandler).
      - On permanent termination (closing console / exit): purges checkpoints so fresh launch starts new session.
      - On pause (human intervention): preserves exact code line / Excel cell checkpoint.
      - Manages user-decided resume requests ([F8], [PAUSE], or inactivity timeout).
    """
    def __init__(self):
        self.state = SessionState.INITIALIZING
        self._handler_ref = PHANDLER_ROUTINE(self._console_ctrl_handler)
        self._handler_registered = False

    def register_console_handler(self):
        """Binds to Windows kernel console events to catch window close actions."""
        if not self._handler_registered:
            try:
                ctypes.windll.kernel32.SetConsoleCtrlHandler(self._handler_ref, True)
                self._handler_registered = True
                log("[SessionManager] Windows console control handler registered.")
            except Exception as e:
                log(f"[SessionManager] Note: Could not register console handler: {e}")

    def _console_ctrl_handler(self, dwCtrlType: int) -> int:
        event_names = {
            CTRL_C_EVENT: "Ctrl+C",
            CTRL_BREAK_EVENT: "Ctrl+Break",
            CTRL_CLOSE_EVENT: "Console Window Closed (X)",
            CTRL_LOGOFF_EVENT: "User Logoff",
            CTRL_SHUTDOWN_EVENT: "System Shutdown",
        }
        event_str = event_names.get(dwCtrlType, f"Event {dwCtrlType}")
        log(f"[SessionManager] Permanent session termination signaled: {event_str}")
        self.terminate_session(f"Console Termination ({event_str})")
        return 1

    def start_session(self):
        """Initializes a session; detects if resuming from a paused checkpoint or starting fresh."""
        self.register_console_handler()
        cp = checkpoint_mgr.load_checkpoint()
        if cp and cp.get("payload", {}).get("status") == "PAUSED":
            self.state = SessionState.PAUSED
            workload = cp.get("workload")
            log(f"[SessionManager] Found existing paused checkpoint for {workload}. Ready to resume exact position.")
        else:
            self.state = SessionState.ACTIVE
            checkpoint_mgr.clear_checkpoint()
            log("[SessionManager] Fresh workforce session initialized.")

    def mark_active(self):
        self.state = SessionState.ACTIVE
        state.clear_stop()
        state.clear_resume()
        state.automation_active.set()

    def mark_paused(self, reason: str):
        self.state = SessionState.PAUSED
        state.request_stop()
        state.automation_active.clear()
        log(f"[SessionManager] Session PAUSED: {reason}")
        log("[SessionManager] Checkpoint preserved. Press [F8] or [PAUSE] to resume, or wait for inactivity timeout.")

    def request_resume(self, trigger: str):
        if self.state == SessionState.PAUSED or not state.automation_active.is_set():
            log(f"[SessionManager] Resume requested via {trigger}.")
            state.clear_stop()
            state.request_resume()
            self.mark_active()

    def terminate_session(self, reason: str):
        """Cleanly terminates the session and purges checkpoint so next launch starts fresh."""
        self.state = SessionState.TERMINATED
        state.request_stop()
        state.automation_active.clear()
        try:
            emergency_cleanup()
        except Exception:
            pass
        checkpoint_mgr.clear_checkpoint()
        log(f"[SessionManager] Session terminated ({reason}). Checkpoint purged. Fresh launch will start new session.")

    def is_paused(self) -> bool:
        return self.state == SessionState.PAUSED

    def is_active(self) -> bool:
        return self.state == SessionState.ACTIVE

    def is_terminated(self) -> bool:
        return self.state == SessionState.TERMINATED

session_mgr = SessionManager()
