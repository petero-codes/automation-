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

* **Instant Yield (<30ms)**:
  * Mouse movement displacement (`>25px`)
  * Mouse clicks (Left, Right, or Middle click)
  * Dedicated toggle keys (`[PAUSE]` or `[F8]`)
  * Double-tap `[ESC]`
* **Explicit User Resumption**:
  * When automation is paused by human intervention, the engine **never** auto-resumes on an idle timer.
  * Automation waits strictly for an explicit user signal (`[F8]`, `[PAUSE]`, or CLI command) before resuming.
* **Granular Checkpointing**:
  * Checkpoints are securely stored using Windows DPAPI (`CryptProtectData`).
  * Checkpoints explicitly distinguish between completed operations and next intended operations.
  * Completed operations are never blindly repeated.
* **Predictable Session Lifecycle**:
  * **Pause**: Preserves the checkpoint for the current session.
  * **Resume**: Validates the application state and continues from the checkpoint.
  * **Crash / Unexpected Shutdown**: Marks session state as `INTERRUPTED`. A subsequent launch detects the interrupted state and requires an explicit recovery decision (`--recover` to resume, or `--fresh` to discard).
  * **Permanent Termination**: Closing the console window (`X`), pressing `Ctrl+C`, or system shutdown invalidates and purges the checkpoint. Terminated sessions can never be resumed.

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

All 17 tests verify:
1. VS Code tasks execute correctly with file generation and git staging.
2. Excel tasks execute correctly with accounting formulas, borders, and column fitting.
3. Unrelated application modes are inaccessible and mode filters strictly isolate workloads.
4. Human input pauses automation within sub-30ms latency.
5. Paused automation does not resume until explicitly requested.
6. Excel resumes from the bot's correct task cell without repetition.
7. VS Code resumes from the bot's correct task location without repetition.
8. Human edits made during a pause are preserved.
9. Checkpoints cannot cause completed operations to be blindly repeated.
10. Terminated sessions cannot be resumed.
11. Interrupted sessions recover only through the explicit recovery flow.
12. Errors and unavailable applications fail safely with zero keystroke injection.
