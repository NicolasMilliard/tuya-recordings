from types import SimpleNamespace

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

