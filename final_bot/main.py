"""
Nextgen Autonomous Workforce Engine
Mission-critical autonomous enterprise workforce platform for Windows 10/11.
Automatic hardware/software detection, dynamic workload rotation,
zero-drift reading micro-scroll, and <30ms non-maskable human priority (IRQ 0).
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
from config.settings import IDLE_TIMEOUT

from tasks.scheduler import Scheduler
import tasks.web_tasks as web_tasks
import tasks.system_tasks as sys_tasks
from tasks.shared import (
    detect_best_browser,
    get_installed_browsers,
    is_vscode_installed,
    get_vscode_executable,
    is_excel_installed,
    get_excel_executable,
)

# Mission-Critical Workloads
from tasks.engineering_workload import task_software_engineering
from tasks.financial_workload import task_financial_modeling
from tasks.research_workload import task_technical_research
from tasks.reading_jiggler import task_reading_mode, execute_reading_micro_scroll

def run_environment_discovery():
    """Detects and logs all installed software environments on host machine."""
    log("======================================================================")
    log("       NEXTGEN AUTONOMOUS WORKFORCE ENGINE - ENVIRONMENT DISCOVERY     ")
    log("======================================================================")

    # Browser Detection
    best_exe, best_title = detect_best_browser()
    installed_browsers = get_installed_browsers()
    web_tasks.BROWSER_EXE = best_exe
    web_tasks.BROWSER_TITLE = best_title
    browser_names = [b[1] for b in installed_browsers] if installed_browsers else [best_title]
    log(f"[Discovery] Installed Browsers : {', '.join(browser_names)}")
    log(f"[Discovery] Active Browser Target: {best_title} ({best_exe})")

    # VS Code Detection
    has_vscode = is_vscode_installed()
    vscode_exe = get_vscode_executable()
    log(f"[Discovery] Visual Studio Code   : {'AVAILABLE (' + str(vscode_exe) + ')' if has_vscode else 'NOT INSTALLED (will skip cleanly)'}")

    # Excel Detection
    has_excel = is_excel_installed()
    excel_exe = get_excel_executable()
    log(f"[Discovery] Microsoft Excel      : {'AVAILABLE (' + str(excel_exe) + ')' if has_excel else 'NOT INSTALLED (will skip cleanly)'}")

    log("======================================================================")
    return best_exe, best_title

# Base Weighted Workload Matrix
TASK_WEIGHTS = {
    task_software_engineering:       5,  # Software Engineering (VS Code, dynamic architectures, Git)
    task_financial_modeling:          5,  # Financial Modeling (Excel, 50-90 dynamic rows, live formulas)
    task_technical_research:         4,  # Technical Exploration (220+ curated technical domains)
    task_reading_mode:               3,  # Zero-Drift Reading Mode (subtle scroll jiggler)
    sys_tasks.task_view_task_manager: 1,  # Diagnostic Review (Task Manager)
    sys_tasks.task_terminal_ops:      1,  # Systems Terminal Operations
}

def monitor_idle():
    log(f"[Nextgen Engine] Armed & Ready. Awaiting {IDLE_TIMEOUT}s unbroken idle.")
    log(f"[Nextgen Engine] Instant Yield Active: Move mouse (>25px), Click (L/R/M), [PAUSE], [F8], or Double-ESC.")

    while True:
        time.sleep(0.5)
        # When automation is not active, monitor for unbroken idle
        if not state.automation_active.is_set():
            if get_idle_time_ms() >= IDLE_TIMEOUT * 1000:
                log("[Nextgen Engine] 120s inactivity reached. Emitting Ring-0 hardware RawInput reading pulse...")
                execute_reading_micro_scroll()

                # Transition into Autonomous Workforce Cycle
                state.clear_stop()
                state.automation_active.set()
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
        log('[Nextgen Engine] Terminated manually.')
        emergency_cleanup()

if __name__ == '__main__':
    main()
