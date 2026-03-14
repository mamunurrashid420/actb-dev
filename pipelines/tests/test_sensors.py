"""Tests for sensor definitions."""

from unittest.mock import Mock, patch

import dagster as dg
import requests


class TestPatentsviewUpdateSensor:
    """Tests for patentsview_update_sensor."""

    @patch("pipelines.sensors.requests.head")
    def test_triggers_run_on_new_data(self, mock_head):
        """Sensor should trigger run when S3 has newer data."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange: Mock S3 response with Last-Modified header
        mock_response = Mock()
        mock_response.headers = {"Last-Modified": "Wed, 10 Sep 2025 12:00:00 GMT"}
        mock_head.return_value = mock_response

        # Build sensor context with no cursor (first run)
        context = dg.build_sensor_context()

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Should return RunRequest
        assert isinstance(result, dg.RunRequest)
        assert result.run_key == "patentsview-2025-09-10"

    @patch("pipelines.sensors.requests.head")
    def test_skips_when_no_new_data(self, mock_head):
        """Sensor should skip when S3 data hasn't changed."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange: Mock S3 response
        mock_response = Mock()
        mock_response.headers = {"Last-Modified": "Wed, 10 Sep 2025 12:00:00 GMT"}
        mock_head.return_value = mock_response

        # Build context with cursor showing we've seen this date
        context = dg.build_sensor_context(cursor="2025-09-10T12:00:00")

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Should return SkipReason
        assert isinstance(result, dg.SkipReason)
        assert "No new data" in result.skip_message

    @patch("pipelines.sensors.requests.head")
    def test_skips_on_network_error(self, mock_head):
        """Sensor should skip gracefully on network errors."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange: Mock network failure
        mock_head.side_effect = requests.RequestException("Connection failed")

        context = dg.build_sensor_context()

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Should skip, not crash
        assert isinstance(result, dg.SkipReason)
        assert "Could not reach" in result.skip_message

    @patch("pipelines.sensors.requests.head")
    def test_skips_when_no_last_modified_header(self, mock_head):
        """Sensor should skip if S3 returns no Last-Modified header."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange: Mock response without Last-Modified
        mock_response = Mock()
        mock_response.headers = {}
        mock_head.return_value = mock_response

        context = dg.build_sensor_context()

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Should skip
        assert isinstance(result, dg.SkipReason)
        assert "No Last-Modified" in result.skip_message

    @patch("pipelines.sensors.requests.head")
    def test_triggers_when_remote_is_newer(self, mock_head):
        """Sensor should trigger when remote data is newer than cursor."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange: Mock newer S3 data
        mock_response = Mock()
        mock_response.headers = {"Last-Modified": "Wed, 15 Sep 2025 12:00:00 GMT"}
        mock_head.return_value = mock_response

        # Build context with older cursor
        context = dg.build_sensor_context(cursor="2025-09-10T12:00:00")

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Should return RunRequest for new data
        assert isinstance(result, dg.RunRequest)
        assert result.run_key == "patentsview-2025-09-15"

    @patch("pipelines.sensors.requests.head")
    def test_run_request_has_correct_tags(self, mock_head):
        """RunRequest should include appropriate tags."""
        from pipelines.sensors import patentsview_update_sensor

        # Arrange
        mock_response = Mock()
        mock_response.headers = {"Last-Modified": "Wed, 10 Sep 2025 12:00:00 GMT"}
        mock_head.return_value = mock_response

        context = dg.build_sensor_context()

        # Act
        result = patentsview_update_sensor(context)

        # Assert: Check tags
        assert isinstance(result, dg.RunRequest)
        assert result.tags["trigger"] == "sensor"
        assert "2025-09-10" in result.tags["remote_mtime"]
