import time
import random
from typing import Dict, Any, Callable
from core import state
from core.logger import log
from core.input_driver import emergency_cleanup
from core.checkpoint_manager import checkpoint_mgr
from config.settings import TOTAL_RUNTIME, AUTO_LAUNCH_LOGGY
from tasks.shared import is_vscode_installed, is_excel_installed

def is_task_runnable(task: Callable) -> bool:
    """Verifies whether the target application for a workload is installed."""
    name = getattr(task, '__name__', str(task))
    if 'software_engineering' in name or 'vscode' in name:
        return is_vscode_installed()
    if 'financial' in name or 'excel' in name:
        return is_excel_installed()
    return True

def filter_runnable_tasks(task_weights: Dict[Callable, int]) -> Dict[Callable, int]:
    """Prunes workloads whose required applications are missing on the host machine."""
    runnable = {}
    for task, weight in task_weights.items():
        if is_task_runnable(task):
            runnable[task] = weight
        else:
            name = getattr(task, '__name__', str(task))
            log(f"[Scheduler] Skipping unavailable workload: {name} (application not installed)")

    if not runnable:
        log("[Scheduler] Neither VS Code nor Excel was detected. Please install Visual Studio Code or Microsoft Excel to run workloads.")
        from tasks.reading_jiggler import task_reading_mode
        runnable = {task_reading_mode: 1}

    return runnable

class Scheduler:
    """
    Enterprise Task Scheduler with Non-Maskable IRQ 0 yield handling,
    encrypted session resumability, and dynamic hardware/software workload selection.
    """
    def __init__(self, task_weights: Dict[Callable, int]):
        self.task_weights = filter_runnable_tasks(task_weights)
        self._last_task = None

    def pick_next_task(self):
        pool = [t for t in self.task_weights if t is not self._last_task]
        if not pool:
            pool = list(self.task_weights.keys())
        weights = [self.task_weights[t] for t in pool]
        chosen = random.choices(pool, weights=weights, k=1)[0]
        self._last_task = chosen
        return chosen

    def run(self):
        from core.window_manager import bind_thread_to_interactive_desktop
        bind_thread_to_interactive_desktop()
        state.clear_stop()
        log("[Scheduler] Inactivity threshold reached. Resuming Nextgen Autonomous Workforce Engine.")
        start_time = time.time()
        consecutive_errors = 0

        # Check for encrypted checkpoint resumability
        active_checkpoint = checkpoint_mgr.load_checkpoint()
        if active_checkpoint:
            log(f"[Scheduler] Resuming session from encrypted checkpoint: {active_checkpoint.get('workload')}")

        if AUTO_LAUNCH_LOGGY and not state.is_stopped():
            try:
                from core.loggy_manager import ensure_loggy_running
                ensure_loggy_running()
            except Exception as e:
                log(f"[Loggy3] Note: {e}")

        while not state.is_stopped():
            if time.time() - start_time > TOTAL_RUNTIME:
                log("[Scheduler] Maximum scheduled runtime elapsed. Stopping.")
                break

            task = self.pick_next_task()
            dur = random.randint(600, 900) # 10 to 15 minute task sessions
            task_name = getattr(task, '__name__', str(task))
            log(f"[Scheduler] Starting {task_name} for {dur//60}m {dur%60}s.")

            # Record checkpoint before task execution
            checkpoint_mgr.save_checkpoint(task_name, {"duration": dur, "start_time": time.time()})

            try:
                result = task(dur)
                consecutive_errors = 0
                checkpoint_mgr.clear_checkpoint()
                if result is False:
                    log(f"[Scheduler] Workload {task_name} skipped or yielded early. Advancing to next workload.")
                    continue
            except Exception as e:
                log(f"[Scheduler] Exception in {task_name}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    log("[Scheduler] 3 consecutive errors encountered. Pausing for 5 min...")
                    if state.stop_automation_event.wait(300):
                        break
                    consecutive_errors = 0
                else:
                    time.sleep(2.0)
                continue

            if state.is_stopped():
                log("[Scheduler] Human yield signal acknowledged. Checkpointed active state.")
                break

            # Natural inter-task cognitive break (3 to 5 minutes)
            break_sec = random.randint(180, 300)
            log(f"[Scheduler] Natural cognitive pause: {break_sec//60}m {break_sec%60}s.")
            elapsed = 0.0
            while elapsed < break_sec:
                chunk = min(5.0, break_sec - elapsed)
                if state.stop_automation_event.wait(chunk):
                    break
                elapsed += chunk

        state.automation_active.clear()
        log("[Scheduler] Workforce engine yielded. Awaiting unbroken human inactivity (120s)...")
