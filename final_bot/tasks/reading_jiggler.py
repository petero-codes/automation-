import time
import random
from core import state
from core.logger import log
from core.input_driver import safe_scroll

def execute_reading_micro_scroll() -> bool:
    """
    Executes a zero-drift subtle reading micro-scroll cycle:
      1. Symmetrically scrolls down 1–3 notches.
      2. Dwells naturally for 1.5s–3.0s simulating human reading pause.
      3. Scrolls back UP by the exact same amount.
      4. Cursor displacement = 0px (viewport returned to exact original position).
      5. Emits genuine Ring-0 hardware RawInput packets, resetting OS sleep and away timers.
    """
    if state.is_stopped():
        return False

    notches = random.randint(1, 3)
    log(f"[Reading Jiggler] Zero-drift reading micro-scroll started: {notches} notches.")

    # 1. Subtle Downward Micro-Scroll
    for _ in range(notches):
        if state.is_stopped():
            return False
        safe_scroll('down')
        time.sleep(random.uniform(0.08, 0.16))

    # 2. Natural Reading Dwell (1.5s – 3.0s)
    dwell_duration = random.uniform(1.5, 3.0)
    if state.stop_automation_event.wait(dwell_duration):
        # Human interrupted during dwell; attempt symmetric recovery
        for _ in range(notches):
            safe_scroll('up')
        return False

    # 3. Exact Counter-Scroll Up (Zero-Drift Return)
    for _ in range(notches):
        if state.is_stopped():
            safe_scroll('up')
            return False
        safe_scroll('up')
        time.sleep(random.uniform(0.08, 0.16))

    log(f"[Reading Jiggler] Symmetrical recovery complete: 0px drift, viewport preserved.")
    return True

def task_reading_mode(duration: int):
    """
    Continuous Reading Mode task. Runs periodic zero-drift micro-scrolls
    spaced by cognitive pauses throughout the allocated task duration.
    """
    log(f"[Reading Mode] Active document/code reading mode initiated for {duration}s.")
    start = time.time()

    while time.time() - start < duration and not state.is_stopped():
        success = execute_reading_micro_scroll()
        if not success or state.is_stopped():
            break

        # Natural reading interval between subtle scrolls (12s to 35s)
        interval = random.uniform(12.0, 35.0)
        remaining = duration - (time.time() - start)
        sleep_chunk = min(interval, max(0.5, remaining))
        
        if state.stop_automation_event.wait(sleep_chunk):
            break

    log("[Reading Mode] Session concluded.")
