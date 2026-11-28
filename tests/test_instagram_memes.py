import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("memes", Path(__file__).resolve().parents[1] / "scripts/instagram_memes.py")
memes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memes)


class PublicationSafety(unittest.TestCase):
    def test_legacy_single_game_post_reserves_whole_round(self):
        blocks = {
            "isolated": {"match_keys": ['[35, "A", "B"]']},
            "main": {"match_keys": ['[35, "C", "D"]', '[35, "E", "F"]', '[35, "G", "H"]']},
            "next": {"match_keys": ['[36, "C", "D"]']},
        }
        for status in ("published", "publish_requested", "creating_containers"):
            state = {"isolated": {"state": status}}
            self.assertTrue(memes.round_already_claimed("main", blocks, state))
            self.assertFalse(memes.round_already_claimed("next", blocks, state))

    def test_explicit_round_receipt_and_own_resume(self):
        blocks = {"main": {"match_keys": ['[35, "C", "D"]']}}
        self.assertTrue(memes.round_already_claimed(
            "main", blocks, {"old": {"round_key": "2026:35", "state": "published"}}))
        self.assertTrue(memes.round_already_claimed(
            "main", blocks, {"main": {"state": "published"}}))
        self.assertFalse(memes.round_already_claimed(
            "main", blocks, {"main": {"state": "container_ready"}}))

    def test_unknown_or_mixed_round_fails_closed(self):
        for block in ({}, {"match_keys": []}, {"match_keys": ['[35, "A", "B"]', '[36, "C", "D"]']}):
            with self.assertRaises(memes.PublishError):
                memes.round_key(block)

    def test_isolated_games_and_repeated_featured_game_are_rejected(self):
        matches = [{"round": 35, "home": home, "away": away, "score": "1 x 0"}
                   for home, away in (("A", "B"), ("C", "D"), ("E", "F"))]
        all_keys = [memes.json.dumps([m["round"], m["home"], m["away"]]) for m in matches]
        for count, error in ((1, "at least three"), (2, "at least three"), (3, "different game")):
            keys = all_keys[:count]
            block_id = memes.hashlib.sha256("\n".join(sorted(keys)).encode()).hexdigest()[:20]
            block = {"outcome": "published", "media_id": "summary",
                     "published_at": "2026-11-01T12:00:00-03:00", "match_keys": keys}
            manifest = {"block_id": block_id, "summary_media_id": "summary", "match_keys": keys,
                        "account_id": memes.ACCOUNT, "api_profile_id": memes.PROFILE,
                        "username": memes.USERNAME,
                        "images": [{"file": f"{i}.jpg", "match_key": keys[0]} for i in range(3)]}
            with patch.object(memes, "read_json", return_value=manifest):
                with self.assertRaisesRegex(memes.PublishError, error):
                    memes.validate_manifest(Path("unused"), block_id, block, matches)

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

    def test_final_receipt_is_verified_without_being_rewritten(self):
        api = Mock()
        api.request.return_value = {
            "media_type": "CAROUSEL_ALBUM",
            "permalink": "https://www.instagram.com/p/existing/",
            "children": {"data": [{"id": str(i), "media_type": "IMAGE"} for i in range(3)]},
        }
        manifest = {"block_id": "a" * 20, "caption": "Same caption"}
        recent = [
            {"id": "summary", "permalink": "https://www.instagram.com/p/summary/"},
            {"id": "existing", "caption": "Same caption"},
        ]
        state = {
            "state": "published",
            "summary_media_id": "summary",
            "summary_permalink": "https://www.instagram.com/p/summary/",
            "caption_sha256": memes.hashlib.sha256(b"Same caption").hexdigest(),
            "carousel_id": "existing",
            "permalink": "https://www.instagram.com/p/existing/",
            "child_media_ids": ["0", "1", "2"],
            "slides": 3,
            "published_at": "2026-10-13T23:53:54+00:00",
        }

        with patch.object(memes, "read_json", return_value={"a" * 20: state}), patch.object(memes, "checkpoint") as save:
            memes.publish_one(api, manifest, Path("unused"), {"media_id": "summary"}, recent, "b" * 40)

        save.assert_not_called()
        api.request.assert_called_once_with(
            "GET", "existing", fields="id,media_type,permalink,children.limit(10){id,media_type}"
        )

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
