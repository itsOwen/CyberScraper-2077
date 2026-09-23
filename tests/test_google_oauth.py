import os
import unittest
from unittest.mock import patch

from src.utils import google_sheets_utils as sheets


class OAuthStateTests(unittest.TestCase):
    def setUp(self):
        sheets._pending_oauth_states.clear()

    def test_known_state_returns_code_verifier_once(self):
        sheets.remember_oauth_state("state-1", "verifier-1")
        self.assertEqual(sheets.pop_pending_oauth_state("state-1"), "verifier-1")
        self.assertIsNone(sheets.pop_pending_oauth_state("state-1"))

    def test_unknown_or_missing_state_is_rejected(self):
        sheets.remember_oauth_state("state-1", "verifier-1")
        self.assertIsNone(sheets.pop_pending_oauth_state("forged"))
        self.assertIsNone(sheets.pop_pending_oauth_state(None))

    def test_expired_state_is_rejected(self):
        with patch.object(sheets.time, "time", return_value=1000.0):
            sheets.remember_oauth_state("state-1", "verifier-1")
        with patch.object(sheets.time, "time", return_value=1000.0 + sheets.OAUTH_STATE_TTL_SECONDS + 1):
            self.assertIsNone(sheets.pop_pending_oauth_state("state-1"))

    def test_flow_without_pkce_still_counts_as_known(self):
        sheets.remember_oauth_state("state-1", None)
        self.assertEqual(sheets.pop_pending_oauth_state("state-1"), "")


class RedirectUriTests(unittest.TestCase):
    def _options(self, port, base_path):
        return lambda name: {"server.port": port, "server.baseUrlPath": base_path}[name]

    @patch.dict(os.environ, {}, clear=True)
    def test_default_matches_the_uri_from_the_readme(self):
        with patch.object(sheets.st, "get_option", side_effect=self._options(8501, "")):
            self.assertEqual(sheets.get_redirect_uri(), "http://localhost:8501/")

    @patch.dict(os.environ, {}, clear=True)
    def test_base_path_and_port(self):
        with patch.object(sheets.st, "get_option", side_effect=self._options(8502, "/scraper/")):
            self.assertEqual(sheets.get_redirect_uri(), "http://localhost:8502/scraper/")

    @patch.dict(os.environ, {"GOOGLE_OAUTH_REDIRECT_URI": "https://scraper.example.com/"}, clear=True)
    def test_env_override(self):
        self.assertEqual(sheets.get_redirect_uri(), "https://scraper.example.com/")


if __name__ == "__main__":
    unittest.main()
