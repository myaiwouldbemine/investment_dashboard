from __future__ import annotations

import tempfile
import unittest

from src.utils.dashboard_access import validate_access_params


def u(text: str) -> str:
    return text.encode("ascii").decode("unicode_escape")


class DashboardAccessTests(unittest.TestCase):
    def test_validate_access_params_accepts_first_use_and_rejects_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = f"{tmp_dir}/nonce.db"
            secret = "secret"
            access_chat = "123"
            access_exp = "1700000120"
            access_nonce = "nonce-abc"
            access_sig = "d884ae77c9458695e08ea48dd6e00189f0f6bb5860d80724c34f5413e529b863"

            ok, _ = validate_access_params(
                access_chat=access_chat,
                access_exp=access_exp,
                access_nonce=access_nonce,
                access_sig=access_sig,
                secret=secret,
                nonce_db_path=db_path,
                now_epoch=1700000000,
            )
            self.assertTrue(ok)

            ok, reason = validate_access_params(
                access_chat=access_chat,
                access_exp=access_exp,
                access_nonce=access_nonce,
                access_sig=access_sig,
                secret=secret,
                nonce_db_path=db_path,
                now_epoch=1700000001,
            )
            self.assertFalse(ok)
            self.assertIn(u(r"\u5df2\u88ab\u4f7f\u7528"), reason)

    def test_validate_access_params_rejects_expired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ok, reason = validate_access_params(
                access_chat="123",
                access_exp="1700000000",
                access_nonce="nonce-xyz",
                access_sig="aee9c1eb578fd50c79431efcfb20b8678a07d8b5bdd75f181fcb21f4fbd5cc7c",
                secret="secret",
                nonce_db_path=f"{tmp_dir}/nonce.db",
                now_epoch=1700000001,
            )
            self.assertFalse(ok)
            self.assertIn(u(r"\u904e\u671f"), reason)


if __name__ == "__main__":
    unittest.main()
