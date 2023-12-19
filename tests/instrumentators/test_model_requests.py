import asyncio
from typing import Awaitable, Callable
from unittest import mock
from unittest.mock import ANY

import pytest
from structlog.testing import capture_logs

from ai_gateway.instrumentators.model_requests import ModelRequestInstrumentator


class TestModelRequestInstrumentator:
    @mock.patch("prometheus_client.Gauge.labels")
    def test_watch_sync(self, mock_gauges):
        instrumentator = ModelRequestInstrumentator(
            model_engine="anthropic", model_name="claude", concurrency_limit=None
        )

        with pytest.raises(ValueError):
            with instrumentator.watch(prompt=ANY, opts=ANY):
                assert mock_gauges.mock_calls == [
                    mock.call(model_engine="anthropic", model_name="claude"),
                    mock.call().inc(),
                ]

                mock_gauges.reset_mock()

                raise ValueError("broken")

        assert mock_gauges.mock_calls == [
            mock.call(model_engine="anthropic", model_name="claude"),
            mock.call().dec(),
        ]

    @mock.patch("prometheus_client.Gauge.labels")
    def test_watch_with_limit(self, mock_gauges):
        instrumentator = ModelRequestInstrumentator(
            model_engine="anthropic", model_name="claude", concurrency_limit=5
        )

        with instrumentator.watch(prompt=ANY, opts=ANY):
            mock_gauges.assert_has_calls(
                [
                    mock.call(model_engine="anthropic", model_name="claude"),
                    mock.call().set(5),
                ]
            )

    @mock.patch("prometheus_client.Gauge.labels")
    def test_watch_async(self, mock_gauges):
        instrumentator = ModelRequestInstrumentator(
            model_engine="anthropic", model_name="claude", concurrency_limit=None
        )

        with instrumentator.watch(prompt=ANY, opts=ANY, stream=True) as watcher:
            assert mock_gauges.mock_calls == [
                mock.call(model_engine="anthropic", model_name="claude"),
                mock.call().inc(),
            ]

            mock_gauges.reset_mock()

            watcher.finish()

            assert mock_gauges.mock_calls == [
                mock.call(model_engine="anthropic", model_name="claude"),
                mock.call().dec(),
            ]

    def test_watch_request_log(self):
        instrumentator = ModelRequestInstrumentator(
            model_engine="anthropic", model_name="claude", concurrency_limit=None
        )

        with capture_logs() as cap_logs:
            with instrumentator.watch(
                prompt="\n\nHuman: Hi, How are you?\n\nAssistant:",
                opts={"max_tokens_to_sample": 1024, "temperature": 0.7},
            ):
                pass

        assert len(cap_logs) == 1
        assert cap_logs[0]["prompt"] == "\n\nHuman: Hi, How are you?\n\nAssistant:"
        assert cap_logs[0]["model_options"] == {
            "max_tokens_to_sample": 1024,
            "temperature": 0.7,
        }
        assert cap_logs[0]["model_engine"] == "anthropic"
        assert cap_logs[0]["model_name"] == "claude"
