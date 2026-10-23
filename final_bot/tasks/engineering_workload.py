import os
import time
import random
from pathlib import Path

from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press, safe_write
from core.human_physics import human_typing, human_mouse_move, human_scroll, active_wait
from core.window_manager import focus_window_by_title, maximize_active_window, close_app_safely, wait_for_window
from core.procedural_coder import ProceduralCoder, CodingTask
from tasks.shared import is_vscode_installed, get_vscode_executable

coder_instance = ProceduralCoder()

def navigate_explorer_address_bar(target_path: str, command_to_run: str = "code .") -> bool:
    """
    Procedural File Explorer address-bar navigation:
      1. Win + E -> Opens File Explorer
      2. Alt + D -> Focuses address bar
      3. Types target path and navigates
      4. Alt + D -> Types launch command (e.g. 'code .') and submits
    """
    if state.is_stopped():
        return False

    log(f"[Explorer Navigation] Opening File Explorer (Win+E)...")
    safe_press('win')
    time.sleep(0.2)
    hotkey('win', 'e')
    time.sleep(random.uniform(1.2, 2.0))

    if not wait_for_window(["File Explorer", "Explorer"], timeout=10):
        log("[Explorer Navigation] Explorer window not detected, proceeding directly.")
    else:
        focus_window_by_title(["File Explorer", "Explorer"])
        time.sleep(0.5)

    # Focus Address Bar
    log(f"[Explorer Navigation] Navigating address bar to: {target_path}")
    hotkey('alt', 'd')
    time.sleep(random.uniform(0.3, 0.6))
    
    # Type path and submit
    human_typing(target_path, wpm=85, typos=False)
    if state.is_stopped(): return False
    safe_press('enter')
    time.sleep(random.uniform(1.2, 2.0))

    # Focus address bar again to trigger executable
    log(f"[Explorer Navigation] Executing in directory: {command_to_run}")
    hotkey('alt', 'd')
    time.sleep(random.uniform(0.3, 0.5))
    human_typing(command_to_run, wpm=80, typos=False)
    if state.is_stopped(): return False
    safe_press('enter')
    time.sleep(random.uniform(2.5, 4.0))

    return True

def task_software_engineering(duration: int) -> bool:
    """
    Autonomous Software Engineering Workload in Visual Studio Code:
      - Checks installation; cleanly skips if VS Code is missing
      - Procedural Task Pooling (dynamic multi-architecture code generation)
      - Procedural File Explorer address-bar launch
      - Strict foreground window focus verification (zero blind typing)
      - Variable typing cadence (65-95 WPM) with code review pauses
      - Multi-tab navigation & line review
      - Integrated terminal git staging workflow
    """
    if not is_vscode_installed():
        log("[Software Engineering] VS Code is not installed on this system. Skipping workload cleanly.")
        return False

    log(f"[Software Engineering] Generating dynamic task architecture...")
    task: CodingTask = coder_instance.generate_task()
    log(f"[Software Engineering] Task active: {task.project_name} ({task.language})")

    # Prepare project workspace on disk
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
    workspace_dir = os.path.join(user_profile, "Desktop", "Workspaces", task.project_name)
    try:
        os.makedirs(workspace_dir, exist_ok=True)
    except Exception as e:
        log(f"[Software Engineering] Workspace directory notice: {e}")

    start_time = time.time()

    # Step 1: Launch via Procedural Explorer Navigation
    vscode_exe = get_vscode_executable()
    import shutil
    if shutil.which("code"):
        command_to_run = "code ."
    elif vscode_exe:
        command_to_run = f'"{vscode_exe}" "{workspace_dir}"'
    else:
        command_to_run = "code ."

    if not navigate_explorer_address_bar(workspace_dir, command_to_run):
        log("[Software Engineering] Explorer navigation aborted or interrupted.")
        return False
    if state.is_stopped(): return False

    # Step 2: Focus & Maximize VS Code with strict verification
    target_titles = ["Visual Studio Code", "Code"]
    if not wait_for_window(target_titles, timeout=18):
        log("[Software Engineering] Verification Failed: VS Code window did not appear. Aborting safely.")
        close_app_safely()
        return False

    if not focus_window_by_title(target_titles):
        log("[Software Engineering] Verification Failed: Could not focus VS Code window. Aborting safely.")
        return False

    time.sleep(0.6)
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.0))

    # Step 3: Implement Code Files with Human Cadence
    for filename, code_content in task.files.items():
        if state.is_stopped() or time.time() - start_time >= duration:
            break

        # Verify VS Code is still the foreground window before any typing
        if not focus_window_by_title(target_titles):
            log("[Software Engineering] VS Code window lost focus. Halting keystroke injection.")
            return False

        log(f"[Software Engineering] Editing file: {filename}")
        hotkey('ctrl', 'n') # New tab in VS Code
        time.sleep(random.uniform(0.8, 1.4))

        lines = code_content.splitlines()
        for idx, line in enumerate(lines):
            if state.is_stopped() or time.time() - start_time >= duration:
                break

            stripped = line.strip()
            # Natural code review pauses on structural boundaries
            if stripped.startswith(('def ', 'class ', 'export ', 'interface ', 'func ')):
                if state.stop_automation_event.wait(random.uniform(1.2, 3.5)):
                    break
            elif stripped == '' and random.random() < 0.35:
                if state.stop_automation_event.wait(random.uniform(0.4, 1.5)):
                    break

            # Handle indentation via tabs
            indent_count = len(line) - len(line.lstrip(' \t'))
            for _ in range(indent_count // 4 if line.startswith(' ') else indent_count):
                if state.is_stopped(): break
                safe_press('tab')
                time.sleep(0.04)

            # Type line content with authentic human typing cadence (65–95 WPM)
            actual_content = line.strip()
            if actual_content:
                human_typing(actual_content, wpm=random.randint(65, 95))

            if state.is_stopped(): break
            safe_press('enter')
            time.sleep(random.uniform(0.08, 0.25))

            # Periodic saving (Ctrl+S)
            if idx > 0 and idx % random.randint(4, 8) == 0:
                hotkey('ctrl', 's')
                time.sleep(0.4)

        # Final save for the active file
        if not state.is_stopped():
            hotkey('ctrl', 's')
            time.sleep(0.8)

        # Natural code review scroll session
        if not state.is_stopped():
            hotkey('ctrl', 'home')
            time.sleep(0.5)
            for _ in range(random.randint(3, 8)):
                if state.is_stopped(): break
                human_scroll('down', random.randint(1, 3))
                time.sleep(random.uniform(0.8, 2.2))

    # Step 4: Terminal Git Staging Workflow
    remaining = duration - (time.time() - start_time)
    if remaining > 20 and not state.is_stopped():
        if not focus_window_by_title(target_titles):
            log("[Software Engineering] VS Code not focused for terminal. Aborting.")
            return False

        log("[Software Engineering] Opening integrated terminal for Git staging...")
        hotkey('ctrl', '`') # Toggle integrated terminal
        time.sleep(random.uniform(1.5, 2.5))

        git_steps = [
            ("git status", 1.8),
            ("git add .", 1.0),
            (f'git commit -m "{task.git_commits[0]}"', 2.0)
        ]

        for git_cmd, review_pause in git_steps:
            if state.is_stopped(): break
            human_typing(git_cmd, wpm=random.randint(75, 95), typos=False)
            time.sleep(0.3)
            safe_press('enter')
            if state.stop_automation_event.wait(review_pause):
                break

        # Close terminal panel
        if not state.is_stopped():
            hotkey('ctrl', '`')
            time.sleep(0.5)

    log("[Software Engineering] Workload cycle complete.")
    return True
