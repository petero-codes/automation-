import os
import time
import random
from typing import Tuple

from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press
from core.human_physics import human_typing, human_scroll, active_wait
from core.window_manager import focus_window_by_title, maximize_active_window, close_app_safely, wait_for_window
from tasks.engineering_workload import navigate_explorer_address_bar
from core.financial_generator import FinancialGenerator, FinancialModel, FinancialCell

financial_gen = FinancialGenerator()

def _navigate_cell(curr: Tuple[int, int], target: Tuple[int, int]):
    """Navigates from current grid coordinate to target using arrow keys."""
    curr_r, curr_c = curr
    target_r, target_c = target

    # Row navigation
    d_r = target_r - curr_r
    if d_r > 0:
        for _ in range(d_r):
            if state.is_stopped(): break
            safe_press('down')
            time.sleep(0.04)
    elif d_r < 0:
        for _ in range(-d_r):
            if state.is_stopped(): break
            safe_press('up')
            time.sleep(0.04)

    # Column navigation
    d_c = target_c - curr_c
    if d_c > 0:
        for _ in range(d_c):
            if state.is_stopped(): break
            safe_press('right')
            time.sleep(0.04)
    elif d_c < 0:
        for _ in range(-d_c):
            if state.is_stopped(): break
            safe_press('left')
            time.sleep(0.04)

def task_financial_modeling(duration: int):
    r"""
    Autonomous Financial Modeling & Analysis Workload in Microsoft Excel:
      - Generates 50-90 dynamic rows across financial domains
      - Procedural File Explorer address-bar launch into Desktop\Financial_Models
      - Enters data and live accounting formulas (=SUM, =AVERAGE, =IF, =VLOOKUP)
      - Applies professional accounting borders and currency formatting
    """
    log("[Financial Modeling] Generating dynamic financial model...")
    model: FinancialModel = financial_gen.generate_model()
    log(f"[Financial Modeling] Active Model: {model.model_name} ({model.row_count} rows, {len(model.cells)} cells)")

    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
    models_dir = os.path.join(user_profile, "Desktop", "Financial_Models")
    try:
        os.makedirs(models_dir, exist_ok=True)
    except Exception as e:
        log(f"[Financial Modeling] Directory note: {e}")

    start_time = time.time()

    # Step 1: Launch Excel via Procedural Explorer Address-Bar Navigation
    excel_cmd = f'excel "{model.model_name}.xlsx"'
    navigate_explorer_address_bar(models_dir, excel_cmd)
    if state.is_stopped(): return

    # Step 2: Focus & Maximize Excel Window
    if not wait_for_window(["Excel", "Microsoft Excel"], timeout=18):
        log("[Financial Modeling] Notice: Waiting for Excel window...")
        time.sleep(2.0)

    focus_window_by_title(["Excel", "Microsoft Excel"])
    time.sleep(0.6)
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.0))

    # If opening a fresh Excel instance, select blank workbook
    safe_press('enter')
    time.sleep(random.uniform(0.8, 1.4))

    # Step 3: Populate Spreadsheet Grid with Human Cadence
    current_pos = (1, 1)

    for cell in model.cells:
        if state.is_stopped() or time.time() - start_time >= duration:
            break

        # Move to target cell
        _navigate_cell(current_pos, (cell.row, cell.col))
        current_pos = (cell.row, cell.col)

        # Type cell value / live formula
        human_typing(cell.value, wpm=random.randint(65, 95), typos=False)
        if state.is_stopped(): break

        # Submit cell entry (Enter moves down by 1 in Excel default settings)
        safe_press('enter')
        current_pos = (cell.row + 1, cell.col)
        time.sleep(random.uniform(0.06, 0.20))

        # Format Currency if needed
        if cell.format_currency and random.random() < 0.25:
            # Move back up to format
            safe_press('up')
            time.sleep(0.05)
            hotkey('ctrl', 'shift', '$')
            safe_press('down')
            time.sleep(0.05)

        # Natural cognitive review pause every 10-18 cells
        if cell.row % random.randint(10, 18) == 0 and cell.col == 1:
            if state.stop_automation_event.wait(random.uniform(1.2, 3.0)):
                break

    # Step 4: Apply Professional Formatting & Accounting Borders
    if not state.is_stopped() and time.time() - start_time < duration:
        log("[Financial Modeling] Applying accounting borders and column formatting...")
        
        # Select All
        hotkey('ctrl', 'a')
        time.sleep(0.4)

        # Apply All Borders: Alt -> H -> B -> A
        for key in ('alt', 'h', 'b', 'a'):
            if state.is_stopped(): break
            safe_press(key)
            time.sleep(0.12)
        time.sleep(0.4)

        # Auto-fit Column Widths: Alt -> H -> O -> I
        for key in ('alt', 'h', 'o', 'i'):
            if state.is_stopped(): break
            safe_press(key)
            time.sleep(0.12)
        time.sleep(0.5)

        # Deselect and return to top-left
        hotkey('ctrl', 'home')
        time.sleep(0.6)

        # Save Workbook: Ctrl + S
        hotkey('ctrl', 's')
        time.sleep(0.8)

    # Step 5: Natural Review Scroll Session
    remaining = duration - (time.time() - start_time)
    if remaining > 10 and not state.is_stopped():
        log("[Financial Modeling] Reviewing financial worksheet...")
        for _ in range(random.randint(4, 10)):
            if state.is_stopped(): break
            human_scroll('down', random.randint(2, 5))
            time.sleep(random.uniform(1.2, 2.5))
        for _ in range(random.randint(2, 5)):
            if state.is_stopped(): break
            human_scroll('up', random.randint(2, 4))
            time.sleep(random.uniform(1.0, 2.0))

    log("[Financial Modeling] Workload cycle complete.")
