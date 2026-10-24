import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = str(BASE_DIR / 'idle_automation.log')

# Automation execution parameters
IDLE_TIMEOUT  = 120        # seconds of idle before initial workforce start
TOTAL_RUNTIME = 10 * 3600  # maximum runtime per session (10 hours)

# Code scrolling profile: notch_range, pause_range, back_prob, distract_prob, distract_range
SCROLL_PROFILES = {
    'code': ((1, 2), (2.0, 6.0), 0.10, 0.02, (5.0, 10.0)),
}
