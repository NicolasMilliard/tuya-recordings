from types import SimpleNamespace

import pytest

try:
    from probatio import to_field_list as convert
except ImportError:
    from voluptuous_serialize import convert

from homeassistant.helpers import config_validation as cv

from custom_components.tuya_recordings.config_flow import (
    _dependency_error_key,
    _native_authorize_schema,
    _options_schema,
    _required_dependency_errors,
    _user_schema,
    _validate_form_input,
)
from custom_components.tuya_recordings.const import (
    CONF_ALERT_RESET_SECONDS,
    CONF_APP_PROFILE,
    CONF_CATALOG_SYNC_MINUTES,
    CONF_LOOKBACK_DAYS,
    CONF_MEDIA_STORAGE_PATH,
    CONF_MEDIA_SYNC_HOURS,
    CONF_MEDIA_VIEW_RECORDINGS_ORDER,
    CONF_MEDIA_SYNC_ENABLED,
    CONF_REGION,
    DEFAULT_CATALOG_SYNC_MINUTES,
)


def test_user_schema_is_frontend_serializable():
    converted = convert(_user_schema({}), custom_serializer=cv.custom_serializer)

    assert any(field["name"] == CONF_MEDIA_STORAGE_PATH for field in converted)


def test_user_schema_offers_smart_life_and_tuya_smart():
    converted = convert(_user_schema({}), custom_serializer=cv.custom_serializer)

    account_app = next(field for field in converted if field["name"] == CONF_APP_PROFILE)
    options = account_app["selector"]["select"]["options"]
    assert {option["value"] for option in options} == {"smart_life", "tuya_smart"}


def test_native_authorization_qr_is_frontend_serializable():
    converted = convert(
        _native_authorize_schema("tuyaSmart--qrLogin?token=test-token"),
        custom_serializer=cv.custom_serializer,
    )

    qr = next(field for field in converted if field["name"] == "qr_code")
    assert qr["selector"]["qr_code"]["data"] == "tuyaSmart--qrLogin?token=test-token"


def test_options_schema_is_frontend_serializable():
    config_entry = SimpleNamespace(data={}, options={})

    converted = convert(_options_schema(config_entry), custom_serializer=cv.custom_serializer)

    assert any(field["name"] == CONF_MEDIA_STORAGE_PATH for field in converted)


@pytest.mark.parametrize("key,value", [
    ("media_sync_enabled", True),
    ("media_sync_hours", 48),
    ("media_view_recordings_order", "Ascending"),
])
def test_options_preserve_setup_choices(key, value):
    entry = SimpleNamespace(data={key: value}, options={})
    assert _options_schema(entry)({})[key] == value


def test_saved_options_override_setup_choices():
    entry = SimpleNamespace(data={"media_sync_enabled": True}, options={"media_sync_enabled": False})
    assert _options_schema(entry)({})["media_sync_enabled"] is False


def test_thumbnail_sync_is_not_a_user_option():
    entry = SimpleNamespace(data={"thumbnail_sync_enabled": False}, options={})
    for schema in (_user_schema({}), _options_schema(entry)):
        fields = convert(schema, custom_serializer=cv.custom_serializer)
        assert all(field["name"] != "thumbnail_sync_enabled" for field in fields)


def test_media_storage_path_validation_returns_field_error():
    errors = _validate_form_input({CONF_MEDIA_STORAGE_PATH: "/config/www/tuya_recordings"})

    assert errors == {CONF_MEDIA_STORAGE_PATH: "path_not_allowed"}


@pytest.mark.parametrize("path", ["/media/tuya_recordings", " /media/tuya_recordings "])
def test_media_storage_path_validation_normalizes_valid_path(path):
    user_input = {CONF_MEDIA_STORAGE_PATH: path}

    assert _validate_form_input(user_input) == {}
    assert user_input[CONF_MEDIA_STORAGE_PATH] == "/media/tuya_recordings"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (CONF_LOOKBACK_DAYS, -1),
        (CONF_LOOKBACK_DAYS, 32),
        (CONF_CATALOG_SYNC_MINUTES, 14),
        (CONF_CATALOG_SYNC_MINUTES, 1441),
        (CONF_MEDIA_SYNC_HOURS, 745),
        (CONF_ALERT_RESET_SECONDS, 4),
        (CONF_ALERT_RESET_SECONDS, True),
        (CONF_MEDIA_VIEW_RECORDINGS_ORDER, "Random"),
        (CONF_REGION, "not-a-tuya-region"),
        (CONF_MEDIA_SYNC_ENABLED, "yes"),
    ],
)
def test_form_validation_rejects_out_of_range_or_unknown_option_values(field, value):
    user_input = {CONF_MEDIA_STORAGE_PATH: "/media/tuya_recordings", field: value}

    assert _validate_form_input(user_input) == {field: "invalid_value"}


def test_form_validation_normalizes_numeric_option_values():
    user_input = {
        CONF_MEDIA_STORAGE_PATH: "/media/tuya_recordings",
        CONF_CATALOG_SYNC_MINUTES: "30",
        CONF_ALERT_RESET_SECONDS: "75",
    }

    assert _validate_form_input(user_input) == {}
    assert user_input[CONF_CATALOG_SYNC_MINUTES] == 30
    assert user_input[CONF_ALERT_RESET_SECONDS] == 75


def test_setup_requires_official_tuya_but_not_localtuya():
    class Entries:
        def __init__(self, entries):
            self.entries = entries

        def async_entries(self, domain):
            return self.entries.get(domain, [])

    hass = SimpleNamespace(config_entries=Entries({"localtuya": [object()]}))
    errors = _required_dependency_errors(hass)
    assert errors == {"tuya_required"}
    assert _dependency_error_key(errors) == "tuya_required"

    hass = SimpleNamespace(config_entries=Entries({"tuya": [object()]}))
    assert _required_dependency_errors(hass) == set()


def test_options_default_to_safe_catalog_interval():
    entry = SimpleNamespace(data={}, options={})

    assert (
        _options_schema(entry)({})[CONF_CATALOG_SYNC_MINUTES]
        == DEFAULT_CATALOG_SYNC_MINUTES
    )


def test_options_preserve_catalog_interval():
    entry = SimpleNamespace(data={CONF_CATALOG_SYNC_MINUTES: 30}, options={})

    assert _options_schema(entry)({})[CONF_CATALOG_SYNC_MINUTES] == 30
