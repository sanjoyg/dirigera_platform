"""End-to-end: set the integration up against a fake hub and count hub requests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.dirigera_platform.const import DOMAIN

from .conftest import blind_json


class Resp:
    def __init__(self, payload):
        self._payload = payload
        import json

        self.text = json.dumps(payload)
        self.content = self.text.encode()
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def fake_hub(monkeypatch):
    devices = [blind_json(id_=f"blind-{i}", current=0, target=0) for i in range(10)]
    for i, d in enumerate(devices):
        d["attributes"]["customName"] = f"Rollo {i}"
    log = []

    def fake_request(self, method, url, **kwargs):
        route = url.split("/v1", 1)[1]
        log.append((method, route))
        if route == "/devices":
            return Resp(devices)
        if route == "/scenes":
            return Resp([])
        if route.startswith("/devices/"):
            return Resp(next(d for d in devices if d["id"] == route.split("/")[2]))
        return Resp({})

    class FakeApp:
        def __init__(self, *a, **kw):
            pass

        def run_forever(self, **kw):
            import time

            time.sleep(0.05)

        def close(self):
            pass

    monkeypatch.setattr("requests.Session.request", fake_request)
    monkeypatch.setattr("websocket.WebSocketApp", FakeApp)
    return log


async def test_setup_and_request_budget(hass, fake_hub):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IP_ADDRESS: "192.0.2.3", CONF_TOKEN: "tok", "hide_device_set_bulbs": True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    covers = hass.states.async_entity_ids("cover")
    assert len(covers) == 10
    state = hass.states.get(covers[0])
    assert state.state == "open"
    assert state.attributes["current_position"] == 100

    fake_hub.clear()
    # 2 minutes: upstream polled every entity every 15-30 s (here ~10 covers +
    # 10 battery sensors = ~60 requests). Now: zero.
    now = dt_util.utcnow()
    for sec in range(15, 121, 15):
        async_fire_time_changed(hass, now + timedelta(seconds=sec))
        await hass.async_block_till_done()
    assert [r for r in fake_hub if r[1].startswith("/devices/")] == []
    assert fake_hub == []

    # after the resync interval: exactly one bulk request
    fake_hub.clear()
    async_fire_time_changed(hass, now + timedelta(minutes=5, seconds=5))
    await hass.async_block_till_done()
    await hass.async_add_executor_job(lambda: None)
    await hass.async_block_till_done()
    assert fake_hub == [("GET", "/devices")]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
