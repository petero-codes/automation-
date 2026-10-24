import os
import time
import random
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

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

def compute_file_hash(content: str) -> str:
    """Computes SHA-256 hash of file content for state verification."""
    return hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()

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

def save_vscode_checkpoint(
    task: CodingTask,
    workspace_dir: str,
    filename: str,
    line_idx: int,
    lines: list,
) -> None:
    """Saves granular checkpoint with last completed op, next intended op, and content hash."""
    file_path = os.path.join(workspace_dir, filename)
    last_op = {
        "op": "WRITE_LINE",
        "file": filename,
        "line_index": line_idx,
        "content": lines[line_idx] if 0 <= line_idx < len(lines) else "",
    }
    next_idx = line_idx + 1
    next_op = {
        "op": "WRITE_LINE",
        "file": filename,
        "line_index": next_idx,
        "content": lines[next_idx] if next_idx < len(lines) else None,
    }

    # Snapshot written lines so far
    written_so_far = "\n".join(lines[:line_idx + 1])
    content_hash = compute_file_hash(written_so_far)

    checkpoint_payload = {
        "status": "PAUSED",
        "project_name": task.project_name,
        "language": task.language,
        "workspace_dir": workspace_dir,
        "current_file": filename,
        "file_path": file_path,
        "line_index": line_idx,
        "last_completed_op": last_op,
        "next_intended_op": next_op,
        "file_content_hash": content_hash,
        "files": task.files,
        "git_commits": task.git_commits,
        "interrupted_at": time.time(),
    }
    checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", checkpoint_payload)
    log(f"[Resume Controller] Checkpointed exact position: {filename} at line {line_idx + 1} (Next: line {next_idx + 1})")

def validate_vscode_resume(file_path: str, checkpoint_payload: Dict[str, Any]) -> tuple[bool, int]:
    """
    Validates file state before resuming.
    Preserves human edits made during pause.
    Returns (can_resume: bool, next_line_index: int).
    """
    resume_line_idx = checkpoint_payload.get("line_index", -1)
    last_op = checkpoint_payload.get("last_completed_op", {})
    expected_last_content = last_op.get("content", "").strip()

    # If the file does not exist on disk yet (e.g. was only in editor tab), resume next line
    if not os.path.isfile(file_path):
        return True, resume_line_idx + 1

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            disk_lines = f.readlines()

        disk_stripped = [l.strip() for l in disk_lines]

        # Verify if human made modifications while automation was paused
        if expected_last_content:
            # Check if expected last completed line is present in file
            matching_indices = [i for i, l in enumerate(disk_stripped) if l == expected_last_content]
            if matching_indices:
                # Find the closest matching index to our interrupted line
                best_idx = min(matching_indices, key=lambda i: abs(i - resume_line_idx))
                log(f"[Resume Controller] Preserved human edits. Re-anchored to line {best_idx + 1} (matching last completed op).")
                return True, best_idx + 1
            else:
                log(f"[Resume Controller] Note: Human modified or replaced checkpointed line. Continuing safely from next intended line {resume_line_idx + 2}.")
                return True, resume_line_idx + 1

        return True, resume_line_idx + 1
    except Exception as e:
        log(f"[Resume Controller] File validation error ({e}). Aborting safely.")
        return False, -1

def task_software_engineering(duration: int) -> bool:
    """
    Autonomous Software Engineering Workload in Visual Studio Code:
      - Validates and resumes from exact file, line, and operation checkpoint.
      - Preserves human edits made during pauses.
      - Checks installation; cleanly skips if VS Code is missing.
      - Strict foreground window focus verification (zero blind typing).
      - Variable typing cadence with structural boundary pauses.
      - Integrated terminal git staging workflow.
    """
    if not is_vscode_installed():
        log("[Software Engineering] VS Code is not installed on this system. Skipping workload cleanly.")
        return False

    # Check for an interrupted paused session checkpoint
    cp = checkpoint_mgr.load_checkpoint()
    is_resuming = (
        cp is not None
        and cp.get("workload") in ("SOFTWARE_ENGINEERING", "VS_CODE")
        and (cp.get("status") == "PAUSED" or cp.get("payload", {}).get("status") == "PAUSED")
    )

    if is_resuming:
        payload = cp.get("payload", cp)
        task = CodingTask(
            project_name=payload.get("project_name", "resumed_project"),
            language=payload.get("language", "python"),
            files=payload.get("files", {}),
            git_commits=payload.get("git_commits", ["chore: update"]),
        )
        workspace_dir = payload.get("workspace_dir", "")
        resume_file = payload.get("current_file")
        file_path = payload.get("file_path", os.path.join(workspace_dir, resume_file) if resume_file else "")

        # Validate checkpoint before continuing
        valid, next_start_line = validate_vscode_resume(file_path, payload)
        if not valid:
            log("[Software Engineering] Checkpoint validation failed: File state cannot be recovered safely. Aborting task rather than guessing.")
            checkpoint_mgr.clear_checkpoint()
            return False

        resume_line_idx = next_start_line - 1
        log(f"[Resume Controller] Restoring interrupted VS Code task: {task.project_name} -> {resume_file} starting at line {next_start_line}")
    else:
        log("[Software Engineering] Generating dynamic task architecture...")
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
    time.sleep(random.uniform(0.8, 1.5))

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
            start_line = resume_line_idx + 1
            log(f"[Resume Controller] Resuming active file: {filename} from line {start_line + 1} of {len(lines)}")
            is_resuming = False
        else:
            log(f"[Software Engineering] Editing file: {filename}")
            hotkey('ctrl', 'n')  # New tab in VS Code
            time.sleep(random.uniform(0.6, 1.2))

        for idx in range(start_line, len(lines)):
            line = lines[idx]
            if state.is_stopped() or time.time() - start_time >= duration:
                # Interrupted: Checkpoint exact file & line index without repeating!
                prev_completed = idx - 1 if idx > 0 else 0
                save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines)
                return False

            stripped = line.strip()
            # Natural code review pauses on structural boundaries
            if stripped.startswith(('def ', 'class ', 'export ', 'interface ', 'func ')):
                if state.stop_automation_event.wait(random.uniform(1.0, 2.5)):
                    prev_completed = idx - 1 if idx > 0 else 0
                    save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines)
                    return False
            elif stripped == '' and random.random() < 0.35:
                if state.stop_automation_event.wait(random.uniform(0.4, 1.2)):
                    prev_completed = idx - 1 if idx > 0 else 0
                    save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines)
                    return False

            # Handle indentation via tabs
            indent_count = len(line) - len(line.lstrip(' \t'))
            for _ in range(indent_count // 4 if line.startswith(' ') else indent_count):
                if state.is_stopped(): break
                safe_press('tab')
                time.sleep(0.04)

            # Type line content with authentic human typing cadence (65-95 WPM)
            actual_content = line.strip()
            if actual_content:
                human_typing(actual_content, wpm=random.randint(65, 95))

            if state.is_stopped():
                # Line completed just before yield: record this idx as last completed op
                save_vscode_checkpoint(task, workspace_dir, filename, idx, lines)
                return False

            safe_press('enter')
            time.sleep(random.uniform(0.06, 0.20))

            # Periodic saving (Ctrl+S)
            if idx > 0 and idx % random.randint(4, 8) == 0:
                hotkey('ctrl', 's')
                time.sleep(0.3)

        # Final save for the active file
        if not state.is_stopped():
            hotkey('ctrl', 's')
            time.sleep(0.5)

        # Code review scroll session
        if not state.is_stopped():
            hotkey('ctrl', 'home')
            time.sleep(0.4)
            for _ in range(random.randint(2, 5)):
                if state.is_stopped(): break
                human_scroll('down', random.randint(1, 3))
                time.sleep(random.uniform(0.6, 1.5))

    # Step 4: Terminal Git Staging Workflow
    remaining = duration - (time.time() - start_time)
    if remaining > 20 and not state.is_stopped():
        if not focus_window_by_title(target_titles):
            log("[Software Engineering] VS Code not focused for terminal. Aborting.")
            return False

        log("[Software Engineering] Opening integrated terminal for Git staging...")
        hotkey('ctrl', '`')  # Toggle integrated terminal
        time.sleep(random.uniform(1.2, 2.0))

        git_steps = [
            ("git status", 1.5),
            ("git add .", 1.0),
            (f'git commit -m "{task.git_commits[0]}"', 1.8)
        ]

        for git_cmd, review_pause in git_steps:
            if state.is_stopped(): break
            human_typing(git_cmd, wpm=random.randint(75, 95), typos=False)
            time.sleep(0.2)
            safe_press('enter')
            if state.stop_automation_event.wait(review_pause):
                break

        # Close terminal panel
        if not state.is_stopped():
            hotkey('ctrl', '`')
            time.sleep(0.4)

    if not state.is_stopped():
        # Task completed end-to-end: clear checkpoint
        checkpoint_mgr.clear_checkpoint()
        log("[Software Engineering] Workload cycle complete. Checkpoint cleared.")
        return True
    return False
