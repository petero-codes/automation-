"""
Nextgen Autonomous Workforce Engine
Dedicated Desktop Automation Engine: Visual Studio Code & Microsoft Excel Only.
100% Offline execution, natural human cognitive pacing, hardware input emulation,
and measured sub-millisecond human priority yield via Win32 low-level hooks.
"""

import os
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import threading
import time
import math

from core import state
from core.logger import log
from core.input_driver import init_driver
from core.priority_engine import start_priority_engine, get_idle_time_ms
from core.session_manager import session_mgr, SessionState
from config.settings import IDLE_TIMEOUT

from tasks.scheduler import Scheduler
from tasks.shared import (
    is_vscode_installed,
    get_vscode_executable,
    is_excel_installed,
    get_excel_executable,
)
from core.system_cleaner import purge_legacy_system_artifacts

# Dedicated Workloads: Strictly Visual Studio Code & Microsoft Excel
from tasks.engineering_workload import task_software_engineering
from tasks.financial_workload import task_financial_modeling

# Workload Pool: Exclusively VS Code & Excel
TASK_WEIGHTS = {
    task_software_engineering: 5,  # Software Engineering (VS Code, dynamic architectures, Git)
    task_financial_modeling:   5,  # Financial Modeling (Excel, 50-90 dynamic rows, live formulas)
}

def run_environment_discovery(mode: str = "both"):
    """Detects and logs offline productivity environments on host machine and purges legacy artifacts."""
    purge_legacy_system_artifacts()
    log("======================================================================")
    log("   NEXTGEN AUTONOMOUS WORKFORCE ENGINE - VS CODE & EXCEL ONLY        ")
    log("======================================================================")
    log(f"[Discovery] Execution Mode     : {mode.upper()}")

    # VS Code Detection
    has_vscode = is_vscode_installed()
    vscode_exe = get_vscode_executable()
    if has_vscode:
        log(f"[Discovery] Visual Studio Code : READY ({vscode_exe})")
    else:
        log("[Discovery] Visual Studio Code : NOT DETECTED (will skip cleanly)")

    # Excel Detection
    has_excel = is_excel_installed()
    excel_exe = get_excel_executable()
    if has_excel:
        log(f"[Discovery] Microsoft Excel    : READY ({excel_exe})")
    else:
        log("[Discovery] Microsoft Excel    : NOT DETECTED (will skip cleanly)")

    log("[Discovery] Network Mode       : 100% Offline (Zero external network calls)")
    log("======================================================================")

def disable_quickedit():
    """Disables QuickEdit mode in Windows Console so clicking terminal never halts the process."""
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        hStdin = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE
        mode = wintypes.DWORD()
        if kernel32.GetConsoleMode(hStdin, ctypes.byref(mode)):
            ENABLE_QUICK_EDIT_MODE = 0x0040
            ENABLE_EXTENDED_FLAGS = 0x0080
            new_mode = (mode.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS
            kernel32.SetConsoleMode(hStdin, new_mode)
    except Exception:
        pass

def run_countdown(seconds: int, label: str = "Automation starting in", cancellable: bool = True) -> bool:
    """
    Executes a visible second-by-second countdown on the terminal.
    Allows user to abort by moving mouse or pressing a key.
    Returns True if finished, False if interrupted by human.
    """
    if os.environ.get("SKIP_COUNTDOWN") == "1":
        return True

    if cancellable and state.is_stopped():
        log(">>> Countdown aborted. HUMAN HAS CONTROL. <<<")
        return False

    try:
        from core.priority_engine import priority_engine
        priority_engine.activate_grace_period(1.0)
    except Exception:
        pass

    log("======================================================================")
    log(f"[Countdown] {label} {seconds} seconds... (Release mouse and keyboard)")
    log("======================================================================")

    start_pos = None
    try:
        from core.human_physics import get_mouse_pos
        start_pos = get_mouse_pos()
    except Exception:
        pass

    for sec in range(seconds, 0, -1):
        log(f"[Countdown] {sec}...")
        for _ in range(10):
            if state.is_stopped():
                log(">>> Countdown aborted. HUMAN HAS CONTROL. <<<")
                return False
            if cancellable and start_pos is not None:
                try:
                    cur_pos = get_mouse_pos()
                    if math.hypot(cur_pos[0] - start_pos[0], cur_pos[1] - start_pos[1]) > 50.0:
                        log("======================================================================")
                        log(">>> HUMAN HAS CONTROL <<<")
                        log("[Countdown] Human movement detected. Automation cancelled.")
                        log("[SessionManager] Press ENTER in this terminal, [F8]/[F9]/[F10], or pause hands-off to resume.")
                        log("======================================================================")
                        try:
                            session_mgr.mark_paused("Human Movement during Countdown")
                        except Exception:
                            pass
                        return False
                except Exception:
                    pass
            time.sleep(0.1)

    return True

def monitor_idle(mode: str = "both", start_now: bool = False):
    """
    Main supervisory loop:
      - When an interrupted session exists: blocks execution until recovery decision is made.
      - For fresh sessions: starts when idle threshold is reached, [F8]/[PAUSE] is pressed, or --now flag passed.
      - When PAUSED by human interaction: waits STRICTLY for explicit user resume ([F8] or [PAUSE]).
        It NEVER auto-resumes after an idle timeout once paused.
      - When TERMINATED: exits supervisor loop cleanly.
    """
    log(f"[Nextgen Engine] Armed & Ready. Initial launch triggers after {IDLE_TIMEOUT}s idle or [F8]/[Fn+F8]/[F9]/[F10]/[PAUSE].")
    log("[Nextgen Engine] Instant Yield Active: Move mouse (>60px), Click (L/R/M), [PAUSE], [F8], [F9], [F10], or Double-ESC.")
    log("[Nextgen Engine] Emergency Stop: [Ctrl+Pause], [Shift+Pause], [Ctrl+F8], [Ctrl+F9], [Ctrl+F10], or [Ctrl+C] in console.")
    log(f"[Nextgen Engine] Quick Resume: Press ENTER in this terminal, [F8]/[Fn+F8]/[F9]/[F10], or pause hands-off for {IDLE_TIMEOUT}s (2 minutes) to auto-resume.")

    disable_quickedit()

    # Filter task weights based on selected mode
    filtered_weights = {}
    if mode in ("vscode", "both"):
        filtered_weights[task_software_engineering] = TASK_WEIGHTS[task_software_engineering]
    if mode in ("excel", "both"):
        filtered_weights[task_financial_modeling] = TASK_WEIGHTS[task_financial_modeling]

    sched = Scheduler(filtered_weights, mode=mode)
    if not sched.task_weights:
        log(f"[Nextgen Engine] Error: No supported applications detected for mode '{mode}'. Halting.")
        return

    first_start_done = False
    worker_thread: Optional[threading.Thread] = None
    last_idle_report = 0.0

    if start_now:
        log("[Nextgen Engine] Immediate execution mode requested (--now).")
        state.clear_stop()
        try:
            from core.priority_engine import priority_engine
            priority_engine.activate_grace_period(2.5)
        except Exception:
            pass
        if run_countdown(5, label="Starting workforce engine in", cancellable=True):
            log("======================================================================")
            log(">>> BOT TAKING CONTROL (Hands off mouse & keyboard) <<<")
            log("======================================================================")
            try:
                from core.priority_engine import priority_engine
                priority_engine.activate_grace_period(2.5)
            except Exception:
                pass
            first_start_done = True
            session_mgr.mark_active()
            worker_thread = threading.Thread(target=sched.run, daemon=True)
            worker_thread.start()
        else:
            log(">>> Launch cancelled by user. HUMAN HAS CONTROL. Press ENTER or [F8]/[F9] to start. <<<")

    try:
        import msvcrt
        has_msvcrt = True
    except ImportError:
        has_msvcrt = False

    while True:
        time.sleep(0.2)

        # Clean exit when session is terminated
        if session_mgr.is_terminated():
            log("[Nextgen Engine] Session terminated. Exiting supervisor loop.")
            break

        # Check console keyboard input (non-blocking)
        if has_msvcrt and msvcrt.kbhit():
            try:
                ch = msvcrt.getch()
                if ch in (b'\r', b'\n', b' ', b'r', b'R'):
                    if session_mgr.is_paused() or (not first_start_done and not state.automation_active.is_set()):
                        log("[Nextgen Engine] Console input detected (ENTER/SPACE). Triggering explicit resume...")
                        session_mgr.request_resume("Console Key (ENTER/SPACE)")
                elif ch in (b'q', b'Q', b'\x03'):
                    log("[Nextgen Engine] Console exit key pressed. Terminating session.")
                    session_mgr.terminate_session("Console Exit Key")
                    break
            except Exception:
                pass

        worker_alive = worker_thread is not None and worker_thread.is_alive()

        if not worker_alive:
            # If session is interrupted from crash/unexpected exit, require recovery decision
            if session_mgr.is_interrupted():
                log("[Nextgen Engine] Session is INTERRUPTED. Awaiting explicit recovery (--recover or --fresh).")
                time.sleep(2.0)
                continue

            user_resume = state.is_resume_requested()

            # Rule: If paused, can resume via explicit hotkey / console Enter, OR after 2-minute (120s) hands-off inactivity!
            if session_mgr.is_paused() or user_resume:
                idle_sec = get_idle_time_ms() // 1000
                inactivity_auto_resume = session_mgr.is_paused() and (idle_sec >= IDLE_TIMEOUT)

                if user_resume or inactivity_auto_resume:
                    trigger_label = "User explicit resume" if user_resume else f"{IDLE_TIMEOUT}s (2-minute) human inactivity timeout (auto-resume)"
                    log(f"[Resume Controller] {trigger_label} detected.")
                    state.clear_resume()
                    state.clear_stop()
                    try:
                        from core.priority_engine import priority_engine
                        priority_engine.activate_grace_period(2.5)
                    except Exception:
                        pass

                    if run_countdown(3, label="Resuming workload from checkpoint in", cancellable=True):
                        log("======================================================================")
                        log(">>> BOT RESUMING AUTOMATION (Hands off mouse & keyboard) <<<")
                        log("======================================================================")
                        try:
                            from core.priority_engine import priority_engine
                            priority_engine.activate_grace_period(2.5)
                        except Exception:
                            pass
                        session_mgr.mark_active()
                        worker_thread = threading.Thread(target=sched.run, daemon=True)
                        worker_thread.start()
                    else:
                        log(">>> Resume cancelled. HUMAN HAS CONTROL. Press ENTER or pause hands-off to resume. <<<")
                continue

            # Fresh session before first start: can start on idle timeout or explicit toggle
            if not first_start_done:
                idle_sec = get_idle_time_ms() // 1000
                remaining = max(0, IDLE_TIMEOUT - idle_sec)

                now_t = time.time()
                if now_t - last_idle_report >= 10.0 and remaining > 0:
                    last_idle_report = now_t
                    log(f"[Idle Countdown] System idle: {idle_sec}s / {IDLE_TIMEOUT}s ({remaining}s remaining until automation) | Press ENTER to start immediately")

                inactivity_reached = idle_sec >= IDLE_TIMEOUT
                if user_resume or inactivity_reached:
                    state.clear_resume()
                    state.clear_stop()
                    if user_resume:
                        log("[Nextgen Engine] User started automation via dedicated toggle / console key.")
                    else:
                        log(f"[Nextgen Engine] {IDLE_TIMEOUT}s initial inactivity reached. Launching automation...")

                    try:
                        from core.priority_engine import priority_engine
                        priority_engine.activate_grace_period(2.5)
                    except Exception:
                        pass

                    if run_countdown(3, label="Launching workload in", cancellable=True):
                        log("======================================================================")
                        log(">>> BOT TAKING CONTROL (Hands off mouse & keyboard) <<<")
                        log("======================================================================")
                        try:
                            from core.priority_engine import priority_engine
                            priority_engine.activate_grace_period(2.5)
                        except Exception:
                            pass
                        first_start_done = True
                        session_mgr.mark_active()
                        worker_thread = threading.Thread(target=sched.run, daemon=True)
                        worker_thread.start()
                    else:
                        log(">>> Launch cancelled by user. HUMAN HAS CONTROL. <<<")

from core.window_manager import bind_thread_to_interactive_desktop

def parse_args():
    parser = argparse.ArgumentParser(description="Nextgen Autonomous Workforce Engine (VS Code & Excel)")
    parser.add_argument(
        "--mode",
        choices=["vscode", "excel", "both"],
        default=None,
        help="Target application mode: vscode, excel, or both (default: both)"
    )
    parser.add_argument(
        "--coding",
        action="store_true",
        help="Launch Visual Studio Code software engineering workload"
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Launch Microsoft Excel financial modeling workload"
    )
    parser.add_argument(
        "--workday",
        action="store_true",
        help="Launch unified workday lottery (both VS Code & Excel)"
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help="Explicitly recover an interrupted session from a crash/unexpected exit"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Discard any interrupted session and start fresh"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Start automation immediately without waiting for the idle timeout"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for human inactivity threshold before starting automation"
    )
    args = parser.parse_args()

    # Map flags to mode
    if args.coding:
        args.mode = "vscode"
    elif args.excel:
        args.mode = "excel"
    elif args.workday:
        args.mode = "both"
    elif args.mode is None:
        args.mode = "both"

    return args

def main():
    args = parse_args()
    bind_thread_to_interactive_desktop()
    init_driver()
    start_priority_engine()

    recovery_decision = None
    if args.recover:
        recovery_decision = "recover"
    elif args.fresh:
        recovery_decision = "discard"

    session_mgr.start_session(recovery_decision=recovery_decision)

    # If interrupted session exists and no CLI decision was provided, prompt if interactive
    if session_mgr.is_interrupted() and recovery_decision is None:
        if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            try:
                choice = input("[SessionManager] Interrupted session detected. Recover and resume? [Y/n]: ").strip().lower()
                if choice in ("", "y", "yes"):
                    session_mgr.recover_interrupted_session()
                else:
                    session_mgr.discard_interrupted_session()
            except Exception:
                pass
        else:
            log("[SessionManager] Interrupted session detected from crash or shutdown.")
            log("[SessionManager] Launch with '--recover' to restore checkpoint, or '--fresh' to start new session.")
            return

    run_environment_discovery(mode=args.mode)

    try:
        monitor_idle(mode=args.mode, start_now=args.now)
    except KeyboardInterrupt:
        log("[Nextgen Engine] Terminated cleanly by user via KeyboardInterrupt.")
        session_mgr.terminate_session("KeyboardInterrupt")
    except Exception as e:
        log(f"[Nextgen Engine] Unexpected crash / interrupted session: {e}")
        session_mgr.mark_interrupted(str(e))

if __name__ == '__main__':
    main()
