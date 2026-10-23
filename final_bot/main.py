"""
Nextgen Autonomous Workforce Engine
Dedicated Offline Productivity Engine: Visual Studio Code & Microsoft Excel.
100% Offline execution, natural human cognitive pacing, Ring-0 hardware input,
and <30ms non-maskable human priority (IRQ 0).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import ctypes
import threading
import time

from core import state
from core.logger import log
from core.input_driver import init_driver, emergency_cleanup
from core.priority_engine import start_priority_engine, get_idle_time_ms
from core.session_manager import session_mgr
from config.settings import IDLE_TIMEOUT

from tasks.scheduler import Scheduler
from tasks.shared import (
    is_vscode_installed,
    get_vscode_executable,
    is_excel_installed,
    get_excel_executable,
)

# Dedicated Offline Workloads
from tasks.engineering_workload import task_software_engineering
from tasks.financial_workload import task_financial_modeling
from tasks.reading_jiggler import execute_reading_micro_scroll

# Workload Matrix: Strictly Visual Studio Code & Microsoft Excel
TASK_WEIGHTS = {
    task_software_engineering: 5,  # Software Engineering (VS Code, dynamic architectures, Git)
    task_financial_modeling:   5,  # Financial Modeling (Excel, 50-90 dynamic rows, live formulas)
}

def run_environment_discovery():
    """Detects and logs offline productivity environments on host machine."""
    log("======================================================================")
    log("   NEXTGEN AUTONOMOUS WORKFORCE ENGINE - OFFLINE CODING & EXCEL      ")
    log("======================================================================")

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

    log(f"[Discovery] Active Workloads   : Coding (VS Code) & Financial Modeling (Excel)")
    log(f"[Discovery] Network Mode       : 100% Offline (Zero external network calls)")
    log("======================================================================")

def monitor_idle():
    session_mgr.start_session()
    log(f"[Nextgen Engine] Armed & Ready. Awaiting {IDLE_TIMEOUT}s unbroken idle or [F8]/[PAUSE] to resume.")
    log(f"[Nextgen Engine] Instant Yield Active: Move mouse (>25px), Click (L/R/M), [PAUSE], [F8], or Double-ESC.")

    while True:
        time.sleep(0.5)
        # When automation is not active, monitor for unbroken idle OR user resume request
        if not state.automation_active.is_set():
            user_resume = state.is_resume_requested()
            inactivity_reached = get_idle_time_ms() >= IDLE_TIMEOUT * 1000

            if user_resume or inactivity_reached:
                state.clear_resume()
                if not user_resume:
                    log("[Nextgen Engine] 120s inactivity reached. Emitting Ring-0 hardware reading pulse...")
                    execute_reading_micro_scroll()
                else:
                    log("[Nextgen Engine] User triggered instant resume via dedicated toggle.")

                # Transition into Autonomous Workforce Cycle
                session_mgr.mark_active()
                sched = Scheduler(TASK_WEIGHTS)
                threading.Thread(target=sched.run, daemon=True).start()

def _bind_to_interactive_desktop():
    GENERIC_ALL = 0x10000000
    desk = ctypes.windll.user32.OpenInputDesktop(0, False, GENERIC_ALL)
    if desk:
        ctypes.windll.user32.SetThreadDesktop(desk)
        ctypes.windll.user32.CloseDesktop(desk)

def main():
    _bind_to_interactive_desktop()
    init_driver()
    start_priority_engine()
    run_environment_discovery()
    try:
        monitor_idle()
    except KeyboardInterrupt:
        log('[Nextgen Engine] Terminated manually by user.')
        session_mgr.terminate_session("KeyboardInterrupt")
    except Exception as e:
        log(f'[Nextgen Engine] Terminated with exception: {e}')
        session_mgr.terminate_session(str(e))

if __name__ == '__main__':
    main()
