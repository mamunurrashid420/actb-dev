"""Tests for schedule definitions.

Tests validate that schedules are properly configured with correct cron expressions,
timezones, target assets, and default states.
"""

import dagster as dg
import pytest

from pipelines.schedules import ALL_SCHEDULES


class TestScheduleDefinitions:
    """Tests for schedule configuration and structure."""

    @pytest.fixture
    def all_schedules(self):
        """Get all schedule definitions from ALL_SCHEDULES."""
        return ALL_SCHEDULES

    @pytest.fixture
    def schedules_by_name(self, all_schedules):
        """Index schedules by name for efficient lookup."""
        return {schedule.name: schedule for schedule in all_schedules}

    def test_all_schedules_exist(self, schedules_by_name):
        """Test that all 4 schedules are defined and registered."""
        expected_schedules = [
            "weekly_fred_refresh",
            "weekly_bls_refresh",
            "weekly_world_bank_refresh",
            "weekly_combined_indicators",
            # Note: weekly_cross_country not yet implemented (no cross-country comparison assets exist yet)
        ]

        for schedule_name in expected_schedules:
            assert schedule_name in schedules_by_name, (
                f"Missing schedule: {schedule_name}"
            )

    def test_schedule_count(self, all_schedules):
        """Test that expected number of schedules are defined."""
        # 21 schedules total (includes FRED, BLS, World Bank, USDA, BEA, SEC, etc.)
        assert len(all_schedules) == 21, (
            f"Expected 21 schedules, found {len(all_schedules)}"
        )

    def test_all_schedules_exported(self):
        """Test that ALL_SCHEDULES contains all schedules."""
        # 21 schedules total
        assert len(ALL_SCHEDULES) == 21, (
            f"ALL_SCHEDULES should contain 21 schedules, found {len(ALL_SCHEDULES)}"
        )

        # Check all are ScheduleDefinition instances
        for schedule in ALL_SCHEDULES:
            assert isinstance(schedule, dg.ScheduleDefinition), (
                f"Expected ScheduleDefinition, got {type(schedule)}"
            )

    def test_all_schedules_have_default_stopped(self, all_schedules):
        """Test that all schedules start in STOPPED state."""
        for schedule in all_schedules:
            assert schedule.default_status == dg.DefaultScheduleStatus.STOPPED, (
                f"Schedule {schedule.name} should default to STOPPED, got {schedule.default_status}"
            )

    def test_all_schedules_have_timezone(self, all_schedules):
        """Test that all schedules have timezone set to US/Eastern."""
        for schedule in all_schedules:
            assert schedule.execution_timezone == "US/Eastern", (
                f"Schedule {schedule.name} should have timezone 'US/Eastern', got {schedule.execution_timezone}"
            )

    def test_all_schedules_have_descriptions(self, all_schedules):
        """Test that all schedules have non-empty descriptions."""
        for schedule in all_schedules:
            assert schedule.description, f"Schedule {schedule.name} missing description"
            assert len(schedule.description) > 20, (
                f"Schedule {schedule.name} has too short description: {schedule.description}"
            )


class TestSourceDataSchedules:
    """Tests for source data schedules (FRED, BLS, World Bank)."""

    @pytest.fixture
    def schedules_by_name(self):
        """Get schedules indexed by name."""
        return {schedule.name: schedule for schedule in ALL_SCHEDULES}

    def test_fred_schedule_configuration(self, schedules_by_name):
        """Test FRED schedule has correct configuration."""
        schedule = schedules_by_name["weekly_fred_refresh"]

        # Check cron schedule (Monday 2 AM)
        assert schedule.cron_schedule == "0 2 * * 1", (
            f"FRED schedule should run Monday 2 AM, got {schedule.cron_schedule}"
        )

        # Check it targets fred group
        assert "fred" in schedule.description.lower(), (
            "FRED schedule description should mention 'fred'"
        )

    def test_bls_schedule_configuration(self, schedules_by_name):
        """Test BLS schedule has correct configuration."""
        schedule = schedules_by_name["weekly_bls_refresh"]

        # Check cron schedule (Friday 7 AM)
        assert schedule.cron_schedule == "0 7 * * 5", (
            f"BLS schedule should run Friday 7 AM, got {schedule.cron_schedule}"
        )

        # Check it targets bls group
        assert "bls" in schedule.description.lower(), (
            "BLS schedule description should mention 'bls'"
        )

    def test_world_bank_schedule_configuration(self, schedules_by_name):
        """Test World Bank schedule has correct configuration."""
        schedule = schedules_by_name["weekly_world_bank_refresh"]

        # Check cron schedule (Sunday 2 AM)
        assert schedule.cron_schedule == "0 2 * * 0", (
            f"World Bank schedule should run Sunday 2 AM, got {schedule.cron_schedule}"
        )

        # Check it targets world bank
        assert (
            "world bank" in schedule.description.lower()
            or "country" in schedule.description.lower()
        ), "World Bank schedule description should mention 'world bank' or 'country'"


class TestPublishedLayerSchedules:
    """Tests for published layer schedules."""

    @pytest.fixture
    def schedules_by_name(self):
        """Get schedules indexed by name."""
        return {schedule.name: schedule for schedule in ALL_SCHEDULES}

    def test_combined_indicators_schedule_configuration(self, schedules_by_name):
        """Test combined indicators schedule has correct configuration."""
        schedule = schedules_by_name["weekly_combined_indicators"]

        # Check cron schedule (Monday 4 AM - after all source refreshes)
        assert schedule.cron_schedule == "0 4 * * 1", (
            f"Combined indicators schedule should run Monday 4 AM, got {schedule.cron_schedule}"
        )

        # Check it mentions both US and country in description
        desc_lower = schedule.description.lower()
        assert "us" in desc_lower or "country" in desc_lower, (
            "Combined indicators schedule description should mention US or country"
        )

    def test_published_schedules_run_after_sources(self, schedules_by_name):
        """Test that published schedules are timed after their source schedules."""
        # All source schedules should run before combined indicators (Monday 4 AM)
        fred_schedule = schedules_by_name["weekly_fred_refresh"]
        bls_schedule = schedules_by_name["weekly_bls_refresh"]
        world_bank_schedule = schedules_by_name["weekly_world_bank_refresh"]
        combined_indicators_schedule = schedules_by_name["weekly_combined_indicators"]

        # FRED runs Monday 2 AM (before combined indicators at 4 AM)
        assert fred_schedule.cron_schedule == "0 2 * * 1"
        # BLS runs Friday 7 AM (well before Monday)
        assert bls_schedule.cron_schedule == "0 7 * * 5"
        # World Bank runs Sunday 2 AM (before Monday)
        assert world_bank_schedule.cron_schedule == "0 2 * * 0"
        # Combined indicators runs Monday 4 AM
        assert combined_indicators_schedule.cron_schedule == "0 4 * * 1"


class TestCronExpressions:
    """Tests for cron expression validity."""

    @pytest.fixture
    def all_schedules(self):
        """Get all schedule definitions."""
        return ALL_SCHEDULES

    def test_cron_expressions_are_valid(self, all_schedules):
        """Test that all cron expressions are valid 5-field format."""
        for schedule in all_schedules:
            cron = schedule.cron_schedule
            parts = cron.split()

            # Cron should have 5 fields: minute, hour, day of month, month, day of week
            assert len(parts) == 5, (
                f"Schedule {schedule.name} has invalid cron format: {cron} (expected 5 fields)"
            )

            # Validate each field is numeric or wildcard
            for i, part in enumerate(parts):
                assert (
                    part
                    .replace("*", "")
                    .replace(",", "")
                    .replace("-", "")
                    .replace("/", "")
                    .isdigit()
                    or part == "*"
                ), f"Schedule {schedule.name} has invalid cron field {i}: {part}"

    def test_no_hourly_schedules(self, all_schedules):
        """Test that no schedules run more frequently than daily."""
        for schedule in all_schedules:
            cron = schedule.cron_schedule
            parts = cron.split()

            # minute field should be a specific minute, not * or */n
            minute = parts[0]
            # hour field should be a specific hour, not * or */n
            hour = parts[1]

            # Should not be * (every minute/hour)
            assert minute != "*", f"Schedule {schedule.name} runs every minute: {cron}"
            assert hour != "*", f"Schedule {schedule.name} runs every hour: {cron}"

    def test_daily_schedules_are_appropriate(self, all_schedules):
        """Test that truly daily schedules are only for high-volume data.

        Note: Quarterly schedules may have '*' in day_of_week but run on specific
        days of specific months (e.g., '0 3 1 1,4,7,10 *' = first day of quarters).
        Monthly schedules run on a specific day_of_month (e.g., '0 2 1 * *' = 1st of month).
        """
        # Daily schedules are allowed for SEC and other high-frequency data sources
        allowed_daily_prefixes = ["sec", "fsds"]

        for schedule in all_schedules:
            cron = schedule.cron_schedule
            parts = cron.split()

            # day_of_month field (index 2)
            day_of_month = parts[2]
            # month field (index 3)
            month = parts[3]
            # day_of_week field (index 4)
            day_of_week = parts[4]

            # Only check truly daily schedules (run every day of every month)
            # Skip quarterly schedules (specific months) and monthly schedules
            # (specific day_of_month)
            is_daily = day_of_week == "*" and month == "*" and day_of_month == "*"
            if is_daily:
                name_lower = schedule.name.lower()
                is_allowed = any(
                    prefix in name_lower for prefix in allowed_daily_prefixes
                )
                assert is_allowed, (
                    f"Schedule {schedule.name} runs daily but may not need to: {cron}. "
                    "Only high-volume data schedules should run daily."
                )
