import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import instagram_token_check as token_check


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.ok = 200 <= status < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


class InstagramTokenCheckTests(unittest.TestCase):
    def test_validates_profile_and_media_permissions(self):
        session = FakeSession([
            FakeResponse(200, {"id": "123", "username": "brasileirao"}),
            FakeResponse(200, {"data": []}),
        ])

        username = token_check.validate_token("123", "secret", "v23.0", session)

        self.assertEqual(username, "brasileirao")
        self.assertEqual(len(session.calls), 2)
        self.assertTrue(session.calls[1][0].endswith("/media"))

    def test_failure_is_actionable_without_leaking_message_or_token(self):
        session = FakeSession([
            FakeResponse(400, {"error": {
                "message": "Invalid token secret-value",
                "type": "OAuthException",
                "code": 190,
                "error_subcode": 463,
            }}),
        ])

        with self.assertRaises(token_check.CredentialValidationError) as raised:
            token_check.validate_token("123", "secret-value", "v23.0", session)

        detail = str(raised.exception)
        self.assertEqual(detail, "HTTP 400, type OAuthException, code 190, subcode 463")
        self.assertNotIn("Invalid token", detail)
        self.assertNotIn("secret-value", detail)

    def test_missing_token_fails_before_any_request(self):
        session = FakeSession([])
        with self.assertRaisesRegex(token_check.CredentialValidationError, "not configured"):
            token_check.validate_token("123", "", "v23.0", session)
        self.assertEqual(session.calls, [])


if __name__ == "__main__":
    unittest.main()
