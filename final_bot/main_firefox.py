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
from core.killswitch import start_daemons, get_idle_time_ms
from config.settings import IDLE_TIMEOUT

from tasks.scheduler import Scheduler
import tasks.web_tasks as web_tasks
import tasks.system_tasks as sys_tasks

web_tasks.BROWSER_EXE = 'firefox'
web_tasks.BROWSER_TITLE = 'Mozilla Firefox'

TASK_WEIGHTS = {
    web_tasks.task_watch_shorts:      4,
    web_tasks.task_read_wiki:         3,
    web_tasks.task_browse_news:       3,
    web_tasks.task_browse_reddit:     3,
    web_tasks.task_browse_explore:    3,
    web_tasks.task_read_novel:        2,
    web_tasks.task_browse_github:     2,
    sys_tasks.task_type_essay:        1,
    sys_tasks.task_view_task_manager: 1,
}

def monitor_idle():
    log(f'Script ready. Waiting for {IDLE_TIMEOUT}s idle. Double-tap ESC to stop automation.')
    while True:
        time.sleep(0.5)
        if not state.automation_active.is_set():
            if get_idle_time_ms() >= IDLE_TIMEOUT * 1000:
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
    start_daemons()
    try:
        monitor_idle()
    except KeyboardInterrupt:
        log('Terminated manually.')
        emergency_cleanup()

if __name__ == '__main__':
    main()
