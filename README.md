# Nextgen Autonomous Workforce Engine

> **Dedicated Desktop Automation Engine: Visual Studio Code & Microsoft Excel Only**

Nextgen is a high-performance desktop automation platform engineered with hardware-level input emulation (via the Windows **Interception** filter driver), sub-30ms human priority yielding, and fine-grained session resumability. Nextgen produces realistic, human-indistinguishable computer activity across two dedicated offline productivity workloads: **Visual Studio Code** and **Microsoft Excel**.

---

## 🏛️ Supported Productivity Workloads (100% Offline)

### 💻 1. Software Engineering (Visual Studio Code & Git)
* **Procedural Code Synthesis**: Dynamic multi-architecture software generation (Python, TypeScript, Go).
* **Multi-Tier App Focus**: Checks running processes, Start Menu, and direct executable paths with strict foreground focus verification (zero blind typing).
* **Authentic Human Flow**: Variable typing cadence (65–95 WPM) with natural bursts, structural boundary pauses (functions, classes), tab indentation, and periodic file saves (`Ctrl+S`).
* **Integrated Git Staging**: Automated terminal staging (`git status`, `git add .`, `git commit`).
* **Edit-Preserving Resumption**: When interrupted, records exact file path, completed line index, `last_completed_op`, `next_intended_op`, and content hash. On resume, verifies file content, preserves human edits, and continues safely without repeating completed lines.

### 📊 2. Financial Modeling & Analysis (Microsoft Excel)
* **50–90 Row Dynamic Models**: Real-time generation of SaaS Unit Economics, DCF Valuations, and Departmental OPEX models.
* **Strict Focus Verification**: Brings forward and verifies foreground focus before any cell navigation or typing.
* **Live Accounting Formulas**: Enters real formulas cell-by-cell (`=SUM`, `=AVERAGE`, `=IF`, `=VLOOKUP`).
* **Professional Accounting Formatting**: Currency formatting (`Ctrl+Shift+$`), accounting borders (`Alt+H+B+A`), and column auto-fitting (`Alt+H+O+I`).
* **Non-Repeating Cell Resumption**: When interrupted, records workbook path, worksheet name, target cell coordinate `(row, col)`, `last_completed_op`, and `next_intended_op`. On resume, re-anchors to the target cell and advances strictly to `next_intended_op`, preventing blind re-execution.

---

## 🛡️ Human Interruption, Priority & Exact Resumption

* **Measured Human Input Priority Yield**:
  * Implemented using Win32 low-level message hooks (`WH_MOUSE_LL` and `WH_KEYBOARD_LL`).
  * Asynchronously dispatches emergency cleanup to avoid blocking the OS hook message pump.
  * Empirical measured latency: **0.6ms to 1.5ms** from human event detection to automation yield.
  * Triggers:
    * Mouse movement displacement (`>25px`)
    * Mouse clicks (Left, Right, or Middle click)
    * Dedicated toggle keys (`[PAUSE]` or `[F8]`)
    * Double-tap `[ESC]`
* **Explicit User Resumption**:
  * When automation is paused by human intervention, the engine **never** auto-resumes on an idle timer.
  * Automation waits strictly for an explicit user signal (`[F8]`, `[PAUSE]`, or CLI command) before resuming.
* **Granular DPAPI Checkpointing**:
  * Checkpoints are securely encrypted using Windows DPAPI (`CryptProtectData`). If DPAPI is unavailable, the engine refuses to persist unencrypted sensitive code, file paths, or financial data to disk.
  * Checkpoints explicitly distinguish between completed operations (`last_completed_op`) and next intended operations (`next_intended_op`).
  * Completed operations are never blindly repeated.
* **Predictable Session Lifecycle**:
  * **Pause**: Preserves the checkpoint for the current session.
  * **Resume**: Validates the application state and continues from the checkpoint.
  * **Crash / OS Shutdown / Logoff**: Marks session state as `INTERRUPTED` without deleting the checkpoint. A subsequent launch detects the interrupted state and requires an explicit recovery decision (`--recover` to resume, or `--fresh` to discard).
  * **Explicit Termination**: Closing the console window (`X`) or pressing `Ctrl+C` cleanly terminates the session, invalidates, and purges the checkpoint. Terminated sessions can never be resumed.

---

## ⚙️ Execution Modes

The engine strictly exposes only two execution modes (plus a combined mode):

| Mode | Command | Description |
| :--- | :--- | :--- |
| **Both** (Default) | `RUN.bat` or `python main.py --mode both` | Alternates between VS Code and Excel workloads |
| **VS Code Only** | `RUN.bat --mode vscode` or `python main.py --mode vscode` | Dedicated Software Engineering workload only |
| **Excel Only** | `RUN.bat --mode excel` or `python main.py --mode excel` | Dedicated Financial Modeling workload only |

Additional CLI flags:
* `--recover`: Recovers an interrupted session left by a crash or unexpected shutdown.
* `--fresh`: Discards any interrupted session and starts clean.

---

## 🚀 Quick Start (One-Click Deployment)

### Step 1: Install (Run Once)
Double-click **`INSTALL.bat`** (or right-click -> *Run as administrator*).
* Automatically detects or installs Python 3.10+.
* Builds isolated `.venv` with machine-portability safeguards.
* Registers the **Interception Filter Driver** with Windows.

### Step 2: Restart Your Computer (Required)
Windows requires a one-time reboot for the filter driver to bind to hardware input device stacks.

### Step 3: Run the Engine
Double-click **`RUN.bat`** (or run `RUN.bat --mode vscode` / `RUN.bat --mode excel`).
* Verifies driver status.
* Auto-detects installed desktop applications (VS Code, Microsoft Excel).
* 100% Offline operation: executes dedicated software engineering and financial modeling with zero external internet dependencies.

---

## 📂 Project Directory Structure

```text
python-automation/
├── INSTALL.bat                   # 1-Click installer (Python, .venv, driver)
├── RUN.bat                       # 1-Click launcher (checks driver, launches engine)
├── uninstall_driver.bat          # Clean uninstaller for Interception driver
├── requirements.txt              # Minimal dependency manifest
├── README.md                     # Technical architecture & deployment guide
│
├── Interception/                 # Hardware Input Filter Driver
│   ├── install-interception.exe  # Official driver installer binary
│   └── library/                  # x64 & x86 C/C++ libraries
│
├── final_bot/                    # Modular Bot Engine
│   ├── main.py                   # Engine entry point & supervisor
│   │
│   ├── config/
│   │   └── settings.py           # Timing, runtime, and scroll profile settings
│   │
│   ├── core/
│   │   ├── priority_engine.py    # Win32 Low-Level Hooks & <30ms yield
│   │   ├── session_manager.py    # Session Lifecycle (Active, Paused, Interrupted, Terminated)
│   │   ├── checkpoint_manager.py # Checkpoint Manager (DPAPI encryption & validation)
│   │   ├── system_cleaner.py     # Legacy System Cleaner (Auto-purges obsolete artifacts)
│   │   ├── procedural_coder.py   # High-entropy software engineering generator
│   │   ├── financial_generator.py# 50-90 row Excel model generator with live formulas
│   │   ├── human_physics.py      # Cubic Bezier mouse easing, typing flow, scroll
│   │   ├── input_driver.py       # Interception driver input injection wrapper
│   │   └── window_manager.py     # Window focus & interactive desktop binding
│   │
│   └── tasks/
│       ├── engineering_workload.py# VS Code Controller & line-level execution
│       ├── financial_workload.py  # Excel Controller & cell-level execution
│       ├── scheduler.py           # Mode-filtered task scheduler
│       └── shared.py              # Multi-tier app detection & window focus
│
└── tests/
    └── test_nextgen_suite.py     # Comprehensive test suite covering all 12 criteria
```

---

## 🧪 Verification & Testing

Run the test suite using the isolated virtual environment:

```cmd
.venv\Scripts\python.exe -m unittest discover tests
```

### Test Classification:
* **Real Windows Integration Tests (No Mocks)**:
  * **DPAPI Encryption & Persistence** (`test_dpapi_encrypted_checkpoints`): Executes real `CryptProtectData` and `CryptUnprotectData` on Windows filesystem.
  * **Zero Plaintext Fallback** (`test_dpapi_encryption_failure_prevents_plaintext_leak`): Verifies encryption failure aborts write rather than leaking plaintext data.
  * **Human Edit Preservation** (`test_8_human_edits_preserved_during_pause`): Writes real files to Windows filesystem, verifies re-anchoring to last completed operation.
  * **Session Lifecycle Persistence** (`test_10_terminated_sessions_cannot_be_resumed`, `test_11_interrupted_sessions_recover_only_through_intended_recovery_flow`): Exercises real state persistence across restarts and verifies that terminated sessions cannot be restored.
  * **OS Shutdown Handling** (`test_os_shutdown_preserves_interrupted_checkpoint`): Verifies OS shutdown signal preserves session checkpoint in `INTERRUPTED` state.
  * **Legacy System Artifact Cleaner** (`test_purge_legacy_system_artifacts`): Creates and cleans real residual files on disk.
* **Unit Tests & Logic Verification (Mocked GUI / Window State)**:
  * Application execution logic (`test_1_vscode_tasks_execute_correctly`, `test_2_excel_tasks_execute_correctly`): Verifies task synthesis, sequencing, and staging; GUI windows and keystrokes are mocked to prevent physical UI interference during test runs.
  * Mode filtering (`test_3_unrelated_application_modes_are_inaccessible`): Verifies exclusive isolation of VS Code and Excel modes.
  * Human input yield & latency measurement (`test_4_human_input_pauses_automation`): Verifies state transition and empirical performance counter measurement (<1.5ms).
  * Explicit resume requirement (`test_5_automation_does_not_resume_until_explicitly_requested`): Verifies idle timers cannot restart a paused session.
  * Resumption coordinate arithmetic (`test_6_excel_resumes_from_bot_correct_task_cell`, `test_7_vscode_resumes_from_bot_correct_task_location`).
  * Non-repetition of completed operations (`test_9_checkpoints_cannot_cause_completed_operations_to_be_repeated`).
  * Safe failure when apps are missing (`test_12_errors_and_unavailable_applications_fail_safely`).
  * Procedural coder & financial model generator (`test_procedural_coder_generation`, `test_financial_generator_structure_and_formulas`).
  * Checkpoint schema validation (`test_checkpoint_schema_deep_validation`).
