from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.approval.workflow import ApprovalWorkflow
from app.storage.repository import TradingRepository


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/handle_approval_command.py '승인 TT-...' [paper]")
        raise SystemExit(2)
    text = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "paper"
    repo = TradingRepository(Path("data") / "trading.db")
    repo.initialize()
    result = ApprovalWorkflow(repo).handle_text(text, mode=mode)
    print(result.message)
    if not result.accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
