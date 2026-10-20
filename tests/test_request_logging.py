import asyncio
import logging
from types import SimpleNamespace

from custom_components.tuya_recordings import http as recordings_http


def test_frontend_playback_event_is_not_logged_as_warning(caplog):
    async def json():
        return {"phase": "click", "dev_id": "dev", "start": 1, "end": 2}

    view = recordings_http.TuyaRecordingsDebugView(SimpleNamespace())
    with caplog.at_level(logging.DEBUG, logger=recordings_http.__name__):
        asyncio.run(view.post(SimpleNamespace(json=json)))

    assert [record.levelno for record in caplog.records] == [logging.DEBUG]
