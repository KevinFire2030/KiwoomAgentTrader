import os
import unittest
from unittest.mock import patch

from app.config.settings import KiwoomSettings, SettingsError


class KiwoomSettingsTest(unittest.TestCase):
    def test_loads_required_kiwoom_environment(self):
        env = {
            "KIWOOM_APP_KEY": "app-key",
            "KIWOOM_SECRET_KEY": "secret-key",
            "KIWOOM_ACCOUNT_NO": "12345678",
            "KIWOOM_BASE_URL": "https://api.kiwoom.example",
            "TRADING_MODE": "paper",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = KiwoomSettings.from_env()

        self.assertEqual(settings.app_key, "app-key")
        self.assertEqual(settings.secret_key, "secret-key")
        self.assertEqual(settings.account_no, "12345678")
        self.assertEqual(settings.base_url, "https://api.kiwoom.example")
        self.assertEqual(settings.trading_mode, "paper")

    def test_rejects_live_mode_without_explicit_live_trading_flag(self):
        env = {
            "KIWOOM_APP_KEY": "app-key",
            "KIWOOM_SECRET_KEY": "secret-key",
            "KIWOOM_ACCOUNT_NO": "12345678",
            "TRADING_MODE": "live_manual",
            "ENABLE_LIVE_TRADING": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SettingsError):
                KiwoomSettings.from_env()


if __name__ == "__main__":
    unittest.main()
