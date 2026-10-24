import math
import random
import time
import ctypes
from core import state
from core.input_driver import safe_move_to, safe_write, safe_press
from config.settings import SCROLL_PROFILES

def _screen_size():
    return (ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1))

def get_mouse_pos():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

def _ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def human_mouse_move(tx, ty, duration=None):
    if state.is_stopped(): return
    try:
        sx, sy = get_mouse_pos()
        dist = math.hypot(tx - sx, ty - sy)
        if dist < 2:
            return
            
        if duration is None:
            # Slower, more deliberate default duration
            duration = random.uniform(0.5, 1.3) * max(0.5, (dist / 800))
            
        # Determine number of steps based on duration and a target 60-80 fps update rate
        fps = random.uniform(60, 80)
        num_steps = max(5, int(duration * fps))
        
        # Control points for a slight curve
        deviation = min(dist * 0.2, random.uniform(10, 80))
        cx = sx + (tx - sx) * 0.5 + random.uniform(-deviation, deviation)
        cy = sy + (ty - sy) * 0.5 + random.uniform(-deviation, deviation)
        
        step_delay = duration / num_steps

        for i in range(1, num_steps + 1):
            if state.is_stopped(): break
            t = i / num_steps
            t_eased = _ease_in_out_cubic(t)
            
            # Quadratic bezier interpolation using the eased t
            inv_t = 1.0 - t_eased
            px = (inv_t * inv_t * sx) + (2 * inv_t * t_eased * cx) + (t_eased * t_eased * tx)
            py = (inv_t * inv_t * sy) + (2 * inv_t * t_eased * cy) + (t_eased * t_eased * ty)
            
            # Add jitter that diminishes at the start and end
            jitter_mag = math.sin(t * math.pi) * random.uniform(0.5, 2.0)
            px += random.uniform(-jitter_mag, jitter_mag)
            py += random.uniform(-jitter_mag, jitter_mag)
            
            safe_move_to(int(round(px)), int(round(py)))
            time.sleep(max(step_delay, 0.002))

        # Final correction to exact coordinate
        if not state.is_stopped():
            safe_move_to(tx, ty)
            
        # Optional micro-correction overshoot
        if random.random() < 0.25 and not state.is_stopped():
            angle = random.uniform(0, 2 * math.pi)
            d = random.uniform(2, 8)
            ox, oy = int(tx + math.cos(angle) * d), int(ty + math.sin(angle) * d)
            safe_move_to(ox, oy)
            time.sleep(random.uniform(0.08, 0.2))
            if not state.is_stopped():
                safe_move_to(tx, ty)
    except Exception:
        pass

def random_mouse_drift():
    if state.is_stopped(): return
    sw, sh = _screen_size()
    human_mouse_move(
        random.randint(int(sw * 0.10), int(sw * 0.90)),
        random.randint(int(sh * 0.15), int(sh * 0.85)),
    )

def active_wait(wait_time):
    """Wait for wait_time with subtle periodic cursor drift to register activity."""
    start = time.time()
    while time.time() - start < wait_time and not state.is_stopped():
        remaining = wait_time - (time.time() - start)
        chunk = min(remaining, random.uniform(4.0, 8.0))
        if state.stop_automation_event.wait(chunk):
            break
        if not state.is_stopped():
            try:
                sx, sy = get_mouse_pos()
                sw, sh = _screen_size()
                nx = max(0, min(sw - 1, sx + random.randint(-15, 15)))
                ny = max(0, min(sh - 1, sy + random.randint(-15, 15)))
                human_mouse_move(nx, ny, duration=random.uniform(0.3, 0.8))
            except Exception:
                pass

QWERTY_NEIGHBORS = {
    'a': 'sqzw', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx',
    'e': 'wsdr', 'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb',
    'i': 'ujko', 'j': 'huikm', 'k': 'jiol', 'l': 'kop',
    'm': 'njk',  'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
    'q': 'wa',   'r': 'edft', 's': 'qazxdew', 't': 'rfgy',
    'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
    'y': 'tghu', 'z': 'asx',
}
FAST_BIGRAMS = {'th', 'er', 'in', 'on', 'at', 'nd', 'st', 'es', 'en', 'of', 'to', 'it', 'is'}

def _press_char(char):
    if char == '\n':
        safe_press('enter')
    elif char == '\t':
        safe_press('tab')
    elif char == '\b':
        safe_press('backspace')
    else:
        safe_write(char)

def human_typing(text, wpm=65, typos=True):
    base_delay = 60.0 / (wpm * 5)
    burst_rem  = random.randint(2, 12)
    prev_char  = ''
    t0 = time.time()
    
    # Introduce a wandering speed modulator to simulate changing train of thought
    flow_speed = 1.0 
    
    for i, char in enumerate(text):
        if state.is_stopped(): break
        
        burst_rem -= 1
        if burst_rem <= 0:
            burst_rem = random.randint(2, 12)
            # More erratic pauses
            pause = random.choices(
                [random.uniform(0.08, 0.25), random.uniform(0.30, 0.90), random.uniform(1.0, 3.0)],
                weights=[0.60, 0.30, 0.10]
            )[0]
            if state.stop_automation_event.wait(pause): break
            # Shift flow speed on burst resets
            flow_speed = random.uniform(0.5, 1.8)
            
        # Gradually normalize flow speed
        flow_speed += (1.0 - flow_speed) * 0.1
            
        fatigue = 1.0 + min(0.40, (time.time() - t0) / 3600 * 0.40)
        pair = (prev_char + char).lower()
        bigram_mult = 0.55 if pair in FAST_BIGRAMS else 1.0
        
        if (typos and char.isalpha() and random.random() < 0.025
                and char.lower() in QWERTY_NEIGHBORS
                and not state.is_stopped()):
            _press_char(random.choice(QWERTY_NEIGHBORS[char.lower()]))
            if state.stop_automation_event.wait(max(0.05, random.gauss(0.2, 0.08))): break
            safe_press('backspace')
            if state.stop_automation_event.wait(random.uniform(0.08, 0.18)): break

        _press_char(char)
        prev_char = char
        
        # Add high variance to individual key strokes
        stroke_variance = random.lognormvariate(0.0, 0.4)
        delay = base_delay * fatigue * bigram_mult * flow_speed * stroke_variance
        
        # Occasional micro-stutter
        if random.random() < 0.05:
            delay += random.uniform(0.1, 0.3)
            
        if state.stop_automation_event.wait(max(0.01, delay)): break

def human_scroll(direction, notches):
    from core.input_driver import safe_scroll
    if state.is_stopped(): return
    
    # Establish a base speed for this specific scroll burst
    burst_speed = random.uniform(0.02, 0.09)
    
    for i in range(notches):
        if state.is_stopped(): break
        safe_scroll(direction)
        
        # Fluctuate the speed wildly mid-scroll to make it uneven
        burst_speed *= random.uniform(0.5, 2.2)
        burst_speed = max(0.01, min(0.4, burst_speed))
        
        # Add occasional random hesitation
        hesitation = random.uniform(0.1, 0.5) if random.random() < 0.2 else 0.0
        
        time.sleep(burst_speed + hesitation)

def content_scroll_session(content_type, duration):
    if state.is_stopped(): return
    sw, sh = _screen_size()
    human_mouse_move(sw // 2, sh // 2)
    default_profile = ((1, 2), (2.0, 5.0), 0.10, 0.02, (5.0, 10.0))
    notch_range, pause_range, back_prob, distract_prob, distract_range = \
        SCROLL_PROFILES.get(content_type, default_profile)
    start = time.time()
    while time.time() - start < duration and not state.is_stopped():
        n = random.randint(*notch_range)
        human_scroll('down', n)
        if state.is_stopped(): break
        pause = random.uniform(*pause_range)
        if random.random() < back_prob:
            human_scroll('up', random.randint(1, 3))
            pause *= random.uniform(1.2, 1.8)
        if random.random() < distract_prob:
            pause += random.uniform(*distract_range)
        if random.random() < 0.18 and not state.is_stopped():
            random_mouse_drift()
        active_wait(pause)
