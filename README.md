# Nextgen Autonomous Workforce Engine

> **Enterprise-Grade, Undetectable Autonomous Workforce Platform for Windows 10/11**

Nextgen is a high-performance autonomous workforce platform engineered with kernel-level hardware simulation (via the Windows **Interception** filter driver) and natural cognitive pacing. Driven by genuine Ring-0 hardware RawInput packets, Nextgen produces realistic, human-indistinguishable computer activity across three mission-critical enterprise workloads.

---

## 🏛️ Mission-Critical Workloads

### 💻 1. Software Engineering (Visual Studio Code & Git)
* **Dynamic Task Pooling**: Autonomous full-stack software development across dynamic system architectures powered by high-entropy procedural generation (and optional Gemini AI synthesis).
* **Procedural File Explorer Navigation**: `Win+E` -> focus address bar (`Alt+D`) -> navigate to project folder -> launch via address bar `code .`.
* **Authentic Human Flow**: Variable typing cadence (65–95 WPM) with burst pacing, bigram acceleration, cognitive code review dwell pauses, tab navigation, and integrated terminal Git staging (`git status`, `git add .`, `git commit`).

### 📊 2. Financial Modeling & Analysis (Microsoft Excel)
* **50–90 Row Dynamic Models**: Real-time generation of SaaS Unit Economics, DCF Valuations, and Departmental OPEX models.
* **Procedural File Explorer Launch**: `Win+E` -> address bar `Desktop\Financial_Models` -> launch `excel "<model>.xlsx"`.
* **Live Accounting Formulas**: Enters real formulas cell-by-cell (`=SUM`, `=AVERAGE`, `=IF`, `=VLOOKUP`).
* **Professional Accounting Formatting**: Currency formatting (`Ctrl+Shift+$`), accounting borders (`Alt+H+B+A`), and column auto-fitting (`Alt+H+O+I`).

### 🌐 3. Technical Web Exploration & Research (220+ Domains)
* **220+ Curated Domains**: Systematic research across Cloud & Infrastructure (AWS, Azure, GCP, Kubernetes, Docker), Language Specs (Python, Rust, Go, TypeScript, MDN), Distributed Databases (Postgres, Redis, Kafka), AI/ML research (ArXiv, PyTorch, HuggingFace), and Engineering publications (Hacker News, IEEE, Martin Fowler).
* **Browser Agnostic**: Native support for Brave, Mozilla Firefox, Microsoft Edge, and Google Chrome.
* **Reading Physics & Tab Dynamics**: Chaotic burst scrolling, reading drift, opening references in background tabs (`Ctrl+T`), tab switching (`Ctrl+Tab`), and natural tab cleanup (`Ctrl+W`).

### 📖 4. Reading Mode (Subtle Scroll Jiggler Engine)
* **Zero-Drift Simulation**: Designed for reading documents, PDFs, code files, and specifications.
* **Symmetrical Micro-Scroll**: After 120 seconds of unbroken human inactivity, executes a subtle downward micro-scroll (1–3 notches), dwells naturally for 1.5s–3.0s, and scrolls back UP by the exact same amount.
* **Zero Cursor Movement (0px)**: Preserves exact reading viewport position while generating genuine Ring-0 hardware RawInput packets that reset OS sleep, screensavers, and Teams/Slack away timers.

---

## 🛡️ Non-Maskable Human Priority (IRQ 0)

* **Instant Yield (<30ms)**:
  * Mouse movement displacement (`>25px`)
  * Mouse clicks (Left, Right, or Middle click)
  * Dedicated toggle keys (`[PAUSE]` or `[F8]`)
  * Double-tap `[ESC]`
* **Inactivity Auto-Resume**: Automatically resumes work after 2 minutes (120s) of unbroken human inactivity.
* **Fine-Grained Resumability**: Encrypted session state persisted via Windows DPAPI (`CryptProtectData`), checkpointing the exact code line, spreadsheet cell, or URL.

---

## 🚀 Quick Start (One-Click Deployment)

### Step 1: Install (Run Once)
Double-click **`INSTALL.bat`** (or right-click -> *Run as administrator*).
* Automatically detects or installs Python 3.10+.
* Builds isolated `.venv` with machine-portability safeguards.
* Registers the **Interception Kernel Driver** with Windows.
* Creates a desktop shortcut: **"Loggy Bot"**.

### Step 2: Restart Your Computer (Required)
Windows requires a one-time reboot for the kernel driver to bind to hardware mouse and keyboard device stacks.

### Step 3: Run the Workforce Engine
Double-click **`RUN.bat`** (or your desktop shortcut).
* Verifies kernel driver is loaded and active.
* Automatically auto-detects your installed browser.
* Awaits 120s of human inactivity, triggers the subtle reading jiggler, and commences autonomous workforce operations.

---

## 📂 Project Directory Structure

```text
python-automation/
├── INSTALL.bat                   # 1-Click installer (Python, .venv, driver, shortcut)
├── RUN.bat                       # 1-Click launcher (checks driver, launches Nextgen)
├── uninstall_driver.bat          # Clean uninstaller for Interception driver
├── requirements.txt              # Minimal dependency manifest
├── README.md                     # Technical architecture & deployment guide
│
├── Interception/                 # Ring-0 Kernel Filter Driver
│   ├── install-interception.exe  # Official driver installer binary
│   └── library/                  # x64 & x86 C/C++ libraries
│
├── final_bot/                    # Nextgen Modular Bot Engine
│   ├── main_shorts.py            # Primary entry point (Auto-detects browser)
│   ├── main_firefox.py           # Firefox targeted entry point
│   ├── main_chrome.py            # Chrome targeted entry point
│   ├── main_edge.py              # Edge targeted entry point
│   │
│   ├── config/
│   │   ├── domains.py            # 220+ curated technical and enterprise domains
│   │   └── settings.py           # Timing, weights, and parameters
│   │
│   ├── core/
│   │   ├── priority_engine.py    # Non-maskable IRQ 0 human priority hook (<30ms)
│   │   ├── checkpoint_manager.py # Windows DPAPI encrypted session resumability
│   │   ├── procedural_coder.py   # High-entropy software engineering generator
│   │   ├── financial_generator.py# 50-90 row Excel model generator with live formulas
│   │   ├── human_physics.py      # Cubic Bezier mouse easing, typing flow, scroll
│   │   ├── input_driver.py       # Interception driver wrapper
│   │   └── window_manager.py     # Window focus & maximization
│   │
│   └── tasks/
│       ├── engineering_workload.py# VS Code full-stack software development & Git
│       ├── financial_workload.py  # Excel financial modeling & accounting formatting
│       ├── research_workload.py   # 220+ domain technical web exploration
│       ├── reading_jiggler.py     # Zero-drift subtle scroll reading jiggler
│       └── scheduler.py           # Weighted enterprise task scheduler
│
└── tests/
    └── test_nextgen_suite.py     # 9 comprehensive unit & integration tests
```

---

## 🧪 Verification & Testing

To execute the unit and integration test suite:
```cmd
.venv\Scripts\python.exe -m unittest tests/test_nextgen_suite.py
```
* **Test Results**: 9/9 Tests Passing (Priority Engine, Zero-Drift Jiggler, Procedural Coder, Financial Generator, 220+ Domains, DPAPI Checkpoints, Scheduler Weights).
