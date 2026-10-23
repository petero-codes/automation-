import time
import random
from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import content_scroll_session, human_mouse_move, _screen_size
from tasks.shared import open_browser, _open_url, detect_best_browser
from config.domains import get_random_domain

def task_technical_research(duration: int):
    """
    Autonomous Technical Web Exploration & Research Workload:
      - Curated rotation across 220+ technical and enterprise domains
      - Supports Brave, Firefox, Edge, and Chrome
      - Realistic human reading physics & chaotic burst scrolling
      - Tab dynamics (tab creation, cycling, closing)
    """
    detected_exe, detected_title = detect_best_browser()
    log(f"[Technical Research] Active Browser: {detected_title} ({detected_exe}) for {duration}s")
    
    open_browser(detected_exe, detected_title)
    if state.is_stopped(): return

    start_time = time.time()
    tab_count = 1

    while time.time() - start_time < duration and not state.is_stopped():
        domain = get_random_domain()
        log(f"[Technical Research] Navigating to technical resource: {domain}")
        
        success = _open_url(domain)
        if not success or state.is_stopped():
            break

        # Reading & Exploration Phase on current domain
        browse_dwell = random.uniform(25.0, 75.0)
        remaining = duration - (time.time() - start_time)
        session_time = min(browse_dwell, max(5.0, remaining))

        content_scroll_session('reading', session_time)
        if state.is_stopped(): break

        # Tab Dynamics: Open references in background or new tabs
        if random.random() < 0.40 and tab_count < 4 and remaining > 30:
            secondary_domain = get_random_domain()
            log(f"[Technical Research] Opening reference tab: {secondary_domain}")
            hotkey('ctrl', 't')
            time.sleep(random.uniform(0.4, 0.7))
            tab_count += 1
            
            _open_url(secondary_domain)
            if state.is_stopped(): break

            # Brief scan on secondary tab
            content_scroll_session('scanning', random.uniform(15.0, 30.0))
            if state.is_stopped(): break

            # Cycle tabs (Ctrl + Tab)
            if random.random() < 0.60:
                hotkey('ctrl', 'tab')
                time.sleep(random.uniform(1.0, 2.5))

            # Close reference tab (Ctrl + W)
            if random.random() < 0.50 and tab_count > 1:
                hotkey('ctrl', 'w')
                tab_count -= 1
                time.sleep(random.uniform(0.5, 1.2))

        # Natural cognitive pause before next research rotation
        dwell_pause = random.uniform(3.0, 8.0)
        if state.stop_automation_event.wait(dwell_pause):
            break

    log("[Technical Research] Research session concluded.")
