"""Tests for the hub-load / reliability fixes."""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest
from dirigera import Hub
from dirigera.devices.blinds import dict_to_blind
from dirigera.hub.abstract_smart_home_hub import AbstractSmartHomeHub

from custom_components.dirigera_platform import hub_http
from custom_components.dirigera_platform import base_classes
from custom_components.dirigera_platform.base_classes import (
    battery_percentage_sensor,
    ikea_blinds_device,
    ikea_blinds_sensor,
    ikea_starkvind_air_purifier_device,
)
from custom_components.dirigera_platform.hub_event_listener import hub_event_listener
from custom_components.dirigera_platform.scene import ikea_scene

from .conftest import blind_json


class FakeHub(AbstractSmartHomeHub):
    """Minimal hub used by devices and the listener."""

    def __init__(self, devices=None):
        self.devices = devices or []
        self.get_calls = 0
        self.patches = []
        self.websocket_base_url = "wss://x"
        self.token = "t"

    def get(self, route):
        self.get_calls += 1
        assert route == "/devices"
        return self.devices

    def patch(self, route, data):
        self.patches.append((route, data))

    def post(self, route, data=None):  # pragma: no cover
        return None

    def delete(self, route, data=None):  # pragma: no cover
        return None

    def get_blinds_by_id(self, id_):  # pragma: no cover - must not be called
        raise AssertionError("per-entity polling must not happen")


def make_blind(hass, hub, **kw):
    blind = dict_to_blind(blind_json(**kw), hub)
    device = ikea_blinds_device(hass, hub, blind)
    cover = ikea_blinds_sensor(device)
    return device, cover


# ---------------------------------------------------------------- HTTP session


def test_hub_uses_shared_keep_alive_session(monkeypatch):
    hub_http.apply_patch()
    hub_http.close_sessions()
    calls = []

    class Resp:
        content = b"[]"
        text = "[]"

        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_request(self, method, url, **kwargs):
        calls.append((id(self), method, url))
        return Resp()

    monkeypatch.setattr("requests.Session.request", fake_request)
    h1 = Hub("tok", "10.0.0.1")
    h2 = Hub("tok", "10.0.0.1")
    h1.get("/devices")
    h2.patch("/devices/x", data=[{"attributes": {}}])
    assert len(calls) == 2
    assert calls[0][0] == calls[1][0], "both hubs must share one session"
    assert calls[1][1] == "PATCH"
    assert hub_http.get_session(h1.api_base_url).verify is False


def test_session_retries_transient_errors():
    session = hub_http._build_session()
    adapter = session.get_adapter("https://10.0.0.1:8443/v1/devices")
    retry = adapter.max_retries
    assert retry.connect == 2 and retry.read == 1
    assert "PATCH" in retry.allowed_methods and "POST" not in retry.allowed_methods


# ---------------------------------------------------------------- polling


async def test_entities_do_not_poll(hass):
    hub = FakeHub()
    device, cover = make_blind(hass, hub)
    battery = battery_percentage_sensor(device)
    assert cover.should_poll is False
    assert battery.should_poll is False


async def test_air_purifier_keeps_polling(hass):
    # airPurifier events are not handled by the listener, so polling stays on
    assert ikea_starkvind_air_purifier_device.needs_polling.fget(None) is True


def test_scene_does_not_poll():
    scene = ikea_scene(MagicMock(), MagicMock())
    assert scene.should_poll is False


# ---------------------------------------------------------------- resync


async def test_resync_one_request_updates_known_devices(hass):
    hub = FakeHub()
    device, cover = make_blind(hass, hub, current=0, target=0)
    device.schedule_update_ha_state = MagicMock()
    hub.devices = [
        blind_json(current=40, target=40, battery=12, reachable=False),
        blind_json(id_="unknown-device"),
        {"garbage": True},
    ]
    listener = hub_event_listener(hub, hass, discovery_coordinator=MagicMock())
    assert listener.resync() is True
    assert hub.get_calls == 1
    assert cover.current_cover_position == 60
    assert device.battery_percentage == 12
    assert device.available is False
    device.schedule_update_ha_state.assert_called_once()
    # resync must not start discovery for unknown devices
    listener._discovery_coordinator.discover_device.assert_not_called()


async def test_resync_failure_is_logged_not_raised(hass, caplog):
    hub = FakeHub()

    def boom(route):
        raise ConnectionError("hub down")

    hub.get = boom
    listener = hub_event_listener(hub, hass)
    assert listener.resync() is False
    assert "resync failed" in caplog.text


async def test_target_level_from_event_is_applied(hass):
    hub = FakeHub()
    device, cover = make_blind(hass, hub, current=0, target=0)
    device.schedule_update_ha_state = MagicMock()
    listener = hub_event_listener(hub, hass)
    msg = {
        "type": "deviceStateChanged",
        "data": {"id": "blind-1", "deviceType": "blinds",
                 "attributes": {"blindsTargetLevel": 70, "blindsCurrentLevel": 10}},
    }
    listener.on_message(None, json.dumps(msg))
    assert device.blinds_target_level == 70
    assert cover.current_cover_position == 90


async def test_bad_event_is_logged_as_warning(hass, caplog):
    listener = hub_event_listener(FakeHub(), hass)
    listener.on_message(None, "{not json")
    assert "error processing hub event" in caplog.text


async def test_on_open_triggers_resync(hass, monkeypatch):
    listener = hub_event_listener(FakeHub(), hass)
    called = []
    monkeypatch.setattr(listener, "resync", lambda: called.append(1))
    listener._on_open(None)
    for _ in range(50):
        if called:
            break
        time.sleep(0.01)
    assert called == [1]


def test_websocket_has_keepalive(monkeypatch):
    captured = {}

    class FakeApp:
        def __init__(self, *a, **kw):
            captured["init"] = kw

        def run_forever(self, **kw):
            captured["run"] = kw

    monkeypatch.setattr("websocket.WebSocketApp", FakeApp)
    listener = hub_event_listener(FakeHub(), MagicMock())
    listener.create_listener()
    assert captured["run"]["ping_interval"] > 0
    assert 0 < captured["run"]["ping_timeout"] < captured["run"]["ping_interval"]
    assert "on_open" in captured["init"]


def test_stop_does_not_wait_for_retry_sleep():
    listener = hub_event_listener(FakeHub(), MagicMock())
    listener.create_listener = lambda: None  # connection fails immediately
    listener.start()
    time.sleep(0.1)
    t0 = time.monotonic()
    listener.stop()
    assert time.monotonic() - t0 < 2


# ---------------------------------------------------------------- blinds direction


async def test_blind_direction_follows_movement(hass, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(base_classes.time, "monotonic", lambda: clock[0])
    hub = FakeHub()
    device, cover = make_blind(hass, hub, current=0, target=0)  # HA position 100 = open
    cover.hass = hass
    cover.async_write_ha_state = MagicMock()

    assert cover.is_opening is False and cover.is_closing is False

    # going down: hub level rises, HA position falls
    device._json_data.attributes.blinds_current_level = 10
    clock[0] += 1
    assert cover.is_closing is True and cover.is_opening is False
    device._json_data.attributes.blinds_current_level = 30
    clock[0] += 1
    assert cover.is_closing is True

    # no report for longer than the timeout => stopped
    clock[0] += base_classes.BLIND_MOVE_TIMEOUT + 0.5
    assert cover.is_closing is False and cover.is_opening is False

    # going up again (e.g. with the remote)
    device._json_data.attributes.blinds_current_level = 20
    clock[0] += 1
    assert cover.is_opening is True and cover.is_closing is False


async def test_command_shows_direction_immediately(hass):
    hub = FakeHub()
    device, cover = make_blind(hass, hub, current=0, target=0)
    cover.hass = hass
    cover.async_write_ha_state = MagicMock()
    await cover.async_set_cover_position(position=40)
    assert hub.patches[-1][1] == [{"attributes": {"blindsTargetLevel": 60}}]
    assert cover.is_closing is True
    cover.async_write_ha_state.assert_called()
