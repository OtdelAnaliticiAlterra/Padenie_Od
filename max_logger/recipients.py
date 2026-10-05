from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CHAT_RECIPIENT_TYPE = "chat_id"
USER_RECIPIENT_TYPE = "user_id"


@dataclass(frozen=True)
class MaxRecipient:
    recipient_type: str
    recipient_id: int

    def as_request_kwargs(self) -> dict[str, int]:
        return {self.recipient_type: self.recipient_id}


def normalize_recipients(recipient_ids: Iterable[int] | None = None) -> list[MaxRecipient]:
    recipients: list[MaxRecipient] = []
    seen: set[tuple[str, int]] = set()

    for raw_id in recipient_ids or ():
        recipient_id = int(raw_id)
        if recipient_id == 0:
            raise ValueError("Recipient id cannot be 0.")

        recipient_type = CHAT_RECIPIENT_TYPE if recipient_id < 0 else USER_RECIPIENT_TYPE
        key = (recipient_type, recipient_id)
        if key in seen:
            continue

        seen.add(key)
        recipients.append(MaxRecipient(recipient_type=recipient_type, recipient_id=recipient_id))

    return recipients
