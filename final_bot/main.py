"""
Nextgen Autonomous Workforce Engine
Dedicated Desktop Automation Engine: Visual Studio Code & Microsoft Excel Only.
100% Offline execution, natural human cognitive pacing, hardware input emulation,
and <30ms non-maskable human priority (IRQ 0).
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

def monitor_idle(mode: str = "both"):
    """
    Main supervisory loop:
      - For fresh sessions: starts when idle threshold is reached or when [F8]/[PAUSE] is pressed.
      - When PAUSED by human interaction: waits STRICTLY for explicit user resume ([F8] or [PAUSE]).
        It NEVER auto-resumes after an idle timeout once paused.
    """
    log(f"[Nextgen Engine] Armed & Ready. Initial launch triggers after {IDLE_TIMEOUT}s idle or [F8]/[PAUSE].")
    log("[Nextgen Engine] Instant Yield Active: Move mouse (>25px), Click (L/R/M), [PAUSE], [F8], or Double-ESC.")

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

    while True:
        time.sleep(0.5)

        if not state.automation_active.is_set():
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
    run_environment_discovery(mode=args.mode)

    try:
        monitor_idle(mode=args.mode)
    except KeyboardInterrupt:
        log("[Nextgen Engine] Terminated cleanly by user via KeyboardInterrupt.")
        session_mgr.terminate_session("KeyboardInterrupt")
    except Exception as e:
        log(f"[Nextgen Engine] Unexpected crash / interrupted session: {e}")
        session_mgr.mark_interrupted(str(e))

if __name__ == '__main__':
    main()
