import threading
import time
from pathlib import Path

from automation_core import run_automation


class JobManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.running = False
        self.completed = False
        self.logs = []
        self.stats = {
            "processed": 0,
            "sent": 0,
            "inactive": 0,
            "failed": 0,
        }
        self.reports = {}
        self.run_id = None

    def start(self, settings, run_id, report_urls):
        with self.lock:
            if self.running:
                return False, "Process is already running."

            self.stop_event = threading.Event()
            self.running = True
            self.completed = False
            self.logs = []
            self.stats = {
                "processed": 0,
                "sent": 0,
                "inactive": 0,
                "failed": 0,
            }
            self.reports = report_urls
            self.run_id = run_id
            self._add_log("Starting process...")

            self.thread = threading.Thread(
                target=self._run,
                args=(settings,),
                daemon=True,
            )
            self.thread.start()

        return True, "Process started."

    def stop(self):
        with self.lock:
            if not self.running:
                return False, "No process is running."
            self.stop_event.set()
            self._add_log("Stop requested. Current WhatsApp step will finish/close first.")
        return True, "Stop requested."

    def snapshot(self):
        with self.lock:
            reports = {}
            for key, report in self.reports.items():
                file_path = Path(report["path"])
                reports[key] = {
                    "label": report["label"],
                    "url": report["url"] if file_path.exists() else "",
                    "exists": file_path.exists(),
                }

            return {
                "running": self.running,
                "completed": self.completed,
                "run_id": self.run_id,
                "stats": dict(self.stats),
                "logs": list(self.logs),
                "reports": reports,
            }

    def _run(self, settings):
        try:
            run_automation(
                settings=settings,
                stop_event=self.stop_event,
                log=self._add_log,
                stats=self._update_stats,
            )
        finally:
            with self.lock:
                self.running = False
                self.completed = True

    def _add_log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        with self.lock:
            self.logs.append(f"[{timestamp}] {message}")
            self.logs = self.logs[-500:]

    def _update_stats(self, **values):
        with self.lock:
            self.stats.update(values)


job_manager = JobManager()
