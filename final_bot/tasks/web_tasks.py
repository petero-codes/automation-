import time
import random
from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing, content_scroll_session, active_wait, human_scroll
from core.window_manager import maximize_active_window, close_tab_safely
from tasks.shared import open_browser, _open_url
from config.settings import SHORTS_URL, WIKI_URLS, TECH_NEWS_URLS, REDDIT_URLS, GITHUB_URLS, NOVEL_URLS, SHOPPING_AND_EXPLORE_URLS

BROWSER_EXE = 'brave'
BROWSER_TITLE = 'Brave'

def shorts_scroll_session(duration):
    if state.is_stopped(): return
    from core.human_physics import _screen_size, human_mouse_move
    sw, sh = _screen_size()
    log("Verification: Centering mouse on screen to ensure scrolling hits the browser.")
    human_mouse_move(sw // 2, sh // 2)
    # Ensure viewport has keyboard focus instead of address bar
    safe_press('esc')
    time.sleep(0.5)
    start = time.time()
    
    while time.time() - start < duration and not state.is_stopped():
        watch_time = random.uniform(8.0, 30.0)
        active_wait(watch_time)
        if state.is_stopped(): break
        log("Scrolling to next Short...")
        try:
            # YouTube Shorts handles Next Video natively with down arrow. Highly reliable.
            safe_press('down')
        except Exception as e:
            log(f"Error during shorts next: {e}")
        if not state.is_stopped():
            if state.stop_automation_event.wait(random.uniform(0.8, 2.2)): break

def task_watch_shorts(duration):
    log(f'Task: Watching YouTube Shorts on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    if not _open_url(SHORTS_URL): return
    hotkey('ctrl', 'm') # Mute tab
    time.sleep(random.uniform(1.5, 3.0))
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.0))
    
    # As requested by user: we leave the nav bar visible instead of full screen
    time.sleep(random.uniform(2.0, 4.0))
    
    shorts_scroll_session(duration)
    
    if not state.is_stopped():
        # Clean up tab
        time.sleep(1.0)
        close_tab_safely()

def task_read_wiki(duration):
    log(f'Task: Reading Wikipedia on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    if not _open_url(random.choice(WIKI_URLS)): return
    maximize_active_window()
    time.sleep(random.uniform(1.5, 3.0))

    start = time.time()
    while time.time() - start < duration and not state.is_stopped():
        read_chunk = random.uniform(45.0, 90.0)
        read_chunk = min(read_chunk, duration - (time.time() - start))
        if read_chunk <= 0: break
        content_scroll_session('reading', read_chunk)
        if state.is_stopped(): break
        
        if time.time() - start < duration - 30:
            # Use Wikipedia's built-in shortcut for a random article
            hotkey('alt', 'shift', 'x')
            time.sleep(random.uniform(2.0, 4.0))

    if not state.is_stopped():
        close_tab_safely()

def task_browse_news(duration):
    log(f'Task: Browsing Tech News on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    
    current_url = random.choice(TECH_NEWS_URLS)
    if not _open_url(current_url): return
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.5))

    start = time.time()
    scan_time = random.uniform(40.0, 90.0)
    content_scroll_session('scanning', min(scan_time, duration))

    if not state.is_stopped() and (time.time() - start) < duration - 60:
        next_url = random.choice(TECH_NEWS_URLS)
        if next_url == current_url:
            safe_press('f5')
            time.sleep(random.uniform(2.0, 4.0))
        else:
            hotkey('ctrl', 'l')
            time.sleep(0.3)
            human_typing(next_url, wpm=95, typos=False)
            if not state.is_stopped():
                safe_press('enter')
                time.sleep(random.uniform(2.5, 4.5))
                safe_press('esc')
                time.sleep(0.4)
        
        current_url = next_url
        remaining = duration - (time.time() - start)
        if remaining > 0 and not state.is_stopped():
            content_scroll_session('scanning', remaining)

    if not state.is_stopped():
        close_tab_safely()

def task_read_novel(duration):
    log(f'Task: Reading a Novel on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    if not _open_url(random.choice(NOVEL_URLS)): return
    time.sleep(random.uniform(2.0, 4.0))
    maximize_active_window()
    content_scroll_session('novel', duration)
    if not state.is_stopped():
        close_tab_safely()

def task_browse_reddit(duration):
    log(f'Task: Browsing Reddit on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    
    current_url = random.choice(REDDIT_URLS)
    if not _open_url(current_url): return
    maximize_active_window()
    time.sleep(random.uniform(1.5, 3.0))

    start = time.time()
    chunk = random.uniform(90.0, 180.0)
    content_scroll_session('reddit', min(chunk, duration))

    if not state.is_stopped() and (time.time() - start) < duration - 45:
        next_url = random.choice(REDDIT_URLS)
        if next_url == current_url:
            safe_press('f5')
            time.sleep(random.uniform(2.0, 4.0))
        else:
            hotkey('ctrl', 'l')
            time.sleep(0.3)
            human_typing(next_url, wpm=90, typos=False)
            if not state.is_stopped():
                safe_press('enter')
                time.sleep(random.uniform(2.5, 4.5))
                safe_press('esc')
                time.sleep(0.4)
                
        current_url = next_url
        remaining = duration - (time.time() - start)
        if remaining > 0 and not state.is_stopped():
            content_scroll_session('reddit', remaining)

    if not state.is_stopped():
        close_tab_safely()

def task_browse_github(duration):
    log(f'Task: Browsing GitHub Trending on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return
    if not _open_url(random.choice(GITHUB_URLS)): return
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.5))
    content_scroll_session('github', duration)
    if not state.is_stopped():
        close_tab_safely()

def task_browse_explore(duration):
    log(f'Task: Browsing Shopping & Multi-Genre Sites on {BROWSER_TITLE}')
    open_browser(BROWSER_EXE, BROWSER_TITLE)
    if state.is_stopped(): return

    current_url = random.choice(SHOPPING_AND_EXPLORE_URLS)
    if not _open_url(current_url): return
    maximize_active_window()
    time.sleep(random.uniform(1.5, 3.0))

    start = time.time()
    chunk = random.uniform(50.0, 100.0)
    content_scroll_session('shopping', min(chunk, duration))

    if not state.is_stopped() and (time.time() - start) < duration - 50:
        next_url = random.choice(SHOPPING_AND_EXPLORE_URLS)
        if next_url == current_url:
            log("Same site selected, refreshing feed (F5)...")
            safe_press('f5')
            time.sleep(random.uniform(2.0, 4.0))
        else:
            hotkey('ctrl', 'l')
            time.sleep(0.3)
            human_typing(next_url, wpm=90, typos=False)
            if not state.is_stopped():
                safe_press('enter')
                time.sleep(random.uniform(2.5, 4.5))
                safe_press('esc')
                time.sleep(0.4)

        current_url = next_url
        remaining = duration - (time.time() - start)
        if remaining > 0 and not state.is_stopped():
            content_scroll_session('shopping', remaining)

    if not state.is_stopped():
        close_tab_safely()

