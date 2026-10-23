import os
import time
import random
from pathlib import Path

from core import state
from core.logger import log
from core.input_driver import hotkey, safe_press, safe_write
from core.human_physics import human_typing, human_mouse_move, human_scroll, active_wait
from core.window_manager import (
    focus_window_by_title,
    maximize_active_window,
    close_app_safely,
    wait_for_window,
    bind_thread_to_interactive_desktop,
)
from core.procedural_coder import ProceduralCoder, CodingTask
from core.checkpoint_manager import checkpoint_mgr
from tasks.shared import is_vscode_installed, get_vscode_executable, open_app_via_run

coder_instance = ProceduralCoder()

def launch_or_focus_vscode(workspace_dir: str) -> bool:
    """
    Directly and reliably launches Visual Studio Code or brings an existing instance forward,
    then verifies window visibility and focus.
    """
    bind_thread_to_interactive_desktop()
    target_titles = ["Visual Studio Code", "Code"]

    # 1. If VS Code is already open, bring to front
    if focus_window_by_title(target_titles):
        log("[Software Engineering] Visual Studio Code is already running; brought to front.")
        return True

    # 2. Try launching via Start menu
    log(f"[Software Engineering] Launching VS Code for workspace: {workspace_dir}")
    open_app_via_run("code")
    time.sleep(2.0)

    # 3. If still not appeared, try direct process spawn fallback
    if not wait_for_window(target_titles, timeout=10.0):
        vscode_exe = get_vscode_executable()
        try:
            import subprocess
            if vscode_exe and os.path.isfile(vscode_exe):
                subprocess.Popen([vscode_exe, workspace_dir])
            else:
                subprocess.Popen(["cmd.exe", "/c", "code", workspace_dir])
        except Exception as e:
            log(f"[Software Engineering] Launch error: {e}")

    # 4. Wait for window to appear, focus, and verify
    return wait_for_window(target_titles, timeout=15.0)

def task_software_engineering(duration: int) -> bool:
    """
    Autonomous Software Engineering Workload in Visual Studio Code:
      - Resumes from exact file and line checkpoint if previously paused by human.
      - Checks installation; cleanly skips if VS Code is missing.
      - Procedural Task Pooling (dynamic multi-architecture code generation).
      - Procedural File Explorer address-bar launch.
      - Strict foreground window focus verification (zero blind typing).
      - Variable typing cadence (65-95 WPM) with code review pauses.
      - Multi-tab navigation & line review.
      - Integrated terminal git staging workflow.
    """
    if not is_vscode_installed():
        log("[Software Engineering] VS Code is not installed on this system. Skipping workload cleanly.")
        return False

    # Check for an interrupted paused session checkpoint
    cp = checkpoint_mgr.load_checkpoint()
    is_resuming = (
        cp is not None
        and cp.get("workload") == "SOFTWARE_ENGINEERING"
        and cp.get("payload", {}).get("status") == "PAUSED"
    )

    if is_resuming:
        payload = cp["payload"]
        task = CodingTask(
            project_name=payload["project_name"],
            language=payload["language"],
            files=payload["files"],
            git_commits=payload["git_commits"],
        )
        workspace_dir = payload["workspace_dir"]
        resume_file = payload.get("current_file")
        resume_line_idx = payload.get("line_index", -1)
        log(f"[Resume Controller] Restoring interrupted VS Code task: {task.project_name} -> {resume_file} at line {resume_line_idx + 1}")
    else:
        log(f"[Software Engineering] Generating dynamic task architecture...")
        task = coder_instance.generate_task()
        resume_file = None
        resume_line_idx = -1
        log(f"[Software Engineering] Task active: {task.project_name} ({task.language})")

        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
        workspace_dir = os.path.join(user_profile, "Desktop", "Workspaces", task.project_name)
        try:
            os.makedirs(workspace_dir, exist_ok=True)
        except Exception as e:
            log(f"[Software Engineering] Workspace directory notice: {e}")

    start_time = time.time()
    target_titles = ["Visual Studio Code", "Code"]

    # Step 1: Launch or Bring Forward VS Code
    if not is_resuming or not focus_window_by_title(target_titles):
        if not launch_or_focus_vscode(workspace_dir):
            log("[Software Engineering] Verification Failed: VS Code window did not appear. Aborting safely.")
            return False
        if state.is_stopped(): return False

    # Step 2: Focus & Maximize VS Code with strict verification
    if not focus_window_by_title(target_titles):
        log("[Software Engineering] Verification Failed: Could not focus VS Code window. Aborting safely.")
        return False

    time.sleep(0.6)
    maximize_active_window()
    time.sleep(random.uniform(1.0, 2.0))

    # Step 3: Implement Code Files with Human Cadence & Fine-Grained Resumability
    past_resume_file = False if resume_file else True

    for filename, code_content in task.files.items():
        if state.is_stopped() or time.time() - start_time >= duration:
            break

        if not past_resume_file:
            if filename != resume_file:
                continue
            past_resume_file = True

        # Verify VS Code is still the foreground window before any typing
        if not focus_window_by_title(target_titles):
            log("[Software Engineering] VS Code window lost focus. Halting keystroke injection.")
            return False

        lines = code_content.splitlines()
        start_line = 0

        if is_resuming and filename == resume_file and resume_line_idx >= 0:
            log(f"[Resume Controller] Resuming active file: {filename} from line {resume_line_idx + 2} of {len(lines)}")
            start_line = resume_line_idx + 1
            is_resuming = False  # Reset resume flag once first interrupted file is picked up
        else:
            log(f"[Software Engineering] Editing file: {filename}")
            hotkey('ctrl', 'n') # New tab in VS Code
            time.sleep(random.uniform(0.8, 1.4))

        for idx in range(start_line, len(lines)):
            line = lines[idx]
            if state.is_stopped() or time.time() - start_time >= duration:
                # Interrupted: Checkpoint exact file & line index!
                checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", {
                    "status": "PAUSED",
                    "project_name": task.project_name,
                    "language": task.language,
                    "workspace_dir": workspace_dir,
                    "files": task.files,
                    "git_commits": task.git_commits,
                    "current_file": filename,
                    "line_index": idx,
                    "interrupted_at": time.time(),
                })
                log(f"[Resume Controller] Checkpointed exact position: {filename} at line {idx + 1}")
                return False

            stripped = line.strip()
            # Natural code review pauses on structural boundaries
            if stripped.startswith(('def ', 'class ', 'export ', 'interface ', 'func ')):
                if state.stop_automation_event.wait(random.uniform(1.2, 3.5)):
                    checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", {
                        "status": "PAUSED",
                        "project_name": task.project_name,
                        "language": task.language,
                        "workspace_dir": workspace_dir,
                        "files": task.files,
                        "git_commits": task.git_commits,
                        "current_file": filename,
                        "line_index": idx,
                        "interrupted_at": time.time(),
                    })
                    return False
            elif stripped == '' and random.random() < 0.35:
                if state.stop_automation_event.wait(random.uniform(0.4, 1.5)):
                    checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", {
                        "status": "PAUSED",
                        "project_name": task.project_name,
                        "language": task.language,
                        "workspace_dir": workspace_dir,
                        "files": task.files,
                        "git_commits": task.git_commits,
                        "current_file": filename,
                        "line_index": idx,
                        "interrupted_at": time.time(),
                    })
                    return False

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

            if state.is_stopped():
                checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", {
                    "status": "PAUSED",
                    "project_name": task.project_name,
                    "language": task.language,
                    "workspace_dir": workspace_dir,
                    "files": task.files,
                    "git_commits": task.git_commits,
                    "current_file": filename,
                    "line_index": idx,
                    "interrupted_at": time.time(),
                })
                return False

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

    if not state.is_stopped():
        # Task completed end-to-end: clear checkpoint
        checkpoint_mgr.clear_checkpoint()
        log("[Software Engineering] Workload cycle complete. Checkpoint cleared.")
        return True
    return False
