"""Tests for SEC FSDS segment normalization.

Tests validate that segment names are normalized correctly to canonical
snake_case names for continuity across years and readability.
"""

import polars as pl

from pipelines.assets.sec.fsds import (
    SEGMENT_NAME_PATTERNS,
    build_segment_name_expr,
    normalize_segment_name,
)


class TestSegmentNormalization:
    """Tests for normalize_segment_name function."""

    # =========================================================================
    # McDonald's validation tests (US segment continuity)
    # =========================================================================

    def test_mcd_us_segment_continuous(self):
        """All MCD US variations should normalize to 'us'."""
        us_variations = ["US", "UnitedStates", "USMarket", "U.S.Market"]
        for raw in us_variations:
            got = normalize_segment_name(raw)
            want = "us"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_mcd_intl_operated_segments(self):
        """MCD international operated markets should normalize."""
        got = normalize_segment_name("InternationalOperatedMarkets")
        want = "intl_operated"
        assert got == want

    def test_mcd_intl_licensed_segments(self):
        """MCD international licensed markets (long name) should normalize."""
        raw = "InternationalDevelopmentalLicensedMarketsandCorporate"
        got = normalize_segment_name(raw)
        want = "intl_licensed"
        assert got == want

    # =========================================================================
    # Starbucks validation tests (geographic segments)
    # =========================================================================

    def test_sbux_us_geographic(self):
        """SBUX US geographic segment."""
        got = normalize_segment_name("US")
        want = "us"
        assert got == want

    def test_sbux_china_from_cn(self):
        """SBUX CN should normalize to 'china'."""
        got = normalize_segment_name("CN")
        want = "china"
        assert got == want

    def test_sbux_international(self):
        """SBUX NonUs should normalize to 'international'."""
        got = normalize_segment_name("NonUs")
        want = "international"
        assert got == want

    # =========================================================================
    # Apple validation tests
    # =========================================================================

    def test_aapl_greater_china(self):
        """AAPL GreaterChina should normalize to 'china'."""
        got = normalize_segment_name("GreaterChina")
        want = "china"
        assert got == want

    def test_aapl_americas(self):
        """AAPL Americas should normalize to 'americas'."""
        got = normalize_segment_name("Americas")
        want = "americas"
        assert got == want

    def test_aapl_europe(self):
        """AAPL Europe should normalize to 'europe'."""
        got = normalize_segment_name("Europe")
        want = "europe"
        assert got == want

    # =========================================================================
    # 2-letter country code tests
    # =========================================================================

    def test_two_letter_codes_fallback_to_snake_case(self):
        """2-letter country codes not in patterns fall through to snake_case."""
        # These aren't in the explicit patterns, so they get snake_case fallback
        codes = ["CA", "GB", "JP", "DE", "FR"]
        for code in codes:
            got = normalize_segment_name(code)
            # Fallback just lowercases
            want = code.lower()
            assert got == want, f"Expected '{code}' → '{want}', got '{got}'"

    # =========================================================================
    # Fallback snake_case conversion tests
    # =========================================================================

    def test_fallback_camelcase_to_snake_case(self):
        """Unknown CamelCase names should convert to snake_case."""
        test_cases = [
            ("RetailBanking", "retail_banking"),
            ("ConsumerProducts", "consumer_products"),
            ("WealthManagement", "wealth_management"),
        ]
        for raw, want in test_cases:
            got = normalize_segment_name(raw)
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_fallback_removes_member_suffix(self):
        """Unknown names should have 'Member' suffix removed."""
        got = normalize_segment_name("NorthAmericaMember")
        assert "member" not in got.lower(), f"Expected 'Member' removed, got '{got}'"

    def test_fallback_shortens_international(self):
        """Fallback should shorten 'International' to 'intl'."""
        got = normalize_segment_name("InternationalSales")
        assert "intl" in got, f"Expected 'intl' in result, got '{got}'"
        assert "international" not in got, "Expected 'International' shortened"

    # =========================================================================
    # Common pattern tests
    # =========================================================================

    def test_corporate_variations(self):
        """Corporate variations should normalize to 'corporate'."""
        variations = ["Corporate", "CorporateAndOther", "CorporateNon"]
        for raw in variations:
            got = normalize_segment_name(raw)
            want = "corporate"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_other_variations(self):
        """Other variations should normalize to 'other'."""
        variations = ["Other", "AllOther", "AllOtherSegments"]
        for raw in variations:
            got = normalize_segment_name(raw)
            want = "other"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_eliminations(self):
        """Elimination segments should normalize to 'eliminations'."""
        got = normalize_segment_name("Eliminations")
        want = "eliminations"
        assert got == want

        got = normalize_segment_name("InterSegmentElimination")
        want = "eliminations"
        assert got == want

    def test_asia_pacific_variations(self):
        """Asia Pacific variations should normalize."""
        variations = ["AsiaPacific", "APAC", "Asia"]
        for raw in variations:
            got = normalize_segment_name(raw)
            want = "asia_pacific"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_latin_america_variations(self):
        """Latin America variations should normalize."""
        variations = ["LatinAmerica", "LATAM", "SouthAmerica"]
        for raw in variations:
            got = normalize_segment_name(raw)
            want = "latin_america"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    def test_rest_of_world_variations(self):
        """Rest of World variations should normalize."""
        variations = ["RestOfWorld", "RestOfTheWorld", "AllOtherCountries"]
        for raw in variations:
            got = normalize_segment_name(raw)
            want = "rest_of_world"
            assert got == want, f"Expected '{raw}' → '{want}', got '{got}'"

    # =========================================================================
    # Meta-segment filtering tests
    # =========================================================================

    def test_meta_segments_return_none(self):
        """Meta-segments like OperatingSegments should return None (filter out)."""
        meta_segments = ["OperatingSegments", "ReportableSegments", "SingleReportable"]
        for raw in meta_segments:
            got = normalize_segment_name(raw)
            assert got is None, f"Expected '{raw}' → None, got '{got}'"


class TestBuildSegmentNameExpr:
    """Tests for the Polars expression builder."""

    def test_expr_handles_multiple_rows(self):
        """Expression should work on multiple rows efficiently."""
        df = pl.DataFrame({
            "segment_name": [
                "US",
                "China",
                "Europe",
                "UnknownSegment",
                "OperatingSegments",
            ]
        })
        result = df.with_columns(build_segment_name_expr().alias("canonical"))

        expected = ["us", "china", "europe", "unknown_segment", "_FILTER_OUT_"]
        got = result["canonical"].to_list()
        assert got == expected

    def test_expr_preserves_lazy_evaluation(self):
        """Expression should work in lazy context."""
        lf = pl.LazyFrame({"segment_name": ["US", "NonUs", "Corporate"]})
        result = lf.with_columns(build_segment_name_expr().alias("canonical")).collect()

        expected = ["us", "international", "corporate"]
        got = result["canonical"].to_list()
        assert got == expected


class TestPatternConstants:
    """Tests for pattern constant structure."""

    def test_patterns_are_tuples(self):
        """Patterns should be list of (regex, canonical) tuples."""
        assert len(SEGMENT_NAME_PATTERNS) > 0
        for pattern in SEGMENT_NAME_PATTERNS:
            assert isinstance(pattern, tuple), f"Pattern not a tuple: {pattern}"
            assert len(pattern) == 2, f"Pattern not 2-tuple: {pattern}"

    def test_canonical_names_are_snake_case(self):
        """All canonical names should be snake_case (lowercase with underscores)."""
        for _pattern, canonical in SEGMENT_NAME_PATTERNS:
            # Skip _FILTER_OUT_ sentinel
            if canonical == "_FILTER_OUT_":
                continue
            # Should be all lowercase
            assert canonical == canonical.lower(), f"'{canonical}' not lowercase"
            # Should not have spaces
            assert " " not in canonical, f"'{canonical}' contains space"
            # Should only contain [a-z_]
            assert all(c.isalpha() or c == "_" for c in canonical), (
                f"'{canonical}' contains invalid characters"
            )

    def test_patterns_have_case_insensitive_flag(self):
        """All patterns should use (?i) for case-insensitive matching."""
        for pattern, _ in SEGMENT_NAME_PATTERNS:
            assert pattern.startswith("(?i)"), f"Pattern missing (?i): {pattern}"
