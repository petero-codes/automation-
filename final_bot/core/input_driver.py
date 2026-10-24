import time
import random
from core import state
from core.logger import log

def init_driver():
    try:
        import interception
        log("Initializing Interception driver...")
        interception.auto_capture_devices()
        log("Driver initialized successfully.")
    except Exception as e:
        log(f"Driver Init Error: {e}")

def safe_key_down(k):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            interception.key_down(k)
        except Exception as e:
            log(f"Driver error (key_down {k}): {e}")

def safe_key_up(k):
    with state.injecting_key:
        try:
            import interception
            interception.key_up(k)
        except Exception as e:
            log(f"Driver error (key_up {k}): {e}")

def safe_press(k):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            interception.press(k)
        except Exception as e:
            log(f"Driver error (press {k}): {e}")

def hotkey(*keys):
    if state.is_stopped(): return
    try:
        for k in keys:
            safe_key_down(k)
        time.sleep(random.uniform(0.04, 0.09))
        for k in reversed(keys):
            safe_key_up(k)
    except Exception as e:
        log(f"Driver error in hotkey {keys}: {e}")

def safe_move_to(x, y):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            interception.move_to(int(x), int(y))
        except Exception as e:
            log(f"Driver error (move_to {x},{y}): {e}")

def safe_mouse_down(btn='left'):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            interception.mouse_down(btn)
        except Exception as e:
            log(f"Driver error (mouse_down {btn}): {e}")

def safe_mouse_up(btn='left'):
    with state.injecting_key:
        try:
            import interception
            interception.mouse_up(btn)
        except Exception as e:
            log(f"Driver error (mouse_up {btn}): {e}")

def safe_write(char):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            interception.write(char)
        except Exception as e:
            log(f"Driver error (write): {e}")

def safe_scroll(direction):
    if state.is_stopped(): return
    with state.injecting_key:
        try:
            import interception
            valid_dir = 'down' if direction.lower() == 'down' else 'up'
            interception.scroll(valid_dir)
        except Exception as e:
            log(f"Driver error (scroll {direction}): {e}")

def emergency_cleanup():
    """Release all held keys/mouse buttons safely to return control to human."""
    try:
        for k in ('shift', 'ctrl', 'alt', 'win', 'enter', 'escape', 'up', 'down', 'left', 'right'):
            safe_key_up(k)
        for btn in ('left', 'right'):
            safe_mouse_up(btn)
        log('Input state cleaned. Human has control.')
    except Exception as e:
        log(f"Error during emergency cleanup: {e}")
