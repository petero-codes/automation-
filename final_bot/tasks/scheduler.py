import time
import random
from core import state
from core.logger import log
from core.input_driver import emergency_cleanup
from config.settings import TOTAL_RUNTIME, AUTO_LAUNCH_LOGGY

class Scheduler:
    def __init__(self, task_weights):
        self.task_weights = task_weights
        self._last_task = None

    def pick_next_task(self):
        pool = [t for t in self.task_weights if t is not self._last_task]
        weights = [self.task_weights[t] for t in pool]
        chosen = random.choices(pool, weights=weights, k=1)[0]
        self._last_task = chosen
        return chosen

    def run(self):
        state.clear_stop()
        log('Idle threshold reached. Starting automation. (Double-tap ESC to yield)')
        start_time = time.time()
        consecutive_errors = 0

        if AUTO_LAUNCH_LOGGY and not state.is_stopped():
            try:
                from core.loggy_manager import ensure_loggy_running
                ensure_loggy_running()
            except Exception as e:
                log(f"[Loggy3] Note: {e}")

        while not state.is_stopped():
            if time.time() - start_time > TOTAL_RUNTIME:
                log('10 hours elapsed. Stopping.')
                break

            task = self.pick_next_task()
            dur = random.randint(600, 900)
            log(f'Starting {task.__name__} for {dur//60}m {dur%60}s.')

            try:
                task(dur)
                consecutive_errors = 0
            except Exception as e:
                log(f'Error in {task.__name__}: {e}')
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    log('3 consecutive errors. Pausing 5 min...')
                    if state.stop_automation_event.wait(300):
                        break
                    consecutive_errors = 0
                else:
                    time.sleep(2.0)

            if state.is_stopped():
                break

            brk = random.randint(240, 300)
            log(f'Break: {brk//60}m {brk%60}s.')
            elapsed = 0.0
            while elapsed < brk:
                chunk = min(5.0, brk - elapsed)
                if state.stop_automation_event.wait(chunk):
                    break
                elapsed += chunk

        state.automation_active.clear()
        log('Automation ended. Monitoring for idle...')
