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

def monitor_idle(mode: str = "both", start_now: bool = False):
    """
    Main supervisory loop:
      - When an interrupted session exists: blocks execution until recovery decision is made.
      - For fresh sessions: starts when idle threshold is reached, [F8]/[PAUSE] is pressed, or --now flag passed.
      - When PAUSED by human interaction: waits STRICTLY for explicit user resume ([F8] or [PAUSE]).
        It NEVER auto-resumes after an idle timeout once paused.
      - When TERMINATED: exits supervisor loop cleanly.
    """
    log(f"[Nextgen Engine] Armed & Ready. Initial launch triggers after {IDLE_TIMEOUT}s idle or [F8]/[PAUSE].")
    log("[Nextgen Engine] Instant Yield Active: Move mouse (>25px), Click (L/R/M), [PAUSE], [F8], or Double-ESC.")
    log("[Nextgen Engine] Emergency Stop: [Ctrl+Pause], [Shift+Pause], [Ctrl+F8], or [Ctrl+C] in console.")

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

    if start_now:
        log("[Nextgen Engine] Immediate execution requested (--now). Launching workload directly...")
        first_start_done = True
        session_mgr.mark_active()
        threading.Thread(target=sched.run, daemon=True).start()

    while True:
        time.sleep(0.5)

        # Clean exit when session is terminated
        if session_mgr.is_terminated():
            log("[Nextgen Engine] Session terminated. Exiting supervisor loop.")
            break

        if not state.automation_active.is_set():
            # If session is interrupted from crash/unexpected exit, require recovery decision
            if session_mgr.is_interrupted():
                log("[Nextgen Engine] Session is INTERRUPTED. Awaiting explicit recovery (--recover or --fresh).")
                time.sleep(2.0)
                continue

            user_resume = state.is_resume_requested()

            # Rule: If paused, automation does NOT resume until explicitly requested
            if session_mgr.is_paused():
                if user_resume:
                    state.clear_resume()
                    log("[Nextgen Engine] User triggered explicit resume via dedicated toggle ([F8]/[PAUSE]).")
                    session_mgr.mark_active()
                    threading.Thread(target=sched.run, daemon=True).start()
                continue

            # Fresh session before first start: can start on idle timeout or explicit toggle
            if not first_start_done:
                inactivity_reached = get_idle_time_ms() >= IDLE_TIMEOUT * 1000
                if user_resume or inactivity_reached:
                    state.clear_resume()
                    if user_resume:
                        log("[Nextgen Engine] User started automation via dedicated toggle.")
                    else:
                        log(f"[Nextgen Engine] {IDLE_TIMEOUT}s initial inactivity reached. Starting workforce...")

                    first_start_done = True
                    session_mgr.mark_active()
                    threading.Thread(target=sched.run, daemon=True).start()

from core.window_manager import bind_thread_to_interactive_desktop

def parse_args():
    parser = argparse.ArgumentParser(description="Nextgen Autonomous Workforce Engine (VS Code & Excel)")
    parser.add_argument(
        "--mode",
        choices=["vscode", "excel", "both"],
        default="both",
        help="Target application mode: vscode, excel, or both (default: both)"
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
    return parser.parse_args()

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
