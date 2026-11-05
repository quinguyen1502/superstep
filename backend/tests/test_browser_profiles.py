"""No live credentials: synthetic profile isolation, encrypted CRUD and revocation digest."""
import json
import time
import pytest
from app.core.errors import AppError
from app.engine.browser_contract import BrowserSettings
from app.engine.browser_profiles import parse_seed, validate_profile, ProfileDenied
from app.services.browser_profile_service import BrowserProfileService, browser_configuration
from app.api.deps import mcp_service
from tests.test_browser_connections import c, api, user, H, create, enabled
from tests.test_browser_runtime import context


def settings(): return BrowserSettings(profile={'name': 'fixture-profile', 'origins': ['https://allowed.test:8443']})
def state():
    return {'cookies': [{'name': 'login', 'value': 'synthetic-cookie', 'domain': 'allowed.test', 'path': '/', 'expires': -1,
                         'httpOnly': True, 'secure': True, 'sameSite': 'Lax'}],
            'origins': [{'origin': 'https://allowed.test:8443', 'localStorage': [{'name': 'login', 'value': 'synthetic-storage'}]}]}


def test_profile_effective_origins_are_closed_and_seed_bound():
    seed = parse_seed(settings(), 'user:owner', json.dumps(state()))
    assert validate_profile(settings(), 'user:owner', seed).allowed_origins == ['https://allowed.test:8443']
    with pytest.raises(ProfileDenied): validate_profile(settings(), 'user:other', seed)
    with pytest.raises(ProfileDenied): validate_profile(BrowserSettings(), 'user:owner', seed)
    with pytest.raises(ProfileDenied): validate_profile(settings(), 'user:owner', None)


@pytest.mark.parametrize('mutation', ['domain', 'outside', 'http', 'expiry', 'indexeddb', 'insecure', 'duplicate', 'oversize'])
def test_unsupported_profile_state_refuses(mutation):
    value, config = state(), settings()
    if mutation == 'domain': value['cookies'][0]['domain'] = '.allowed.test'
    if mutation == 'outside': value['origins'][0]['origin'] = 'https://other.test'
    if mutation == 'http': config = BrowserSettings(profile={'name':'p','origins':['http://allowed.test']})
    if mutation == 'expiry': value['cookies'][0]['expires'] = time.time() - 1
    if mutation == 'indexeddb': value['origins'][0]['indexedDB'] = []
    if mutation == 'insecure': value['cookies'][0]['secure'] = False
    if mutation == 'duplicate': value['cookies'].append(value['cookies'][0])
    if mutation == 'oversize': value['origins'][0]['localStorage'] = [{'name': str(i), 'value':'x'*4096} for i in range(30)]
    with pytest.raises(ProfileDenied): parse_seed(config, 'user:owner', json.dumps(value))


def test_profile_encrypted_personal_owner_only_and_update_invalidates(c):
    owner, stranger = user(c), user(c)
    response = create(c, owner, settings=settings().model_dump(), secrets={'profile_state':json.dumps(state())})
    assert response.status_code == 200, response.text
    public = response.json()['data']; svc = mcp_service(); row = svc.repo.get(public['id'])
    assert public['secrets'] == {'profile_state':'••••'} and 'synthetic-cookie' not in response.text + row.secrets
    original_digest = browser_configuration(row)
    bound = context('user:' + owner['id']).model_copy(update={'connection_id':row.id, 'configuration':original_digest})
    actual, seed = BrowserProfileService.prepare(row, bound)
    assert actual.allowed_origins == settings().profile.origins and seed.principal_id == bound.principal_id
    for principal in ['user:' + stranger['id'], 'visitor:one', 'app:one']:
        with pytest.raises(AppError): BrowserProfileService.prepare(row, bound.model_copy(update={'principal_id':principal}))
    row.scope = 'org'
    with pytest.raises(AppError): BrowserProfileService.prepare(row, bound.model_copy(update={'configuration':browser_configuration(row)}))
    from app.services.mcp_service import McpService
    svc.repo.save(row)
    with pytest.raises(AppError) as denied:
        McpService(svc.repo,is_admin=lambda uid:True).update(row.id,owner['id'],'Org profile',settings=settings().model_dump())
    assert denied.value.code == 'BROWSER_PROFILE_DENIED'
    row.scope = 'user';svc.repo.save(row)
    removed = c.put(f"/api/mcp/servers/{row.id}", headers=H(owner['token']), json={'name':'Removed profile','settings':{},'secrets':{}})
    assert removed.status_code == 200
    changed = svc.repo.get(row.id)
    assert changed.secrets is None and browser_configuration(changed) != original_digest
    with pytest.raises(AppError): BrowserProfileService.prepare(changed, bound)
    svc.repo.delete(row.id)
