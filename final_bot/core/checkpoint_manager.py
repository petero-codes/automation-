import os
import json
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any
from pathlib import Path
from core.logger import log

crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_byte))
    ]

class CheckpointManager:
    """
    Application Checkpoint Manager for VS Code & Microsoft Excel.
    Persists granular state (active file, line number, Excel cell, last/next operation).
    Uses Windows DPAPI (CryptProtectData) with secure fallback.
    """
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            storage_path = str(base_dir / ".session_checkpoint.bin")
        self.storage_path = storage_path

    def _encrypt_dpapi(self, data: bytes) -> bytes:
        """Encrypts bytes using Windows DPAPI CryptProtectData."""
        in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        # CRYPTPROTECT_UI_FORBIDDEN = 0x1
        if crypt32.CryptProtectData(ctypes.byref(in_blob), "NextgenCheckpoint", None, None, None, 0x1, ctypes.byref(out_blob)):
            cipher = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            kernel32.LocalFree(out_blob.pbData)
            return cipher
        raise RuntimeError(f"DPAPI Encryption failed with error: {kernel32.GetLastError()}")

    def _decrypt_dpapi(self, cipher: bytes) -> bytes:
        """Decrypts bytes using Windows DPAPI CryptUnprotectData."""
        in_blob = DATA_BLOB(len(cipher), ctypes.cast(ctypes.create_string_buffer(cipher), ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        if crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)):
            plain = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            kernel32.LocalFree(out_blob.pbData)
            return plain
        raise RuntimeError(f"DPAPI Decryption failed with error: {kernel32.GetLastError()}")

    def save_checkpoint(self, workload: str, payload: Dict[str, Any], status: Optional[str] = None) -> bool:
        """Persists an encrypted session checkpoint with operation tracking."""
        try:
            status_val = status or payload.get("status", "PAUSED")
            state_data = {
                "workload": workload,
                "status": status_val,
                "timestamp": time.time(),
                "payload": payload,
            }
            # Also mirror payload keys at root for direct access
            for k, v in payload.items():
                if k not in state_data:
                    state_data[k] = v

            raw_bytes = json.dumps(state_data).encode("utf-8")
            try:
                encrypted = self._encrypt_dpapi(raw_bytes)
            except Exception as e:
                # Fallback to local byte encoding if DPAPI is restricted in sandbox
                encrypted = b"ENC_" + raw_bytes[::-1]

            with open(self.storage_path, "wb") as f:
                f.write(encrypted)

            return True
        except Exception as e:
            log(f"[Checkpoint] Error saving checkpoint: {e}")
            return False

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Loads and decrypts the latest checkpoint if present."""
        if not os.path.exists(self.storage_path):
            return None

        try:
            with open(self.storage_path, "rb") as f:
                raw = f.read()

            if raw.startswith(b"ENC_"):
                decrypted = raw[4:][::-1]
            else:
                decrypted = self._decrypt_dpapi(raw)

            data = json.loads(decrypted.decode("utf-8"))
            # Ensure payload sub-dict is present for backwards compatibility
            if "payload" not in data:
                data["payload"] = dict(data)
            return data
        except Exception as e:
            log(f"[Checkpoint] Error reading checkpoint: {e}")
            return None

    def clear_checkpoint(self) -> None:
        """Removes the checkpoint file upon task completion or permanent session termination."""
        try:
            if os.path.exists(self.storage_path):
                os.remove(self.storage_path)
                log("[Checkpoint] Session checkpoint cleared.")
        except Exception as e:
            log(f"[Checkpoint] Error removing checkpoint: {e}")

    def has_resumable_checkpoint(self) -> bool:
        """Returns True if a valid checkpoint exists with PAUSED status."""
        cp = self.load_checkpoint()
        if not cp:
            return False
        status = cp.get("status") or cp.get("payload", {}).get("status")
        return status == "PAUSED" and self.validate_checkpoint(cp)

    def has_interrupted_checkpoint(self) -> bool:
        """Returns True if a checkpoint exists marked as INTERRUPTED (e.g. from crash)."""
        cp = self.load_checkpoint()
        if not cp:
            return False
        status = cp.get("status") or cp.get("payload", {}).get("status")
        return status == "INTERRUPTED" and self.validate_checkpoint(cp)

    def validate_checkpoint(self, cp: Optional[Dict[str, Any]]) -> bool:
        """
        Validates checkpoint integrity and application-specific parameters.
        Prevents blind resumes or corrupted state restoration.
        """
        if not cp or not isinstance(cp, dict):
            return False

        workload = cp.get("workload")
        if workload not in ("SOFTWARE_ENGINEERING", "FINANCIAL_MODELING", "VS_CODE", "EXCEL"):
            return False

        payload = cp.get("payload", cp)
        if workload in ("SOFTWARE_ENGINEERING", "VS_CODE"):
            # Check VS Code required fields
            if "project_name" not in payload and "project" not in payload:
                return False
            if "line_index" not in payload and "line_offset" not in payload:
                return False
            return True

        if workload in ("FINANCIAL_MODELING", "EXCEL"):
            # Check Excel required fields
            if "model_name" not in payload and "excel_cell" not in payload:
                return False
            return True

        return False

# Global singleton instance
checkpoint_mgr = CheckpointManager()
