import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sources import KCIClient, parse_kci, crossref_identity, extract_html, classify_duplicates


def response(total, content=""):
    return f"<response><result><total>{total}</total></result><outputData>{content}</outputData></response>".encode()


class SourcesTests(unittest.TestCase):
    def test_auth_word_in_valid_title_is_not_error(self):
        result = parse_kci(response(1, "<record><title>인증키 연구</title></record>"))
        self.assertEqual(result["status"], "ok")

    def test_provider_verified_secret_is_not_echoed(self):
        result = parse_kci(response(1, "<record><verified>secret-value</verified></record>"), "secret-value")
        self.assertNotIn("secret-value", json.dumps(result))
        self.assertIsNone(result["records"][0]["provider_verified"])

    def test_credential_aliases_and_unknown_params_rejected(self):
        for alias in ["KEY", "Api_Key", "APIKEY", "KCI_API_KEY", "Authorization"]:
            self.assertEqual(KCIClient().request("articleSearch", title="a", **{alias: "private"})["status"], "reserved_parameter")
        self.assertEqual(KCIClient().request("articleSearch", title="a", bogus="private")["status"], "unknown_parameter")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "checkpoint.json"
            with self.assertRaises(ValueError):
                KCIClient().collect("a", path, APIKEY="private")
            self.assertFalse(path.exists())

    def test_version_relations_preserved_and_wrong_doi_conflicts(self):
        a = {"paper_id": "P1", "doi": "https://doi.org/10.123/a", "title": "Study", "authors": ["Kim"], "year": 2020}
        b = {**a, "paper_id": "P2", "doi": "10.123/A"}
        self.assertEqual(classify_duplicates([a, b])["pairs"][0]["status"], "duplicate_candidate")
        b["title"] = "Other study"
        self.assertEqual(classify_duplicates([a, b])["pairs"][0]["status"], "identifier_conflict_review")
        b.update({"version_type": "translation", "related_to": ["P1"], "doi": "10.123/b"})
        result = classify_duplicates([a, b])
        self.assertEqual(result["pairs"][0]["status"], "related_versions_keep_distinct")
        self.assertEqual(len(result["records"]), 2)

    def test_auth_is_not_zero(self):
        self.assertEqual(parse_kci(b"<error>INVALID_KEY</error>")["status"], "authentication_error")
        self.assertEqual(parse_kci(response(0))["status"], "zero_results")
        self.assertEqual(parse_kci(b"bad XML")["status"], "malformed_xml")
        self.assertEqual(parse_kci(b"<html>upstream unavailable</html>")["status"], "unexpected_schema")

    @patch.dict(os.environ, {"KCI_API_KEY": "secret+/value"})
    def test_redacts_echoed_xml_and_url(self):
        client = KCIClient(fetch=lambda url: response(1, "<record><url>https://x?key=secret+/value</url><verified>Y</verified></record>"))
        result = client.request("articleSearch", title="교육")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["records"][0]["provider_verified"], "Y")
        self.assertEqual(result["records"][0]["evidence_verification"], "unreviewed")

    @patch.dict(os.environ, {"KCI_API_KEY": "NEVERLOG"})
    def test_network_exception_key_never_returned_and_retries_bounded(self):
        calls = []
        def fail(url):
            calls.append(url)
            raise OSError(url)
        result = KCIClient(fetch=fail, retries=99).request("articleSearch", title="a")
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["status"], "network_error")
        self.assertNotIn("NEVERLOG", json.dumps(result))

    @patch.dict(os.environ, {"KCI_API_KEY": "secret"})
    def test_interruption_and_resume_checkpoint(self):
        def interrupted(url):
            if "page=1&" in url:
                return response(2, "<record><title>one</title></record>")
            raise OSError("disconnected")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            checkpoint = Path(directory) / "search.json"
            first = KCIClient(fetch=interrupted, retries=0).collect("a", checkpoint, page_size=1)
            self.assertEqual(first["completed_pages"], [1])
            self.assertEqual(first["collected_count"], 1)
            self.assertEqual(first["status"], "network_error")
            calls = []
            def resumed(url):
                calls.append(url)
                return response(2, "<record><title>two</title></record>")
            final = KCIClient(fetch=resumed).collect("a", checkpoint, page_size=1)
            self.assertEqual(final["status"], "complete")
            self.assertEqual(final["collected_count"], 2)
            self.assertEqual(len(calls), 1)
            self.assertIn("page=2&", calls[0])
            self.assertNotIn("secret", checkpoint.read_text())

    def test_required_and_page_limits(self):
        client = KCIClient()
        self.assertEqual(client.request("referenceSearch")["status"], "missing_title")
        self.assertEqual(client.request("articleDetail")["status"], "missing_id")
        self.assertEqual(client.request("articleSearch", title="a", displayCount=101)["status"], "invalid_pagination")

    def test_existing_wrong_doi_conflicts(self):
        payload = {"message": {"DOI": "10.1/existing", "title": ["Different paper"], "author": [{"family": "Kim"}], "published": {"date-parts": [[2020]]}}}
        fetch = lambda url: json.dumps(payload).encode()
        result = crossref_identity("10.1/existing", "Desired paper", ["Kim"], 2020, fetch)
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(crossref_identity("10.1/existing", "Different paper", ["Kim"], 2020, fetch)["status"], "matched")
        self.assertEqual(crossref_identity("10.1/existing", "Different paper", [], 2020, fetch)["status"], "unverified")

    def test_html_preserves_locations_without_pages(self):
        result = extract_html("<h2>한계</h2><p>인과관계가 <b>아니다</b>.</p><script>do bad things</script><p>다음 문단</p>", "https://example.org/paper")
        self.assertEqual(result["blocks"][0]["text"], "인과관계가 아니다.")
        self.assertEqual(result["blocks"][0]["section"], "한계")
        self.assertEqual(result["blocks"][1]["paragraph"], 2)
        self.assertNotIn("page", result["blocks"][0])
        self.assertEqual(result["status"], "needs_reading_order_review")


if __name__ == "__main__":
    unittest.main()
