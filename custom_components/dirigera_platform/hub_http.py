"""Shared, keep-alive HTTP transport for the Dirigera hub.

The upstream ``dirigera`` library calls ``requests.get/patch/post/delete``
directly, which opens a brand new TCP + TLS connection for every single
request. The Dirigera hub has a small CPU and the TLS handshake is by far the
most expensive part of a request, so with many entities this alone can make the
hub unresponsive (also for the IKEA Home smart app).

This module replaces those four methods on ``dirigera.Hub`` with versions that
use one ``requests.Session`` per hub address (connection pooling / keep-alive)
and a small, safe retry policy for transient connection problems.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dirigera import Hub

logger = logging.getLogger("custom_components.dirigera_platform")

REQUEST_TIMEOUT = 10  # seconds, same as upstream library
POOL_SIZE = 4         # parallel connections per hub, keeps the hub load bounded

_sessions: Dict[str, requests.Session] = {}
_sessions_lock = threading.Lock()
_patched = False


def _build_session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=1,
        status=0,
        backoff_factor=0.5,
        # All methods used against the hub are idempotent for our use
        # (PATCH sets absolute values such as a target level).
        allowed_methods=frozenset({"GET", "PATCH", "DELETE"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        pool_connections=1, pool_maxsize=POOL_SIZE, pool_block=True, max_retries=retry
    )
    session = requests.Session()
    session.mount("https://", adapter)
    session.verify = False
    return session


def get_session(base_url: str) -> requests.Session:
    with _sessions_lock:
        session = _sessions.get(base_url)
        if session is None:
            session = _build_session()
            _sessions[base_url] = session
        return session


def close_sessions() -> None:
    with _sessions_lock:
        for session in _sessions.values():
            try:
                session.close()
            except Exception:  # pragma: no cover - best effort
                pass
        _sessions.clear()


def _get(self: Hub, route: str) -> Any:
    response = get_session(self.api_base_url).get(
        f"{self.api_base_url}{route}", headers=self.headers(), timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def _patch(self: Hub, route: str, data: List[Dict[str, Any]]) -> Any:
    response = get_session(self.api_base_url).patch(
        f"{self.api_base_url}{route}",
        headers=self.headers(),
        json=data,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text


def _post(self: Hub, route: str, data: Optional[Dict[str, Any]] = None) -> Any:
    response = get_session(self.api_base_url).post(
        f"{self.api_base_url}{route}",
        headers=self.headers(),
        json=data,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    if len(response.content) == 0:
        return None
    return response.json()


def _delete(self: Hub, route: str, data: Optional[Dict[str, Any]] = None) -> Any:
    response = get_session(self.api_base_url).delete(
        f"{self.api_base_url}{route}",
        headers=self.headers(),
        json=data,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    if len(response.content) == 0:
        return None
    return response.json()


def apply_patch() -> None:
    """Install the keep-alive transport on dirigera.Hub (idempotent)."""
    global _patched
    if _patched:
        return
    Hub.get = _get
    Hub.patch = _patch
    Hub.post = _post
    Hub.delete = _delete
    _patched = True
    logger.debug("dirigera.Hub patched to use a shared keep-alive HTTP session")
