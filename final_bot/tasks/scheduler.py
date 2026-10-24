import time
import random
from typing import Dict, Any, Callable, Optional
from core import state
from core.logger import log
from core.input_driver import emergency_cleanup
from core.checkpoint_manager import checkpoint_mgr
from config.settings import TOTAL_RUNTIME
from tasks.shared import is_vscode_installed, is_excel_installed

def is_task_runnable(task: Callable) -> bool:
    """Verifies whether the target application for a workload is installed."""
    name = getattr(task, '__name__', str(task)).lower()
    if 'software_engineering' in name or 'vscode' in name:
        return is_vscode_installed()
    if 'financial' in name or 'excel' in name:
        return is_excel_installed()
    return False

def filter_runnable_tasks(task_weights: Dict[Callable, int], mode: str = "both") -> Dict[Callable, int]:
    """
    Prunes workloads based on execution mode and application availability.
    Supported modes: 'vscode', 'excel', 'both'.
    """
    runnable = {}
    mode = mode.lower()

    for task, weight in task_weights.items():
        name = getattr(task, '__name__', str(task)).lower()

        # Check mode match
        if mode == "vscode" and not ('software_engineering' in name or 'vscode' in name):
            continue
        if mode == "excel" and not ('financial' in name or 'excel' in name):
            continue

        # Check installation
        if is_task_runnable(task):
            runnable[task] = weight
        else:
            log(f"[Scheduler] Skipping unavailable workload: {name} (application not installed)")

    if not runnable:
        log(f"[Scheduler] No runnable workloads available for mode '{mode}'. Ensure required application is installed.")

    return runnable

class Scheduler:
    """
    Dedicated Task Scheduler for Visual Studio Code & Microsoft Excel workloads.
    Handles user pause/yield, fine-grained checkpoint resumption, and safe task cycling.
    """
    def __init__(self, task_weights: Dict[Callable, int], mode: str = "both"):
        self.mode = mode
        self.raw_weights = task_weights
        self.task_weights = filter_runnable_tasks(task_weights, mode=mode)
        self._last_task = None

    def pick_next_task(self) -> Optional[Callable]:
        if not self.task_weights:
            return None
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
        log("[Scheduler] Autonomous Workforce cycle active.")
        start_time = time.time()
        consecutive_errors = 0

        # Check for existing valid checkpoint
        active_checkpoint = checkpoint_mgr.load_checkpoint()
        if active_checkpoint and active_checkpoint.get("status") == "PAUSED":
            log(f"[Scheduler] Resuming session from checkpoint: {active_checkpoint.get('workload')}")

        while not state.is_stopped():
            if time.time() - start_time > TOTAL_RUNTIME:
                log("[Scheduler] Maximum scheduled runtime elapsed. Stopping.")
                break

            task = self.pick_next_task()
            if task is None:
                log("[Scheduler] No runnable tasks detected. Pausing automation.")
                break

            dur = random.randint(600, 900)  # 10 to 15 minute task sessions
            task_name = getattr(task, '__name__', str(task))
            log(f"[Scheduler] Starting {task_name} for {dur//60}m {dur%60}s.")

            try:
                result = task(dur)
                consecutive_errors = 0
                if result is False:
                    if state.is_stopped():
                        log(f"[Scheduler] Workload {task_name} suspended due to human interaction.")
                        break
                    else:
                        log(f"[Scheduler] Workload {task_name} skipped or completed early.")
                        continue
                else:
                    # Task completed successfully end-to-end
                    checkpoint_mgr.clear_checkpoint()
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
        log("[Scheduler] Workforce engine suspended. Awaiting explicit user resume...")
