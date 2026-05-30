import unittest

from app.workflows.intraday_signal_scan import run_intraday_signal_scan


class WorkflowTest(unittest.TestCase):
    def test_paper_workflow_generates_approved_ticket_for_498270(self):
        result = run_intraday_signal_scan("498270", mode="paper")
        self.assertTrue(result.risk_review.approved)
        self.assertIsNotNone(result.ticket)
        self.assertIn("paper_order_recorded", result.report)


if __name__ == "__main__":
    unittest.main()
