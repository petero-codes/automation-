import threading

# Global state for cross-module communication
automation_active = threading.Event()
stop_automation_event = threading.Event()
resume_requested_event = threading.Event()

# Lock to distinguish bot keystrokes from human keystrokes
injecting_key = threading.Lock()

def is_stopped():
    return stop_automation_event.is_set()

def request_stop():
    stop_automation_event.set()

def clear_stop():
    stop_automation_event.clear()

def is_resume_requested():
    return resume_requested_event.is_set()

def request_resume():
    resume_requested_event.set()

def clear_resume():
    resume_requested_event.clear()
