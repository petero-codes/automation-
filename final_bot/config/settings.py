import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IDLE_TIMEOUT  = 120        # seconds idle before automation starts
TOTAL_RUNTIME = 10 * 3600  # max runtime (10 hours)
LOG_FILE      = str(BASE_DIR / 'idle_automation.log')
AUTO_LAUNCH_LOGGY = False  # Set to False: will NOT launch Loggy on startup, on ESC, or during 120s wait

# notch_range, pause_range, back_prob, distract_prob, distract_range
SCROLL_PROFILES = {
    'reading':  ((1, 3), (2.5, 6.5),  0.10, 0.02, (6.0, 12.0)),
    'scanning': ((2, 5), (1.0, 3.5),  0.05, 0.01, (4.0, 8.0)),
    'novel':    ((1, 2), (3.5, 8.5),  0.12, 0.03, (8.0, 15.0)),
    'code':     ((1, 2), (2.0, 6.0),  0.10, 0.02, (5.0, 10.0)),
}
