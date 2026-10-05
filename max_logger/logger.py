from __future__ import annotations

import logging
import sys
from logging import FileHandler, Logger, StreamHandler
from pathlib import Path
from typing import Iterable

from .client import MaxClient
from .handlers import MaxLogHandler
from .recipients import normalize_recipients


class MaxLogger(Logger):
    def __init__(
        self,
        name: str,
        project_file: str,
        token: str,
        recipient_ids: Iterable[int],
        log_file: str | None = None,
        base_url: str = "https://platform-api2.max.ru",
        timeout: float = 60.0,
        encoding: str = "utf-8",
        notify_level: int = logging.ERROR,
        client: MaxClient | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(name, *args, **kwargs)

        self.propagate = False
        self.project_dir = Path(project_file).expanduser().resolve().parent
        self.log_file_path = self._resolve_log_file_path(log_file)
        self.recipients = normalize_recipients(recipient_ids)
        self.client = client or MaxClient(token=token, base_url=base_url, timeout=timeout)

        self.formatter = logging.Formatter(fmt=f"[%(asctime)s: -- {name} -- %(levelname)s] %(message)s")
        self.console_stream_handler = self._build_console_handler()
        self.file_handler = self._build_file_handler(encoding=encoding)
        self.max_handler = self._build_max_handler(notify_level=notify_level)

        self.addHandler(self.file_handler)
        self.addHandler(self.console_stream_handler)
        self.addHandler(self.max_handler)

    def _build_console_handler(self) -> StreamHandler:
        handler = StreamHandler(stream=sys.stdout)
        handler.setFormatter(self.formatter)
        return handler

    def _build_file_handler(self, encoding: str) -> FileHandler:
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        handler = FileHandler(self.log_file_path, encoding=encoding)
        handler.setFormatter(self.formatter)
        return handler

    def _build_max_handler(self, notify_level: int) -> MaxLogHandler:
        handler = MaxLogHandler(self.client, self.recipients)
        handler.setLevel(notify_level)
        handler.setFormatter(self.formatter)
        return handler

    def _resolve_log_file_path(self, log_file: str | None) -> Path:
        if log_file:
            path = Path(log_file).expanduser()
            if path.is_absolute():
                return path.resolve()
            return (self.project_dir / path).resolve()

        return self.project_dir / f"{self.name}.log"
