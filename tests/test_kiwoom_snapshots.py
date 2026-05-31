import unittest

from app.kiwoom.snapshots import account_snapshot_from_response, market_snapshot_from_response, mask_account


class KiwoomSnapshotsTest(unittest.TestCase):
    def test_market_snapshot_parses_signed_price_and_change_rate(self):
        snapshot = market_snapshot_from_response(
            "498270",
            {"cntr_infr": [{"cur_prc": "+18600", "pre_rt": "+6.65"}], "return_code": 0},
        )

        self.assertEqual(snapshot.symbol, "498270")
        self.assertEqual(snapshot.current_price, 18600)
        self.assertEqual(snapshot.change_rate, 6.65)
        self.assertEqual(snapshot.source, "kiwoom_rest")

    def test_account_snapshot_parses_amounts_and_masks_account(self):
        snapshot = account_snapshot_from_response(
            "63617796",
            {
                "prsm_dpst_aset_amt": "000000000303493",
                "tot_evlt_amt": "000000000100000",
                "acnt_evlt_remn_indv_tot": [{"stk_cd": "498270"}],
            },
        )

        self.assertEqual(snapshot.account_no_masked, "63***96")
        self.assertEqual(snapshot.deposit_asset_amount, 303493)
        self.assertEqual(snapshot.total_evaluation_amount, 100000)
        self.assertEqual(snapshot.positions_count, 1)

    def test_mask_account_handles_short_values(self):
        self.assertEqual(mask_account("1234"), "****")


if __name__ == "__main__":
    unittest.main()
