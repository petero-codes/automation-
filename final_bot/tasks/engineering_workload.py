import os
import time
import random
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

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
from tasks.shared import (
    is_vscode_installed,
    get_vscode_executable,
    launch_code_process,
    launch_or_focus_vscode,
)

coder_instance = ProceduralCoder()

def compute_file_hash(content: str) -> str:
    """Computes SHA-256 hash of file content for state verification."""
    return hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()

def save_vscode_checkpoint(
    task: CodingTask,
    workspace_dir: str,
    filename: str,
    line_idx: int,
    lines: list,
    col_idx: int = 0,
) -> None:
    """Saves granular checkpoint with last completed op, next intended op, and context snapshot."""
    file_path = os.path.join(workspace_dir, filename)
    last_op = {
        "op": "WRITE_LINE",
        "file": filename,
        "line_index": line_idx,
        "col_index": col_idx,
        "content": lines[line_idx] if 0 <= line_idx < len(lines) else "",
    }
    next_idx = line_idx + 1
    next_op = {
        "op": "WRITE_LINE",
        "file": filename,
        "line_index": next_idx,
        "col_index": 0,
        "content": lines[next_idx] if next_idx < len(lines) else None,
    }

    # Snapshot written lines so far & surrounding context lines for validation
    written_so_far = "\n".join(lines[:line_idx + 1])
    content_hash = compute_file_hash(written_so_far)
    start_ctx = max(0, line_idx - 2)
    expected_context_lines = [l.strip() for l in lines[start_ctx:line_idx + 1] if l.strip()]

    checkpoint_payload = {
        "status": "PAUSED",
        "project_name": task.project_name,
        "language": task.language,
        "workspace_dir": workspace_dir,
        "current_file": filename,
        "file_path": file_path,
        "line_index": line_idx,
        "col_index": col_idx,
        "last_completed_op": last_op,
        "next_intended_op": next_op,
        "file_content_hash": content_hash,
        "expected_context_lines": expected_context_lines,
        "files": task.files,
        "git_commits": task.git_commits,
        "interrupted_at": time.time(),
    }
    checkpoint_mgr.save_checkpoint("SOFTWARE_ENGINEERING", checkpoint_payload)
    log(f"[Resume Controller] Checkpointed exact position: {filename} at line {line_idx + 1}:{col_idx} (Next: line {next_idx + 1})")

def validate_vscode_resume(file_path: str, checkpoint_payload: Dict[str, Any]) -> Tuple[bool, str, int, int]:
    """
    Validates file state and context against the checkpoint before resuming.
    Preserves human edits made during pause.
    Returns (can_resume: bool, reason: str, next_line_index: int, col_index: int).
    """
    resume_line_idx = checkpoint_payload.get("line_index", -1)
    col_idx = checkpoint_payload.get("col_index", 0)
    last_op = checkpoint_payload.get("last_completed_op", {})
    expected_last_content = last_op.get("content", "").strip()
    expected_context = checkpoint_payload.get("expected_context_lines", [])

    # If the file does not exist on disk yet (e.g. was only in editor tab before first save), safe to resume next line
    if not os.path.isfile(file_path):
        return True, "File not yet committed to disk; proceeding from checkpoint", resume_line_idx + 1, col_idx

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            disk_lines = f.readlines()

        disk_stripped = [l.strip() for l in disk_lines]

        # 1. Exact match for last completed operation
        if expected_last_content:
            matching_indices = [i for i, l in enumerate(disk_stripped) if l == expected_last_content]
            if matching_indices:
                # Pick the closest matching occurrence to checkpoint line
                best_idx = min(matching_indices, key=lambda i: abs(i - resume_line_idx))
                log(f"[Resume Controller] Preserved human edits. Re-anchored to line {best_idx + 1} (matching last completed op).")
                return True, "Re-anchored to matching operation", best_idx + 1, col_idx

        # 2. If exact last line was edited by human, check surrounding context lines
        if expected_context:
            context_matches = [
                i for i, l in enumerate(disk_stripped)
                if any(ctx in l for ctx in expected_context)
            ]
            if context_matches:
                closest_ctx = min(context_matches, key=lambda i: abs(i - resume_line_idx))
                log(f"[Resume Controller] Preserved human edits. Re-anchored via context boundary at line {closest_ctx + 1}.")
                return True, "Re-anchored via context match", closest_ctx + 1, col_idx

        # 3. If file exists but expected context is completely unrecognizable (file wiped or replaced)
        if len(disk_stripped) > 0 and expected_last_content:
            log("[Resume Controller] Safety Halt: Checkpointed context cannot be located in file. Context has changed fundamentally.")
            return False, "Target file context has changed fundamentally; safe resumption impossible", -1, -1

        return True, "File verified; proceeding from next line", resume_line_idx + 1, col_idx
    except Exception as e:
        log(f"[Resume Controller] File validation error ({e}). Aborting safely.")
        return False, str(e), -1, -1

def task_software_engineering(duration: int) -> bool:
    """
    Autonomous Software Engineering Workload in Visual Studio Code:
      - Restores the exact workspace and file, not merely the last active editor.
      - Restores line and column, positioning editor cursor at next intended operation.
      - Validates file contents against checkpoint; stops if context changed fundamentally.
      - Preserves human edits made during pause.
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
        can_resume, reason, next_start_line, next_col = validate_vscode_resume(file_path, payload)
        if not can_resume:
            log(f"[Software Engineering] Checkpoint validation failed: {reason}. Aborting task rather than guessing.")
            checkpoint_mgr.clear_checkpoint()
            return False

        resume_line_idx = next_start_line - 1
        log(f"[Resume Controller] Restoring interrupted VS Code task: {task.project_name} -> {resume_file} starting at line {next_start_line}:{next_col}")
    else:
        log("[Software Engineering] Generating dynamic task architecture...")
        task = coder_instance.generate_task()
        resume_file = None
        resume_line_idx = -1
        next_col = 0
        file_path = ""
        log(f"[Software Engineering] Task active: {task.project_name} ({task.language})")

        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")
        workspace_dir = os.path.join(user_profile, "Desktop", "Workspaces", task.project_name)
        try:
            os.makedirs(workspace_dir, exist_ok=True)
        except Exception as e:
            log(f"[Software Engineering] Workspace directory notice: {e}")

    start_time = time.time()
    target_titles = ["Visual Studio Code", "Code"]

    # Step 1: Launch or Bring Forward VS Code with exact workspace and file restoration
    target_line = resume_line_idx + 1 if is_resuming else 1
    if not is_resuming or not focus_window_by_title(target_titles):
        if not launch_or_focus_vscode(workspace_dir, file_path=file_path, line=target_line, col=next_col):
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

        file_path = os.path.join(workspace_dir, filename)
        try:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    pass
        except Exception as e:
            log(f"[Software Engineering] File init notice: {e}")

        vscode_exe = get_vscode_executable()
        if is_resuming and filename == resume_file and resume_line_idx >= 0:
            start_line = resume_line_idx + 1
            log(f"[Resume Controller] Resuming active file: {filename} from line {start_line + 1} of {len(lines)}")
            if vscode_exe:
                launch_code_process([vscode_exe, "-r", "-g", f"{file_path}:{start_line + 1}:{next_col + 1}"])
                time.sleep(0.8)
            else:
                hotkey('ctrl', 'p')
                time.sleep(0.4)
                human_typing(filename, wpm=140, typos=False)
                safe_press('enter')
                time.sleep(0.6)
                hotkey('ctrl', 'g')
                time.sleep(0.3)
                human_typing(f"{start_line + 1}:{next_col + 1}", wpm=140, typos=False)
                safe_press('enter')

            focus_window_by_title(target_titles)
            maximize_active_window()
            time.sleep(0.2)
            safe_press('end')
            time.sleep(0.2)
            is_resuming = False
        else:
            log(f"[Software Engineering] Editing file: {filename}")
            if vscode_exe:
                launch_code_process([vscode_exe, "-r", file_path])
                time.sleep(0.8)
            else:
                hotkey('ctrl', 'p')
                time.sleep(0.4)
                human_typing(filename, wpm=140, typos=False)
                safe_press('enter')
                time.sleep(0.8)

            focus_window_by_title(target_titles)
            maximize_active_window()
            time.sleep(0.3)

        for idx in range(start_line, len(lines)):
            line = lines[idx]
            if state.is_stopped() or time.time() - start_time >= duration:
                # Interrupted: Checkpoint exact file & line index without repeating!
                prev_completed = idx - 1 if idx > 0 else 0
                save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines, col_idx=len(line))
                hotkey('ctrl', 's')
                return False

            stripped = line.strip()
            # Natural code review pauses on structural boundaries
            if stripped.startswith(('def ', 'class ', 'export ', 'interface ', 'func ')):
                if state.stop_automation_event.wait(random.uniform(1.0, 2.5)):
                    prev_completed = idx - 1 if idx > 0 else 0
                    save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines, col_idx=len(line))
                    hotkey('ctrl', 's')
                    return False
            elif stripped == '' and random.random() < 0.35:
                if state.stop_automation_event.wait(random.uniform(0.4, 1.2)):
                    prev_completed = idx - 1 if idx > 0 else 0
                    save_vscode_checkpoint(task, workspace_dir, filename, prev_completed, lines, col_idx=len(line))
                    hotkey('ctrl', 's')
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
                save_vscode_checkpoint(task, workspace_dir, filename, idx, lines, col_idx=len(line))
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
