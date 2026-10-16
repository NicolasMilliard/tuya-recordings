import base64
import json
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.core import State

from custom_components.tuya_recordings.event import TuyaRecordingAlertEvent


def test_worker_event_notification_is_rescheduled_on_the_ha_event_loop(monkeypatch):
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(loop=Mock()),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id=None,
        tuya_manager=None,
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()
    worker = object()
    main = object()
    monkeypatch.setattr(
        "custom_components.tuya_recordings.event.current_thread", lambda: worker
    )
    monkeypatch.setattr(
        "custom_components.tuya_recordings.event.main_thread", lambda: main
    )

    event._record_event("ipc_human", {"alarm": True})

    event.hass.loop.call_soon_threadsafe.assert_called_once_with(
        event._record_event, "ipc_human", {"alarm": True}
    )
    event._trigger_event.assert_not_called()
    event.async_write_ha_state.assert_not_called()


def test_identical_official_event_state_replay_is_not_recorded():
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id=None,
        tuya_manager=None,
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()
    attributes = {"event_type": "ipc_human", "alarm": True}
    state = State("event.camera_doorbell_message", "detected", attributes)

    event._handle_event_state_change(
        SimpleNamespace(data={"old_state": state, "new_state": state})
    )

    event._trigger_event.assert_not_called()
    event.async_write_ha_state.assert_not_called()


def test_camera_event_uses_the_camera_notification_without_a_hold_timer():
    raw_value = base64.b64encode(
        json.dumps({"cmd": "ipc_human", "alarm": True, "time": 12345}).encode()
    ).decode()
    device = SimpleNamespace(status={"initiative_message": raw_value})
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id="camera-id",
        tuya_manager=SimpleNamespace(device_map={"camera-id": device}),
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()

    event._handle_tuya_device_update(["initiative_message"], {"initiative_message": 456})

    event._trigger_event.assert_called_once_with(
        "detected",
        {
            "cmd": "ipc_human",
            "alarm": True,
            "time": 12345,
            "notification_dp": "initiative_message",
            "dp_timestamp": 456,
            "tuya_event_code": "ipc_human",
        },
    )
    event.async_write_ha_state.assert_called_once()


def test_camera_event_keeps_the_raw_camera_alert_code():
    raw_value = base64.b64encode(json.dumps({"cmd": "ipc_bang"}).encode()).decode()
    device = SimpleNamespace(status={"initiative_message": raw_value})
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id="camera-id",
        tuya_manager=SimpleNamespace(device_map={"camera-id": device}),
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()

    event._handle_tuya_device_update(["initiative_message"], None)

    event._trigger_event.assert_called_once_with(
        "detected",
        {"cmd": "ipc_bang", "notification_dp": "initiative_message", "tuya_event_code": "ipc_bang"},
    )
    event.async_write_ha_state.assert_called_once()


def test_newer_dp_timestamp_records_an_identical_camera_event():
    raw_value = base64.b64encode(json.dumps({"cmd": "ipc_human"}).encode()).decode()
    device = SimpleNamespace(status={"initiative_message": raw_value})
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id="camera-id",
        tuya_manager=SimpleNamespace(device_map={"camera-id": device}),
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()

    event._handle_tuya_device_update(["initiative_message"], {"initiative_message": 100})
    event._handle_tuya_device_update(["initiative_message"], {"initiative_message": 101})
    event._handle_tuya_device_update(["initiative_message"], {"initiative_message": 101})

    assert event._trigger_event.call_count == 2
    assert event._trigger_event.call_args_list[-1].args[1]["dp_timestamp"] == 101
    assert event.async_write_ha_state.call_count == 2


def test_camera_event_records_only_an_explicit_camera_clear():
    raw_value = base64.b64encode(
        json.dumps({"cmd": "ipc_human", "alarm": False}).encode()
    ).decode()
    device = SimpleNamespace(status={"initiative_message": raw_value})
    event = TuyaRecordingAlertEvent(
        hass=SimpleNamespace(),
        entry=SimpleNamespace(entry_id="test"),
        event_entity_id="event.camera_doorbell_message",
        camera_name="Test camera",
        tuya_device_id="camera-id",
        tuya_manager=SimpleNamespace(device_map={"camera-id": device}),
    )
    event._trigger_event = Mock()
    event.async_write_ha_state = Mock()

    event._handle_tuya_device_update(["initiative_message"], None)

    event._trigger_event.assert_called_once_with(
        "cleared",
        {"cmd": "ipc_human", "alarm": False, "notification_dp": "initiative_message", "tuya_event_code": "ipc_human"},
    )
    event.async_write_ha_state.assert_called_once()
