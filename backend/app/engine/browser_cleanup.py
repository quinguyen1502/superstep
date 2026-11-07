"""Restart cleanup for one operator-assigned remote controller identity, never global prefixes."""
import re
import subprocess
from .browser_worker import BrowserWorkerError


def reap_controller(docker, identity):
    if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', identity): raise BrowserWorkerError('unsupported')
    selector = 'label=superstep.browser.controller=' + identity
    def run(*args):
        try:
            result = subprocess.run([docker, *args], capture_output=True, text=True, timeout=30)
            if result.returncode or len(result.stdout) > 128 * 1024: raise BrowserWorkerError()
            return result.stdout.splitlines()
        except (OSError, subprocess.TimeoutExpired): raise BrowserWorkerError() from None
    containers = run('ps', '-aq', '--filter', selector)
    if any(not re.fullmatch(r'[a-f0-9]{12,64}', value) for value in containers): raise BrowserWorkerError()
    for value in containers: run('rm', '-fv', value)
    volumes = run('volume', 'ls', '-q', '--filter', selector)
    if any(not re.fullmatch(r'ss-browser-[a-f0-9]{32}-socket', value) for value in volumes): raise BrowserWorkerError()
    for value in volumes: run('volume', 'rm', value)
