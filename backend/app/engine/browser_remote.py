"""Controlled remote worker, not raw CDP or a hosted Agent. Operator pins the TLS control plane."""
from dataclasses import dataclass
import ipaddress
import json
import ssl
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator

from ..core.browser_urls import http_url
from ..core.net import pinned_request
from .browser_contract import (WorkerEnvelope, BrowserSettings, ExecutionContext, ProfileSeed,
                               WorkerControl, ARGUMENT_MODELS)
from .browser_worker import LocalBrowserWorker, BrowserWorkerError

CAPABILITIES = {'version': 1, 'provider': 'browserless', 'boundary': 'network_none_unix_gateway_v1',
                'operations': list(ARGUMENT_MODELS), 'profile': 'https_host_only_v1',
                'proxy': ['direct', 'operator_default', 'custom_http_none_basic'], 'stealth': False, 'approval': 'target_bound_v1', 'fencing': 'lease_handoff_v1'}


class RemoteOpen(WorkerEnvelope):
    context: ExecutionContext
    settings: BrowserSettings
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    profile_seed: ProfileSeed | None = Field(default=None, repr=False)
    proxy_secrets: dict[str, str] = Field(default_factory=dict, max_length=2, repr=False)

    @model_validator(mode='after')
    def check_proxy_secrets(self):
        if self.settings.proxy.mode == 'custom' and self.settings.proxy.auth == 'basic':
            if set(self.proxy_secrets) != {'proxy_username', 'proxy_password'}: raise ValueError('Missing proxy credentials')
            if any(not value or len(value) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value) for value in self.proxy_secrets.values()):
                raise ValueError('Invalid proxy credentials')
        elif self.proxy_secrets: raise ValueError('Unused proxy credentials')
        return self


@dataclass(frozen=True)
class ApprovedController:
    endpoint: str
    address: str
    # A separate, operator-controlled deployment allowlist. Never constructed from model/tool args.
    def __post_init__(self):
        try:
            parsed = urlsplit(http_url(self.endpoint, origin=True))
            if parsed.scheme != 'https' or self.endpoint.endswith('/'): raise ValueError()
            ipaddress.ip_address(self.address)
        except (ValueError, TypeError): raise BrowserWorkerError('unsupported') from None


class RemoteTransport:
    def __init__(self, controller: ApprovedController, token: str, *, tls: ssl.SSLContext | bool = True):
        if not isinstance(controller, ApprovedController) or tls is False or not isinstance(token, str) or not 32 <= len(token) <= 4096 or any(ord(c) <= 32 or ord(c) >= 127 for c in token):
            raise BrowserWorkerError('unsupported')
        self.controller, self._token, self._tls = controller, token, tls

    def request(self, method, body=None, timeout=65):
        if method not in {'info', 'open', 'command', 'approve', 'artifact', 'close', 'health', 'inspect', 'renew'}: raise BrowserWorkerError('unsupported')
        url, headers, extensions = pinned_request(self.controller.endpoint + '/v1/' + method, self.controller.address)
        headers['Authorization'] = 'Bearer ' + self._token
        raw = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        if raw is not None and len(raw) > 256 * 1024: raise BrowserWorkerError('failed_before_effect')
        headers['Content-Type'] = 'application/json'
        try:
            with httpx.Client(verify=self._tls, trust_env=False, follow_redirects=False, timeout=timeout) as client:
                with client.stream('GET' if method == 'info' else 'POST', url, headers=headers, extensions=extensions, content=raw) as response:
                    if response.status_code != 200: raise BrowserWorkerError()
                    parts, size = [], 0
                    for part in response.iter_bytes():
                        size += len(part)
                        if size > 4 * 1024 * 1024: raise BrowserWorkerError()
                        parts.append(part)
                    result = json.loads(b''.join(parts))
                    if result.get('success') is not True or not isinstance(result.get('data'), dict): raise BrowserWorkerError()
                    return result['data']
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError): raise BrowserWorkerError() from None


class RemoteBrowserWorker(LocalBrowserWorker):
    """Reuse exact command/outcome/artifact semantics; override only infrastructure transport/lifetime."""
    def __init__(self, context, settings, transport: RemoteTransport):
        super().__init__(context, settings, docker='remote-control-only')
        self.transport = transport

    def _rpc(self, method, value, timeout=65):
        if self.closed: raise BrowserWorkerError('expired')
        return self.transport.request(method, value.model_dump(), timeout)

    def start(self, *, secrets=None, approved_proxies=(), operator_default=None, profile_seed=None):
        if self.started or self.closed or self.settings.provider != 'browserless' or approved_proxies or operator_default:
            raise BrowserWorkerError('unsupported')
        from .browser_profiles import validate_profile, ProfileDenied
        try: self.settings = validate_profile(self.settings, self.context.principal_id, profile_seed)
        except ProfileDenied: raise BrowserWorkerError('unsupported') from None
        if self.transport.request('info') != CAPABILITIES: raise BrowserWorkerError('unsupported')
        opened = RemoteOpen(context=self.context, settings=self.settings, request_id=self.session_id, profile_seed=profile_seed,
                            proxy_secrets={k: v for k, v in (secrets or {}).items() if k in {'proxy_username', 'proxy_password'}})
        try:
            result = self.transport.request('open', opened.model_dump())
            if result != {'status': 'ready', 'session_id': self.session_id, 'generation': 1}: raise BrowserWorkerError()
            self.started = True
            # Server's local supervisor owns watchdogs. A lost client never restores/replays a page.
            return self
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.closed and not self.cleanup_pending: return True
        self.cleanup_pending = False
        try:
            control = WorkerControl(context=self.context, session_id=self.session_id, generation=self.generation)
            if self.transport.request('close', control.model_dump()).get('status') != 'closed': self.cleanup_pending = True
        except BrowserWorkerError: self.cleanup_pending = True
        self.closed = True
        return not self.cleanup_pending

    @classmethod
    def attach(cls, context, settings, worker_id, transport, *, generation=1):
        import re
        if not isinstance(worker_id, str) or not re.fullmatch(r'[a-f0-9]{32}', worker_id): raise BrowserWorkerError()
        worker = cls(context, settings, transport)
        worker.session_id, worker.generation = worker_id, generation
        if worker.health().get('status') != 'ready': raise BrowserWorkerError()
        worker.started = True
        return worker

    def _arm_idle(self): pass  # remote controller's independent supervisor enforces this


def approved_transport(secrets, controllers):
    """Bind a connection token to an operator-allowlisted Browserless control plane.

    The connection never supplies or invents the control endpoint — only an approved
    controller list from operator config may be used (Accepted ).
    """
    token = secrets.get('browserless_token')
    approved = [item for item in controllers if isinstance(item, ApprovedController)]
    if not isinstance(token, str) or not approved:
        raise BrowserWorkerError('unsupported')
    if len(approved) != 1:
        # Multi-controller routing is operator config, not a connection-chosen CDP URL.
        raise BrowserWorkerError('unsupported')
    return RemoteTransport(approved[0], token)
