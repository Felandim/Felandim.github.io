import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("memes", Path(__file__).resolve().parents[1] / "scripts/instagram_memes.py")
memes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memes)


class PublicationSafety(unittest.TestCase):
    def test_activation_and_actual_publication_are_required(self):
        valid = {"outcome": "published", "media_id": "123", "published_at": "2026-10-13T16:00:00-03:00"}
        self.assertTrue(memes.eligible(valid))
        for invalid in ({**valid, "outcome": "started"}, {**valid, "media_id": ""},
                        {**valid, "published_at": "2026-10-13T15:09:40-03:00"}):
            self.assertFalse(memes.eligible(invalid))

    def test_uncertain_publication_is_never_retried(self):
        api = Mock()
        manifest = {"block_id": "a" * 20, "caption": "New caption"}
        block = {"media_id": "summary"}
        recent = [{"id": "summary", "permalink": "https://www.instagram.com/p/summary/"}]
        for state in ("publish_requested", "published_pending_verification", "published"):
            with patch.object(memes, "read_json", return_value={"a" * 20: {"state": state}}):
                with self.assertRaises(memes.PublishError):
                    memes.publish_one(api, manifest, Path("unused"), block, recent, "b" * 40)
        api.request.assert_not_called()

    def test_actual_duplicate_recovers_receipt_without_post(self):
        api = Mock()
        api.request.return_value = {"media_type": "CAROUSEL_ALBUM", "permalink": "https://www.instagram.com/p/existing/",
                                   "children": {"data": [{"id": str(i), "media_type": "IMAGE"} for i in range(3)]}}
        manifest = {"block_id": "a" * 20, "caption": "New caption"}
        recent = [{"id": "summary", "permalink": "https://www.instagram.com/p/summary/"},
                  {"id": "existing", "caption": "New caption"}]
        with patch.object(memes, "read_json", return_value={}), patch.object(memes, "checkpoint") as save:
            memes.publish_one(api, manifest, Path("unused"), {"media_id": "summary"}, recent, "b" * 40)
        self.assertTrue(all(call.args[0] == "GET" for call in api.request.call_args_list))
        self.assertEqual(save.call_args.kwargs["state"], "published")
        self.assertEqual(save.call_args.kwargs["carousel_id"], "existing")

    def test_carousel_requires_three_images_and_permalink(self):
        api = Mock()
        base = {"media_type": "CAROUSEL_ALBUM", "permalink": "https://www.instagram.com/p/ok/",
                "children": {"data": [{"id": str(i), "media_type": "IMAGE"} for i in range(3)]}}
        for invalid in ({**base, "permalink": ""}, {**base, "media_type": "IMAGE"},
                        {**base, "children": {"data": base["children"]["data"][:2]}},
                        {**base, "children": {"data": [{"id": str(i), "media_type": "VIDEO"} for i in range(3)]}}):
            api.request.return_value = invalid
            with self.assertRaises(memes.PublishError):
                memes.verified_media(api, "existing")

    def test_account_mismatch_stops_before_media_listing(self):
        api = Mock()
        api.request.return_value = {"id": "different", "username": memes.USERNAME}
        with self.assertRaises(memes.PublishError):
            memes.account_media(api)
        self.assertEqual(api.request.call_count, 1)

    def test_duplicate_scan_reads_past_first_page(self):
        api = Mock()
        api.request.side_effect = [{"id": memes.PROFILE, "username": memes.USERNAME},
                                   {"data": [{"id": "new"}], "paging": {"next": "ignored", "cursors": {"after": "cursor"}}},
                                   {"data": [{"id": "old"}]}]
        self.assertEqual([x["id"] for x in memes.account_media(api)], ["new", "old"])
        self.assertEqual(api.request.call_args.kwargs["after"], "cursor")

    def test_missing_summary_stops_before_any_creation(self):
        api = Mock()
        with self.assertRaises(memes.PublishError):
            memes.publish_one(api, {"block_id": "a" * 20, "caption": "caption"}, Path("unused"), {"media_id": "missing"}, [], "b" * 40)
        api.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
