# Loggy Automation Suite

> **Undetectable Hardware-Level Windows Activity Emulation**

A production-grade Python automation framework designed to simulate authentic human computer activity on Windows without triggering synthetic input detection flags. Engineered with kernel-level device emulation via the Windows **Interception** filter driver to achieve genuine undetectability.

---

## 🚀 Quick Start (One-Click Deployment)

This package is self-contained and pre-configured for one-click deployment on any Windows machine.

### Step 1: Install (Run Once)
Double-click **`INSTALL.bat`** (or right-click -> *Run as administrator*).
* Automatically checks/installs Python 3.10+ if needed.
* Configures an isolated virtual environment (`.venv`) and installs all dependencies from `requirements.txt`.
* Registers the **Interception Kernel Driver** with Windows.
* Creates a desktop shortcut: **"Loggy Bot"**.

### Step 2: Restart Your Computer (Required)
Windows requires a one-time system reboot for the kernel driver to bind to hardware mouse and keyboard device stacks.

### Step 3: Run the Bot
Double-click **`RUN.bat`** (or your desktop shortcut).
* Automatically verifies that the driver is loaded in kernel memory.
* Automatically detects your installed browser (**Brave**, **Google Chrome**, **Mozilla Firefox**, or **Microsoft Edge**).
* Waits for 120 seconds of human inactivity before beginning automation cycles.

To target a specific browser, run from command line:
```cmd
RUN.bat firefox
RUN.bat chrome
RUN.bat edge
```

---

## 🛑 Instant Controls & Safety

* **Instant Human Yield**: The bot continuously polls Windows low-level input ticks (`GetLastInputInfo`). Any physical mouse movement or keypress immediately yields control back to you.
* **Emergency Halt**: Double-tap `ESC` anytime to halt active automation loops immediately.
* **Safe Clean-up**: Closing the command prompt window safely terminates all active background threads.

---

## 📂 Project Directory Structure

```text
python-automation/
├── INSTALL.bat              # One-click installer (elevates, sets up Python, .venv, driver, shortcut)
├── RUN.bat                  # One-click launcher (verifies driver, runs main bot)
├── uninstall_driver.bat     # Clean uninstaller for Interception kernel driver
├── requirements.txt         # Minimal dependency manifest
├── README.md                # This deployment guide
│
├── Interception/            # Interception kernel filter driver
│   ├── install-interception.exe # Official command-line driver installer binary
│   ├── README.md            # Driver documentation
│   └── library/             # x64 & x86 C/C++ libraries and header
│
└── final_bot/               # Modular bot engine
    ├── main_shorts.py       # Primary entry point (auto-detects installed browser)
    ├── main_firefox.py      # Entry point targeting Firefox
    ├── main_chrome.py       # Entry point targeting Chrome
    ├── main_edge.py         # Entry point targeting Edge
    ├── config/              # URLs, timing, and behavior parameters
    ├── core/                # Input drivers, human physics, killswitch, window manager
    ├── tasks/               # Web & desktop automation tasks
    └── docs/                # Architecture documentation
```

---

## ⚙️ System Requirements

* **Operating System**: Windows 10 or Windows 11 (64-bit)
* **Privileges**: Administrator privileges during the initial one-time driver install
* **Browsers Supported**: Brave, Google Chrome, Mozilla Firefox, Microsoft Edge
