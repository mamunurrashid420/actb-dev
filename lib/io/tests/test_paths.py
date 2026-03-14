"""Tests for Hive-standard path resolution."""

from upath import UPath

from shared.io.paths import (
    build_hive_partition_path,
    parse_data_file_path,
    parse_hive_partition_path,
    resolve_asset_path,
)


class TestBuildHivePartitionPath:
    """Tests for build_hive_partition_path function."""

    def test_single_dimension(self):
        """Test single dimension partition uses 'partition=' prefix."""
        got = build_hive_partition_path("USA")
        want = "partition=USA"
        assert got == want

    def test_multi_dimension_sorted(self):
        """Test multi-dimensional partitions are sorted alphabetically."""
        got = build_hive_partition_path({"country": "USA", "indicator": "GDP"})
        want = "country=USA/indicator=GDP"
        assert got == want

    def test_multi_dimension_sorting_order(self):
        """Test multi-dimensional partitions sort regardless of input order."""
        # Input with 'z' before 'a' should still output 'a' first
        got = build_hive_partition_path({"zebra": "1", "alpha": "2"})
        want = "alpha=2/zebra=1"
        assert got == want


class TestResolveAssetPath:
    """Tests for resolve_asset_path function."""

    def test_unpartitioned_uses_data_file(self):
        """Unpartitioned assets use Hive-standard: {asset}/data"""
        got = resolve_asset_path("/data", "bronze/bls/all_series")
        want = UPath("/data/bronze/bls/all_series/data")
        assert got == want

    def test_partitioned_single_dimension(self):
        """Partitioned assets use Hive-style: {asset}/partition={key}/data"""
        got = resolve_asset_path("/data", "bronze/world_bank/timeseries", "USA")
        want = UPath("/data/bronze/world_bank/timeseries/partition=USA/data")
        assert got == want

    def test_partitioned_multi_dimension(self):
        """Multi-dimensional partitions are sorted alphabetically."""
        got = resolve_asset_path(
            "/data", "bronze/multi/asset", {"country": "USA", "year": "2024"}
        )
        want = UPath("/data/bronze/multi/asset/country=USA/year=2024/data")
        assert got == want

    def test_accepts_list_asset_path(self):
        """Asset path can be provided as list."""
        got = resolve_asset_path("/data", ["bronze", "fred", "series"])
        want = UPath("/data/bronze/fred/series/data")
        assert got == want

    def test_accepts_tuple_asset_path(self):
        """Asset path can be provided as tuple (from Dagster AssetKey.path)."""
        got = resolve_asset_path("/data", ("bronze", "bls", "all_series"))
        want = UPath("/data/bronze/bls/all_series/data")
        assert got == want

    def test_accepts_string_base_path(self):
        """Base path can be a string."""
        got = resolve_asset_path("_data/assets", "bronze/test")
        want = UPath("_data/assets/bronze/test/data")
        assert got == want

    def test_accepts_upath_base_path(self):
        """Base path can be a UPath."""
        got = resolve_asset_path(UPath("/data"), "bronze/test")
        want = UPath("/data/bronze/test/data")
        assert got == want

    def test_strips_leading_trailing_slashes(self):
        """Leading/trailing slashes in asset path are handled."""
        got = resolve_asset_path("/data", "/bronze/test/")
        want = UPath("/data/bronze/test/data")
        assert got == want

    def test_single_component_asset_path(self):
        """Single component asset paths work."""
        got = resolve_asset_path("/data", "asset")
        want = UPath("/data/asset/data")
        assert got == want


class TestParseHivePartitionPath:
    """Tests for parse_hive_partition_path function."""

    def test_single_dimension_partition_key(self):
        """Test single dimension with 'partition=' prefix returns value."""
        got = parse_hive_partition_path("partition=USA")
        want = "USA"
        assert got == want

    def test_single_dimension_named_key(self):
        """Test single dimension with named key returns dict."""
        got = parse_hive_partition_path("country=USA")
        want = {"country": "USA"}
        assert got == want

    def test_multi_dimension(self):
        """Test multi-dimensional partition returns dict."""
        got = parse_hive_partition_path("country=USA/indicator=GDP")
        want = {"country": "USA", "indicator": "GDP"}
        assert got == want

    def test_multi_dimension_three_parts(self):
        """Test three-part multi-dimensional partition."""
        got = parse_hive_partition_path("country=USA/year=2024/quarter=Q1")
        want = {"country": "USA", "year": "2024", "quarter": "Q1"}
        assert got == want

    def test_value_with_special_chars(self):
        """Test partition values can contain special characters."""
        got = parse_hive_partition_path("partition=0001067983")
        want = "0001067983"
        assert got == want


class TestParseDataFilePath:
    """Tests for parse_data_file_path function."""

    def test_unpartitioned_parquet(self):
        """Test unpartitioned asset with .parquet extension."""
        got = parse_data_file_path("bronze/bls/all_series/data.parquet", "")
        want = ("bronze/bls/all_series", None)
        assert got == want

    def test_unpartitioned_json(self):
        """Test unpartitioned asset with .json extension."""
        got = parse_data_file_path("silver/reference/crosswalk/data.json", "")
        want = ("silver/reference/crosswalk", None)
        assert got == want

    def test_single_partition(self):
        """Test single-dimension partitioned asset."""
        got = parse_data_file_path(
            "bronze/sec/form_10k/partition=AAPL/data.parquet", ""
        )
        want = ("bronze/sec/form_10k", "AAPL")
        assert got == want

    def test_multi_partition(self):
        """Test multi-dimensional partitioned asset."""
        got = parse_data_file_path(
            "bronze/multi/asset/country=USA/year=2024/data.parquet", ""
        )
        want = ("bronze/multi/asset", {"country": "USA", "year": "2024"})
        assert got == want

    def test_with_base_path(self):
        """Test with non-empty base path."""
        got = parse_data_file_path(
            "/data/assets/bronze/test/data.parquet", "/data/assets"
        )
        want = ("bronze/test", None)
        assert got == want

    def test_with_upath_inputs(self):
        """Test with UPath inputs instead of strings."""
        got = parse_data_file_path(
            UPath("/data/bronze/test/partition=USA/data.parquet"),
            UPath("/data"),
        )
        want = ("bronze/test", "USA")
        assert got == want

    def test_deep_asset_path(self):
        """Test asset with many path components."""
        got = parse_data_file_path(
            "gold/economic/labor_market/unemployment/partition=USA/data.parquet",
            "",
        )
        want = ("gold/economic/labor_market/unemployment", "USA")
        assert got == want


class TestPathRoundTrip:
    """Lifecycle tests: verify forward and reverse operations are inverses."""

    def test_unpartitioned_roundtrip(self):
        """Test unpartitioned asset survives forward-reverse cycle."""
        # Forward: asset → path
        path = resolve_asset_path("/data", "bronze/test/asset")
        # Reverse: path → asset
        asset, partition = parse_data_file_path(str(path) + ".parquet", "/data")
        assert asset == "bronze/test/asset"
        assert partition is None

    def test_single_partition_roundtrip(self):
        """Test single-partition asset survives forward-reverse cycle."""
        path = resolve_asset_path("/data", "bronze/test", "USA")
        asset, partition = parse_data_file_path(str(path) + ".parquet", "/data")
        assert asset == "bronze/test"
        assert partition == "USA"

    def test_multi_partition_roundtrip(self):
        """Test multi-partition asset survives forward-reverse cycle."""
        path = resolve_asset_path(
            "/data", "bronze/test", {"country": "USA", "year": "2024"}
        )
        asset, partition = parse_data_file_path(str(path) + ".parquet", "/data")
        assert asset == "bronze/test"
        assert partition == {"country": "USA", "year": "2024"}

    def test_deep_path_roundtrip(self):
        """Test deeply nested asset path survives roundtrip."""
        path = resolve_asset_path(
            "/data", "gold/economic/labor_market/unemployment", "USA"
        )
        asset, partition = parse_data_file_path(str(path) + ".parquet", "/data")
        assert asset == "gold/economic/labor_market/unemployment"
        assert partition == "USA"
