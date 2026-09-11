from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from miezee.ai.ai_client import AIClient


class WorkerSignals(QObject):
    finished = Signal(str)
    failed = Signal(str)


class AIWorker(QRunnable):
    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt
        self.signals = WorkerSignals()
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    @Slot()
    def run(self) -> None:
        if self.cancelled:
            return
        try:
            response = AIClient().ask(self.prompt)
            if not self.cancelled:
                self.signals.finished.emit(response)
        except Exception as exc:
            if not self.cancelled:
                self.signals.failed.emit(f"Error inesperado: {exc}")
