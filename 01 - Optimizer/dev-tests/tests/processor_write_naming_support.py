from __future__ import annotations

from pathlib import Path
import hashlib

from ingestion_layer_vision.processor import (
    Processor,
    _MAX_ASSET_KEY_LENGTH,
    _MAX_OUTPUT_SLUG_LENGTH,
    _OUTPUT_CLAIM_SUFFIX,
)


class TestNormalizeOutputSeed:
    def test_normalize_output_seed_backslash(self):
        assert Processor._normalize_output_seed("foo\\bar\\baz") == "foo/bar/baz"

    def test_normalize_output_seed_empty(self):
        assert Processor._normalize_output_seed("") == "extract"

    def test_normalize_output_seed_whitespace_only(self):
        assert Processor._normalize_output_seed("  / /  ")


class TestSanitizeOutputFragment:
    def test_sanitize_output_fragment_removes_slashes(self):
        assert Processor._sanitize_output_fragment("a/b/c") == "a__b__c"

    def test_sanitize_output_fragment_strips_special(self):
        result = Processor._sanitize_output_fragment("...test---")
        assert not result.startswith((".", "_", "-"))
        assert not result.endswith((".", "_", "-"))

    def test_sanitize_output_fragment_all_special_returns_extract(self):
        assert Processor._sanitize_output_fragment("///") == "extract"


class TestShortOutputToken:
    def test_short_output_token_valid_hash(self):
        assert Processor._short_output_token("sha256:" + "ab" * 32, "fallback") == "abababab"

    def test_short_output_token_invalid_hash_uses_fallback(self):
        expected = hashlib.sha256("my_seed".encode("utf-8")).hexdigest()[:8]
        assert Processor._short_output_token("", "my_seed") == expected

    def test_short_output_token_no_prefix_valid_hex(self):
        assert Processor._short_output_token("ab" * 32, "x") == "abababab"


class TestBuildOutputSlug:
    def test_build_output_slug_short_no_truncation(self):
        slug = Processor._build_output_slug("test.pdf", "sha256:" + "ab" * 32)
        assert len(slug) <= _MAX_OUTPUT_SLUG_LENGTH

    def test_build_output_slug_truncation(self):
        long_path = "a" * 200 + ".pdf"
        slug = Processor._build_output_slug(long_path, "sha256:" + "ab" * 32)
        assert len(slug) <= _MAX_OUTPUT_SLUG_LENGTH
        assert "abababab" in slug


class TestBuildAssetKey:
    def test_build_asset_key_max_length(self):
        long_path = "x" * 200 + ".pdf"
        asset_key = Processor._build_asset_key(long_path, "sha256:" + "ab" * 32)
        assert len(asset_key) <= _MAX_ASSET_KEY_LENGTH

    def test_build_asset_key_short_path(self):
        asset_key = Processor._build_asset_key("test.pdf", "sha256:" + "ab" * 32)
        parts = asset_key.rsplit(".", 1)
        assert len(parts) == 2
        assert parts[1] == "abababab"


class TestIterOutputCandidates:
    def test_iter_output_candidates_correct_sequence(self):
        candidates = list(Processor._iter_output_candidates(Path("/out"), "slug", "", "abcd1234"))
        assert candidates[0] == Path("/out/slug.raw.json")
        assert candidates[1] == Path("/out/slug.abcd1234.raw.json")
        assert candidates[2] == Path("/out/slug.abcd1234.01.raw.json")
        assert candidates[-1] == Path("/out/slug.abcd1234.64.raw.json")
        assert len(candidates) == 2 + 64

    def test_iter_output_candidates_with_page_suffix(self):
        candidates = list(Processor._iter_output_candidates(Path("/out"), "slug", "_p05", "abcd1234"))
        for candidate in candidates:
            assert str(candidate).endswith("_p05.raw.json")

    def test_iter_output_candidates_budget_windows_path_length_for_deep_parent(self):
        deep_parent = Path("C:/") / Path(*(["very_deep_segment"] * 8))
        candidates = list(Processor._iter_output_candidates(deep_parent, "x" * 220, "_p01", "abcd1234"))

        assert candidates
        assert all(len(str(candidate)) <= 259 - len(_OUTPUT_CLAIM_SUFFIX) for candidate in candidates)
        assert len({candidate.name for candidate in candidates}) == len(candidates)
