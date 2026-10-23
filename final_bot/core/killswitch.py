import ctypes
import threading
import time
from core import state
from core.logger import log
from core.input_driver import emergency_cleanup
from core.priority_engine import priority_engine, get_idle_time_ms, start_priority_engine, stop_priority_engine

def set_ignore_until(t):
    pass

def start_daemons():
    """Starts the sub-30ms Non-Maskable Human Priority Engine."""
    start_priority_engine()
