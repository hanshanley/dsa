import base64
import gzip
import io
import unittest
import zipfile

from dsa_analysis.publication_security import literal_pattern, sanitize


class PublicationSecurityTests(unittest.TestCase):
    def test_provider_key_is_removed_without_changing_policy_text(self):
        key = b"AI" + b"za" + b"A" * 35
        raw = b'<p>Fund schools.</p><script>apiKey="' + key + b'"</script>'
        clean, counts = sanitize(raw)
        self.assertNotIn(key, clean)
        self.assertIn(b"<p>Fund schools.</p>", clean)
        self.assertEqual(len(clean), len(raw))
        self.assertTrue(counts)
        self.assertEqual(sanitize(clean)[0], clean)

    def test_signed_links_and_generic_config_values_are_removed(self):
        value = b"abcde12345fghij67890klmno"
        raw = b'https://example.org/file?sv=2026&sig=' + value + b'&sr=b'
        clean, _ = sanitize(raw)
        self.assertNotIn(value, clean)
        self.assertIn(b"&sr=b", clean)
        raw = b'{"client_secret":"' + value + b'","datePublished":"2020-01-01"}'
        clean, _ = sanitize(raw)
        self.assertNotIn(value, clean)
        self.assertIn(b'"datePublished":"2020-01-01"', clean)

    def test_encoded_and_compressed_captures_are_sanitized(self):
        key = b"AI" + b"za" + b"B" * 35
        encoded = base64.b64encode(b'{"apiKey":"' + key + b'","message":"Preserve this."}')
        cleaned, _ = sanitize(encoded)
        self.assertNotIn(key, base64.b64decode(cleaned))
        self.assertIn(b"Preserve this.", base64.b64decode(cleaned))
        compressed = gzip.compress(b"<p>Housing.</p>" + key)
        cleaned, _ = sanitize(compressed)
        self.assertNotIn(key, gzip.decompress(cleaned))
        self.assertIn(b"<p>Housing.</p>", gzip.decompress(cleaned))

    def test_nested_archive_keeps_paths_and_noncredential_content(self):
        key = b"AI" + b"za" + b"C" * 35
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("source.html", b"<p>Public transit.</p>" + key)
        cleaned, _ = sanitize(stream.getvalue())
        with zipfile.ZipFile(io.BytesIO(cleaned)) as archive:
            content = archive.read("source.html")
        self.assertNotIn(key, content)
        self.assertIn(b"Public transit.", content)

    def test_private_scanner_values_are_not_needed_in_public_code(self):
        value = b"opaque-" + b"x9z2" * 9
        clean, _ = sanitize(b'{"custom":"'+value+b'"}', literal_pattern([value]))
        self.assertNotIn(value, clean)
        self.assertIn(b"REDACTED", clean)


if __name__ == "__main__":
    unittest.main()
