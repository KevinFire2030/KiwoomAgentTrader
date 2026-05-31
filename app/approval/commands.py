from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ApprovalAction = Literal["approve", "reject"]


@dataclass(frozen=True)
class ApprovalCommand:
    action: ApprovalAction
    ticket_id: str


_APPROVAL_PATTERN = re.compile(r"^\s*(승인|approve)\s+([A-Za-z0-9_-]+)\s*$", re.IGNORECASE)
_REJECTION_PATTERN = re.compile(r"^\s*(거절|reject)\s+([A-Za-z0-9_-]+)\s*$", re.IGNORECASE)


def parse_approval_command(text: str) -> ApprovalCommand | None:
    approval = _APPROVAL_PATTERN.match(text or "")
    if approval:
        return ApprovalCommand("approve", approval.group(2))
    rejection = _REJECTION_PATTERN.match(text or "")
    if rejection:
        return ApprovalCommand("reject", rejection.group(2))
    return None
