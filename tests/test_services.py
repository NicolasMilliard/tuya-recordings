import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components import tuya_recordings as integration
from custom_components.tuya_recordings import (
    _entries_for_call,
    _official_tuya_camera_device_ids,
    _required_dependency_errors,
)
from custom_components.tuya_recordings.client import TuyaRecordingsClient
from custom_components.tuya_recordings.const import DOMAIN


def test_entries_for_call_returns_all_valid_clients():
    first = {"client": TuyaRecordingsClient({})}
    second = {"client": TuyaRecordingsClient({})}
    hass = SimpleNamespace(data={DOMAIN: {"one": first, "two": second, "bad": {"client": object()}}})

    assert _entries_for_call(hass, None) == [first, second]


def test_entries_for_call_returns_requested_client_only():
    first = {"client": TuyaRecordingsClient({})}
    second = {"client": TuyaRecordingsClient({})}
    hass = SimpleNamespace(data={DOMAIN: {"one": first, "two": second}})

    assert _entries_for_call(hass, "two") == [second]
    assert _entries_for_call(hass, "missing") == []


class _ConfigEntries:
    def __init__(self, entries_by_domain):
        self._entries_by_domain = entries_by_domain

    def async_entries(self, domain):
        return self._entries_by_domain.get(domain, [])


def test_required_dependency_errors_require_only_official_tuya():
    hass = SimpleNamespace(config_entries=_ConfigEntries({}))

    assert _required_dependency_errors(hass) == {"tuya_required"}

    hass = SimpleNamespace(
        config_entries=_ConfigEntries(
            {
                "tuya": [SimpleNamespace(data={})],
            }
        )
    )

    assert _required_dependency_errors(hass) == set()


def test_official_tuya_camera_device_ids_come_from_tuya_camera_entities():
    entity_entries = [
        SimpleNamespace(platform="tuya", entity_id="camera.porch_cam", device_id="dev-reg-1"),
        SimpleNamespace(platform="tuya", entity_id="switch.porch_cam_privacy_mode", device_id="dev-reg-1"),
        SimpleNamespace(platform="localtuya", entity_id="camera.local_fake", device_id="dev-reg-2"),
        SimpleNamespace(platform="tuya", entity_id="camera.garage_cam_2", device_id="dev-reg-3"),
    ]
    device_entries = [
        SimpleNamespace(id="dev-reg-1", name="Porch Cam", name_by_user=None, identifiers={("tuya", "tuya-porch")}),
        SimpleNamespace(id="dev-reg-2", name="Local Fake", name_by_user=None, identifiers={("tuya", "wrong")}),
        SimpleNamespace(id="dev-reg-3", name="Side Cam", name_by_user="Garage Cam", identifiers={("tuya", "tuya-garage")}),
    ]

    assert _official_tuya_camera_device_ids(entity_entries, device_entries) == {
        "tuya-porch": "Porch Cam",
        "tuya-garage": "Garage Cam",
    }


@pytest.mark.parametrize(
    "registry_event", ["entity_registry_updated", "device_registry_updated"]
)
def test_setup_discovers_cameras_from_device_registry_values(
    monkeypatch, tmp_path, registry_event
):
    entities = {
        "camera.porch": SimpleNamespace(
            platform="tuya", entity_id="camera.porch", device_id="registry-porch"
        ),
        "camera.garage": SimpleNamespace(
            platform="tuya", entity_id="camera.garage", device_id="registry-garage"
        ),
    }
    devices = {
        "registry-porch": SimpleNamespace(
            id="registry-porch", identifiers={("tuya", "tuya-porch")},
            name="Porch Cam", name_by_user=None,
        ),
        "registry-garage": SimpleNamespace(
            id="registry-garage", identifiers={("tuya", "tuya-garage")},
            name="Garage Cam", name_by_user="Garage",
        ),
    }
    monkeypatch.setattr(
        integration.er, "async_get", lambda hass: SimpleNamespace(entities=entities)
    )
    monkeypatch.setattr(
        integration.dr, "async_get", lambda hass: SimpleNamespace(devices=list(devices.values()), async_get=devices.get)
    )
    monkeypatch.setattr(integration, "_required_dependency_errors", lambda hass: set())
    monkeypatch.setattr(integration, "_async_update_dependency_issues", lambda *args: None)
    monkeypatch.setattr(integration, "_async_update_camera_repair_issues", lambda *args: None)
    monkeypatch.setattr(integration, "native_app_session", lambda data: None)
    monkeypatch.setattr(integration, "_async_register_services", lambda hass: None)
    monkeypatch.setattr(integration, "_async_register_views", lambda hass: None)
    monkeypatch.setattr(integration, "_async_schedule_media_sync", lambda *args: None)
    monkeypatch.setattr(integration, "async_register_frontend", AsyncMock())
    client = Mock()
    monkeypatch.setattr(integration, "TuyaRecordingsClient", Mock(return_value=client))
    listeners = {}

    def listen(event, callback):
        listeners[event] = callback
        return Mock()

    hass = SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
        config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        bus=SimpleNamespace(async_listen=listen),
        async_add_executor_job=AsyncMock(),
        data={},
    )
    entry = SimpleNamespace(
        entry_id="entry", data={}, options={}, async_on_unload=Mock(),
        add_update_listener=Mock(return_value=Mock()),
    )

    assert asyncio.run(integration.async_setup_entry(hass, entry)) is True
    expected = {"tuya-porch": "Porch Cam", "tuya-garage": "Garage"}
    client.set_camera_inventory.assert_called_once_with(expected)

    client.set_camera_inventory.reset_mock()
    devices["registry-garage"].name_by_user = "Renamed Garage"
    listeners[registry_event]()
    client.set_camera_inventory.assert_called_once_with(
        {"tuya-porch": "Porch Cam", "tuya-garage": "Renamed Garage"}
    )

