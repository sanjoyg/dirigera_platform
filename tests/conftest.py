"""Fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture(autouse=True)
def clean_registry():
    from custom_components.dirigera_platform.hub_event_listener import hub_event_listener

    hub_event_listener.device_registry.clear()
    yield
    hub_event_listener.device_registry.clear()


def blind_json(id_="blind-1", current=0, target=0, battery=50, reachable=True):
    return {
        "id": id_,
        "type": "blinds",
        "deviceType": "blinds",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "isReachable": reachable,
        "lastSeen": "2024-01-01T00:00:00.000Z",
        "attributes": {
            "customName": "Rollo",
            "model": "FYRTUR block-out roller blind",
            "manufacturer": "IKEA of Sweden",
            "firmwareVersion": "1.0",
            "hardwareVersion": "1",
            "blindsCurrentLevel": current,
            "blindsTargetLevel": target,
            "blindsState": "stopped",
            "batteryPercentage": battery,
        },
        "capabilities": {"canSend": [], "canReceive": ["blindsTargetLevel", "customName"]},
        "room": {"id": "r1", "name": "Separate", "color": "c", "icon": "i"},
        "deviceSet": [],
        "remoteLinks": [],
        "isHidden": False,
    }
