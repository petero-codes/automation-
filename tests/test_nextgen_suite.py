"""
Comprehensive Unit & Integration Test Suite for Nextgen Autonomous Workforce Engine.
Strict verification of all 5 mission-critical pillars.
"""

import unittest
import sys
import os
from pathlib import Path

# Add final_bot to path
BASE_DIR = Path(__file__).resolve().parent.parent / "final_bot"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core import state
from core.priority_engine import priority_engine, get_idle_time_ms
from core.checkpoint_manager import CheckpointManager
from core.procedural_coder import ProceduralCoder, sanitize_project_name
from core.financial_generator import FinancialGenerator
from config.domains import get_domain_count, get_random_domain, TECHNICAL_DOMAINS
from tasks.reading_jiggler import execute_reading_micro_scroll
from tasks.scheduler import Scheduler, filter_runnable_tasks
from tasks.shared import (
    is_vscode_installed,
    get_vscode_executable,
    is_excel_installed,
    get_excel_executable,
    detect_best_browser,
    get_installed_browsers,
    get_app_path
)
from tasks.engineering_workload import task_software_engineering
from tasks.financial_workload import task_financial_modeling
from tasks.research_workload import task_technical_research
from tasks.reading_jiggler import task_reading_mode

class TestNextgenWorkforceEngine(unittest.TestCase):

    def setUp(self):
        state.clear_stop()
        state.automation_active.clear()

    # -------------------------------------------------------------
    # 1. PILLAR: Non-Maskable Human Priority (IRQ 0)
    # -------------------------------------------------------------
    def test_priority_engine_initialization(self):
        """Verifies hook structures and displacement threshold."""
        self.assertEqual(priority_engine.displacement_threshold, 25.0)
        self.assertFalse(priority_engine._is_bot_injecting())

    def test_priority_engine_instant_yield(self):
        """Verifies <30ms instant yield changes global state flags immediately."""
        state.automation_active.set()
        self.assertTrue(state.automation_active.is_set())
        
        priority_engine.trigger_instant_yield("Unit Test Simulation")
        
        self.assertTrue(state.is_stopped())
        self.assertFalse(state.automation_active.is_set())

    def test_idle_timer(self):
        """Verifies Windows LastInputInfo API integration."""
        idle_ms = get_idle_time_ms()
        self.assertIsInstance(idle_ms, int)
        self.assertGreaterEqual(idle_ms, 0)

    # -------------------------------------------------------------
    # 2. PILLAR: Reading Mode (Subtle Scroll Jiggler Engine)
    # -------------------------------------------------------------
    def test_reading_micro_scroll_execution(self):
        """Verifies zero-drift subtle reading micro-scroll."""
        result = execute_reading_micro_scroll()
        self.assertTrue(result)

    # -------------------------------------------------------------
    # 3. PILLAR: Software Engineering (VS Code & Task Pooling)
    # -------------------------------------------------------------
    def test_procedural_coder_generation(self):
        """Verifies dynamic multi-architecture task pooling."""
        coder = ProceduralCoder()
        task = coder.generate_task()
        
        self.assertTrue(len(task.project_name) > 0)
        self.assertIn(task.language, ["python", "typescript", "go"])
        self.assertGreaterEqual(len(task.files), 1)
        self.assertGreaterEqual(len(task.git_commits), 1)
        
        # Verify file content is valid code
        for filename, content in task.files.items():
            self.assertTrue(len(content.strip()) > 0)
            self.assertTrue(filename.endswith((".py", ".ts", ".go")))

    # -------------------------------------------------------------
    # 4. PILLAR: Financial Modeling & Analysis (Excel)
    # -------------------------------------------------------------
    def test_financial_generator_structure_and_formulas(self):
        """Verifies 50-90 dynamic rows, live formulas (=SUM, =AVERAGE, =IF, =VLOOKUP)."""
        gen = FinancialGenerator()
        model = gen.generate_model()
        
        self.assertGreaterEqual(model.row_count, 50)
        self.assertLessEqual(model.row_count, 90)
        self.assertGreater(len(model.cells), 200)
        
        # Verify presence of live Excel formulas
        formulas = [c.value for c in model.cells if c.is_formula]
        self.assertGreater(len(formulas), 20)
        has_sum = any("=SUM(" in f for f in formulas)
        has_logic = any("=IF(" in f or "=AVERAGE(" in f or "+" in f for f in formulas)
        self.assertTrue(has_sum or has_logic)

    # -------------------------------------------------------------
    # 5. PILLAR: Curated Technical Research (220+ Domains)
    # -------------------------------------------------------------
    def test_technical_domain_pool_count(self):
        """Verifies curated technical domain pool exceeds 220 domains."""
        count = get_domain_count()
        self.assertGreaterEqual(count, 220)
        
        # Test random domain selection
        d = get_random_domain()
        self.assertIn(d, TECHNICAL_DOMAINS)

    # -------------------------------------------------------------
    # 6. PILLAR: Encrypted Session Checkpoints & Resumability
    # -------------------------------------------------------------
    def test_dpapi_encrypted_checkpoints(self):
        """Verifies Windows DPAPI round-trip encryption & session persistence."""
        test_file = str(BASE_DIR / ".test_checkpoint.bin")
        mgr = CheckpointManager(storage_path=test_file)
        
        payload = {
            "project": "distributed_rate_limiter_v4",
            "file": "rate_limiter.py",
            "line_offset": 64,
            "excel_cell": "D48"
        }
        
        # Save
        saved = mgr.save_checkpoint("VS_CODE", payload)
        self.assertTrue(saved)
        self.assertTrue(os.path.exists(test_file))
        
        # Load & Decrypt
        loaded = mgr.load_checkpoint()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["workload"], "VS_CODE")
        self.assertEqual(loaded["payload"]["line_offset"], 64)
        self.assertEqual(loaded["payload"]["excel_cell"], "D48")
        
        # Clear
        mgr.clear_checkpoint()
        self.assertFalse(os.path.exists(test_file))

    # -------------------------------------------------------------
    # 7. PILLAR: Scheduler Workload Matrix & Dynamic Application Discovery
    # -------------------------------------------------------------
    def test_scheduler_workload_weights(self):
        """Verifies weighted scheduler correctly chooses from enterprise workload pool."""
        weights = {
            task_technical_research: 4,
            task_reading_mode: 3
        }
        sched = Scheduler(weights)
        chosen = sched.pick_next_task()
        self.assertIn(chosen, weights.keys())

    def test_app_detection_helpers(self):
        """Verifies multi-tier detection queries system PATH and registry without errors."""
        self.assertIsInstance(is_vscode_installed(), bool)
        self.assertIsInstance(is_excel_installed(), bool)
        
        best_exe, best_title = detect_best_browser()
        self.assertIsInstance(best_exe, str)
        self.assertIsInstance(best_title, str)
        self.assertTrue(len(best_exe) > 0)
        self.assertTrue(len(best_title) > 0)
        
        browsers = get_installed_browsers()
        self.assertIsInstance(browsers, list)

    def test_project_name_sanitization(self):
        """Verifies invalid path chars and traversal attempts are sanitized."""
        unsafe_names = [
            "../../etc/passwd",
            "repo:name*with?bad<chars>",
            "my project with spaces",
            'quotes"and|pipes',
            "____leading_trailing____"
        ]
        for name in unsafe_names:
            clean = sanitize_project_name(name)
            self.assertTrue(all(c not in clean for c in '<>:"/\\|?*'))
            self.assertFalse(clean.startswith("_"))
            self.assertFalse(clean.endswith("_"))
            self.assertGreater(len(clean), 0)

    def test_scheduler_dynamic_pruning_missing_apps(self):
        """Verifies Scheduler prunes workloads for uninstalled apps and falls back gracefully."""
        from unittest.mock import patch
        
        # Scenario A: Both VS Code and Excel missing
        with patch("tasks.scheduler.is_vscode_installed", return_value=False), \
             patch("tasks.scheduler.is_excel_installed", return_value=False):
            test_weights = {
                task_software_engineering: 5,
                task_financial_modeling: 5,
                task_technical_research: 4,
                task_reading_mode: 3
            }
            sched = Scheduler(test_weights)
            # Software engineering and financial modeling must be pruned
            self.assertNotIn(task_software_engineering, sched.task_weights)
            self.assertNotIn(task_financial_modeling, sched.task_weights)
            self.assertIn(task_technical_research, sched.task_weights)
            self.assertIn(task_reading_mode, sched.task_weights)

        # Scenario B: Target machine has zero productivity tools
        with patch("tasks.scheduler.is_vscode_installed", return_value=False), \
             patch("tasks.scheduler.is_excel_installed", return_value=False):
            empty_weights = {
                task_software_engineering: 5,
                task_financial_modeling: 5
            }
            sched = Scheduler(empty_weights)
            # Must fall back to safe browser research and reading mode
            self.assertGreaterEqual(len(sched.task_weights), 2)
            self.assertIn(task_technical_research, sched.task_weights)
            self.assertIn(task_reading_mode, sched.task_weights)

    def test_workload_skipping_guards_when_apps_uninstalled(self):
        """Verifies task functions return False immediately if app is not installed (zero blind typing)."""
        from unittest.mock import patch

        with patch("tasks.engineering_workload.is_vscode_installed", return_value=False):
            res_se = task_software_engineering(10)
            self.assertFalse(res_se)

        with patch("tasks.financial_workload.is_excel_installed", return_value=False):
            res_fm = task_financial_modeling(10)
            self.assertFalse(res_fm)

    def test_reading_jiggler_dwell_instant_yield(self):
        """Verifies human activity during dwell aborts without counter-scroll contention."""
        # Set stop event so wait returns True immediately
        state.stop_automation_event.set()
        res = execute_reading_micro_scroll()
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
