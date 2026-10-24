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
from core.checkpoint_manager import checkpoint_mgr as global_checkpoint_mgr

class SessionState(Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    INTERRUPTED = "INTERRUPTED"
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
    Session Lifecycle Manager:
      - Distinguishes paused, active, interrupted (crash/shutdown), and terminated sessions.
      - Intercepts Windows console close events (SetConsoleCtrlHandler).
      - On permanent termination (closing console / exit): invalidates checkpoint so fresh launch starts new session.
      - On pause (human intervention): preserves exact code line / Excel cell checkpoint for explicit user resume.
      - On unexpected crash/interruption: marks session INTERRUPTED and requires a clear recovery decision.
      - Enforces that terminated sessions cannot be resumed automatically.
    """
    def __init__(self, checkpoint_manager=None):
        self.checkpoint_mgr = checkpoint_manager or global_checkpoint_mgr
        self.state = SessionState.INITIALIZING
        self._handler_ref = PHANDLER_ROUTINE(self._console_ctrl_handler)
        self._handler_registered = False

    def register_console_handler(self):
        """Binds to Windows console events to catch window close actions."""
        if not self._handler_registered:
            try:
                ctypes.windll.kernel32.SetConsoleCtrlHandler(self._handler_ref, True)
                self._handler_registered = True
                log("[SessionManager] Windows console control handler registered.")
            except Exception as e:
                log(f"[SessionManager] Note: Could not register console handler: {e}")

    def _console_ctrl_handler(self, dwCtrlType: int) -> int:
        if dwCtrlType in (CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
            event_name = "User Logoff" if dwCtrlType == CTRL_LOGOFF_EVENT else "System Shutdown"
            log(f"[SessionManager] OS-level session interruption signaled: {event_name}")
            self.mark_interrupted(f"OS Interruption ({event_name})")
            return 1
        elif dwCtrlType in (CTRL_CLOSE_EVENT, CTRL_C_EVENT, CTRL_BREAK_EVENT):
            event_names = {
                CTRL_C_EVENT: "Ctrl+C",
                CTRL_BREAK_EVENT: "Ctrl+Break",
                CTRL_CLOSE_EVENT: "Console Window Closed (X)",
            }
            event_str = event_names.get(dwCtrlType, f"Event {dwCtrlType}")
            log(f"[SessionManager] Explicit user termination signaled: {event_str}")
            self.terminate_session(f"Explicit Termination ({event_str})")
            return 1
        return 0

    def start_session(self, recovery_decision: Optional[str] = None):
        """
        Initializes a session. Detects if resuming from a paused checkpoint,
        recovering an interrupted crash session, or starting fresh.
        """
        self.register_console_handler()
        cp = self.checkpoint_mgr.load_checkpoint()

        if cp:
            status = cp.get("status") or cp.get("payload", {}).get("status")

            if status == "TERMINATED":
                self.checkpoint_mgr.clear_checkpoint()
                self.state = SessionState.ACTIVE
                log("[SessionManager] Previous session was terminated. Starting fresh session.")

            elif status == "INTERRUPTED":
                self.state = SessionState.INTERRUPTED
                if recovery_decision == "recover":
                    self.state = SessionState.PAUSED
                    # Update status in checkpoint to PAUSED
                    workload = cp.get("workload", "VS_CODE")
                    payload = cp.get("payload", {})
                    payload["status"] = "PAUSED"
                    self.checkpoint_mgr.save_checkpoint(workload, payload, status="PAUSED")
                    log(f"[SessionManager] User selected recovery for interrupted session ({workload}). Checkpoint armed for explicit resume.")
                elif recovery_decision == "discard":
                    self.checkpoint_mgr.clear_checkpoint()
                    self.state = SessionState.ACTIVE
                    log("[SessionManager] Interrupted session discarded. Starting fresh session.")
                else:
                    log(f"[SessionManager] Interrupted session detected ({cp.get('workload')}). Recovery decision required (recover or discard).")

            elif status == "PAUSED":
                self.state = SessionState.PAUSED
                workload = cp.get("workload")
                log(f"[SessionManager] Found existing paused checkpoint for {workload}. Ready to resume on explicit user request.")

            else:
                self.state = SessionState.ACTIVE
                self.checkpoint_mgr.clear_checkpoint()
                log("[SessionManager] Fresh workforce session initialized.")
        else:
            self.state = SessionState.ACTIVE
            self.checkpoint_mgr.clear_checkpoint()
            log("[SessionManager] Fresh workforce session initialized.")

    def mark_active(self):
        self.state = SessionState.ACTIVE
        state.clear_stop()
        state.automation_active.set()

    def mark_paused(self, reason: str):
        self.state = SessionState.PAUSED
        state.request_stop()
        state.automation_active.clear()
        log(f"[SessionManager] Session PAUSED: {reason}")
        log("[SessionManager] Checkpoint preserved. Press [F8], [Fn+F8], [F9], or press ENTER in this terminal to resume.")

    def mark_interrupted(self, reason: str):
        """Flags session as interrupted due to crash or unexpected exit."""
        self.state = SessionState.INTERRUPTED
        state.request_stop()
        state.automation_active.clear()
        cp = self.checkpoint_mgr.load_checkpoint()
        if cp:
            workload = cp.get("workload", "UNKNOWN")
            payload = cp.get("payload", {})
            payload["status"] = "INTERRUPTED"
            payload["interrupted_reason"] = reason
            self.checkpoint_mgr.save_checkpoint(workload, payload, status="INTERRUPTED")
        log(f"[SessionManager] Session marked INTERRUPTED ({reason}).")

    def request_resume(self, trigger: str) -> bool:
        """
        Processes an explicit resume request.
        Terminated sessions cannot be resumed.
        Interrupted sessions require explicit recovery first.
        """
        if self.state == SessionState.TERMINATED:
            log(f"[SessionManager] Resume rejected ({trigger}): Terminated sessions cannot be resumed.")
            return False

        if self.state == SessionState.INTERRUPTED:
            log(f"[SessionManager] Resume rejected ({trigger}): Session was interrupted. Explicit recovery decision required.")
            return False

        log(f"[SessionManager] Resume granted via {trigger}.")
        state.clear_stop()
        state.request_resume()
        self.mark_active()
        return True

    def recover_interrupted_session(self) -> bool:
        """Explicitly recovers an interrupted crash session into PAUSED state for resumption."""
        cp = self.checkpoint_mgr.load_checkpoint()
        if not cp:
            log("[SessionManager] No checkpoint to recover.")
            return False

        workload = cp.get("workload", "VS_CODE")
        payload = cp.get("payload", {})
        payload["status"] = "PAUSED"
        self.checkpoint_mgr.save_checkpoint(workload, payload, status="PAUSED")
        self.state = SessionState.PAUSED
        log(f"[SessionManager] Interrupted session ({workload}) recovered to PAUSED state.")
        return True

    def discard_interrupted_session(self):
        """Discards an interrupted session checkpoint and starts fresh."""
        self.checkpoint_mgr.clear_checkpoint()
        self.state = SessionState.ACTIVE
        log("[SessionManager] Interrupted session discarded.")

    def terminate_session(self, reason: str):
        """Cleanly terminates the session and invalidates checkpoint so next launch starts fresh."""
        self.state = SessionState.TERMINATED
        state.request_stop()
        state.automation_active.clear()
        try:
            emergency_cleanup()
        except Exception:
            pass
        self.checkpoint_mgr.clear_checkpoint()
        log(f"[SessionManager] Session terminated ({reason}). Checkpoint invalidated. Fresh launch will start new session.")

    def is_paused(self) -> bool:
        return self.state == SessionState.PAUSED

    def is_active(self) -> bool:
        return self.state == SessionState.ACTIVE

    def is_interrupted(self) -> bool:
        return self.state == SessionState.INTERRUPTED

    def is_terminated(self) -> bool:
        return self.state == SessionState.TERMINATED

session_mgr = SessionManager()
