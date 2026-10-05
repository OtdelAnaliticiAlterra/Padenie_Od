from __future__ import annotations

from logging import Handler, LogRecord
from typing import Sequence

from .client import MaxClient
from .recipients import MaxRecipient

# MAX API отклоняет сообщения длиннее 4000 символов
# ("Field 'text' size (N) must be at most 4000"), поэтому вписываем текст
# в этот лимит. Считаем бюджет в байтах UTF-8 — это безопасно при любой
# трактовке лимита (и по символам, и по байтам).
MAX_MESSAGE_BYTES = 3900
TRUNCATION_MARKER = "\n\n... [часть сообщения обрезана: превышен лимит MAX] ...\n\n"


def _cut_to_bytes(text: str, max_bytes: int, keep_tail: bool) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    chunk = encoded[-max_bytes:] if keep_tail else encoded[:max_bytes]
    return chunk.decode("utf-8", errors="ignore")


def fit_message(text: str, max_bytes: int = MAX_MESSAGE_BYTES) -> str:
    """Вписать сообщение в лимит MAX, сохранив начало и конец текста."""
    if len(text.encode("utf-8")) <= max_bytes:
        return text

    budget = max_bytes - len(TRUNCATION_MARKER.encode("utf-8"))
    head_budget = budget // 2

    head = _cut_to_bytes(text, head_budget, keep_tail=False)
    tail = _cut_to_bytes(text, budget - head_budget, keep_tail=True)
    return head + TRUNCATION_MARKER + tail


class MaxLogHandler(Handler):
    def __init__(self, client: MaxClient, recipients: Sequence[MaxRecipient], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.recipients = tuple(recipients)

    def emit(self, record: LogRecord) -> None:
        if not self.recipients:
            return

        log_entry = fit_message(self.format(record))
        for recipient in self.recipients:
            try:
                self.client.send_message(text=log_entry, **recipient.as_request_kwargs())
            except Exception:
                self.handleError(record)
