"""Separate read-only web transport. Never inherit browser cookies, proxies or control credentials."""
import ipaddress,json,socket,time
from html.parser import HTMLParser
from urllib.parse import urlsplit
import httpx
from pydantic import ValidationError
from ...core import config
from ...core.errors import AppError
from ...core.net import pinned_request
from ...core.browser_urls import http_url
from ...engine.web_contract import WebSettings,WEB_ARGUMENTS,tool_definitions,origin
from ...engine.browser_network import DestinationPolicy,EgressDenied
from .http_api import HttpApiTools
from .base import redact_values

MAX_RESPONSE=256*1024


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.ignored=0;self.parts=[];self.title=[];self.in_title=False
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','noscript','template'}:self.ignored+=1
        if tag=='title':self.in_title=True
    def handle_endtag(self,tag):
        if tag in {'script','style','noscript','template'}:self.ignored=max(0,self.ignored-1)
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if not self.ignored:
            self.parts.append(data)
            if self.in_title:self.title.append(data)


class WebTools:
    id='web'
    secret_fields=('search_headers',)
    settings_limit=16384
    settings_schema=WebSettings.model_json_schema()

    @staticmethod
    def settings(value):
        try:return WebSettings.model_validate(value)
        except (ValueError,TypeError,ValidationError):raise AppError('MCP_CONFIG_INVALID',field='settings') from None

    @staticmethod
    def headers(secrets):
        if set(secrets)-{'search_headers'}:raise AppError('MCP_CONFIG_INVALID',field='secrets')
        return HttpApiTools.headers({'headers':secrets.get('search_headers')})

    def validate(self,uid,settings,secrets):
        self.authorize(uid,settings);self.headers(secrets)
        if 'search_headers' in secrets and not self.settings(settings).search:raise AppError('MCP_CONFIG_INVALID',field='secrets.search_headers')

    def authorize(self,uid,settings,allow_org=True):
        if not config.browser_enabled():raise AppError('BROWSER_DISABLED')
        self.settings(settings)

    def tools(self,settings):
        self.authorize(None,settings);return tool_definitions(self.settings(settings))

    @staticmethod
    def read(url,*,headers=None,params=None,allowed_origins=(),infrastructure=False):
        """One pinned public destination, verified TLS, no redirects/proxy/cookie jar reuse."""
        target=urlsplit(http_url(url))
        destination=DestinationPolicy.public_discovery(allowed_origins,resolver=socket.getaddrinfo).resolve(target.scheme,target.hostname,target.port or (443 if target.scheme=='https' else 80),infrastructure=infrastructure)
        pinned,authority,extensions=pinned_request(url,destination.address)
        deadline=time.monotonic()+30
        with httpx.Client(timeout=httpx.Timeout(20,connect=5),follow_redirects=False,trust_env=False,verify=True) as client:
            with client.stream('GET',pinned,headers={**(headers or {}),**authority,'Accept-Encoding':'identity'},extensions=extensions,params=params) as response:
                if response.headers.get('content-encoding','identity').lower()!='identity':raise ValueError('Compressed web responses are unsupported')
                body=bytearray()
                for chunk in response.iter_bytes():
                    if len(body)+len(chunk)>MAX_RESPONSE or time.monotonic()>deadline:raise ValueError('Bounded web response exceeded')
                    body.extend(chunk)
                return response.status_code,response.headers.get('content-type','').split(';',1)[0].lower(),bytes(body)

    def execute(self,uid,settings,secrets,tool,args,key,allow_org=True):
        self.authorize(uid,settings,allow_org);parsed=self.settings(settings)
        if tool not in parsed.enabled_tools:raise AppError('MCP_TOOL_NOT_FOUND',tool=tool)
        value=WEB_ARGUMENTS[tool].model_validate(args)
        if tool=='search' and not value.query.strip():return {'status':'missing_input','missing':['query'],'untrusted':True}
        if tool=='fetch' and not value.url.strip():return {'status':'missing_input','missing':['url'],'untrusted':True}
        headers=self.headers(secrets)
        sensitive=list(headers.values())+[secret.split(' ',1)[-1] for name,secret in headers.items() if name.lower()=='authorization']
        try:
            if tool=='search':
                if parsed.search is None:return {'status':'unsupported','reason':'search_not_configured','results':[],'untrusted':True}
                status,kind,body=self.read(parsed.search.endpoint,headers={**headers,'Accept':'application/json'},params={'q':value.query,'format':'json'},infrastructure=True)
                if status in {403,429}:return {'status':'unsupported','reason':'search_provider_refused','results':[],'untrusted':True}
                if status!=200 or kind!='application/json':return {'status':'unsupported','reason':'search_provider_response','results':[],'untrusted':True}
                raw=json.loads(body)
                if not isinstance(raw,dict):raise ValueError('Search shape')
                items=raw.get('results')
                if not isinstance(items,list):raise ValueError('Search shape')
                results=[];seen=set()
                for item in items[:100]:
                    if not isinstance(item,dict):continue
                    url=item.get('url')
                    try:
                        if not isinstance(url,str) or len(url)>2048:continue
                        if any(secret and secret in url for secret in sensitive):continue
                        http_url(url)
                        if parsed.allowed_origins and origin(url) not in parsed.allowed_origins:continue
                        try:address=ipaddress.ip_address(urlsplit(url).hostname)
                        except ValueError:address=None
                        if address is not None and not DestinationPolicy.address_allowed(str(address)):continue
                    except (ValueError,AppError):continue
                    if url in seen:continue
                    seen.add(url);results.append({'url':url,'title':redact_values(str(item.get('title') or ''),sensitive)[:300],
                        'snippet':redact_values(str(item.get('content') or ''),sensitive)[:1000]})
                    if len(results)>=value.limit:break
                return redact_values({'status':'complete' if results else 'empty','results':results,'untrusted':True},sensitive)
            http_url(value.url)
            if parsed.allowed_origins and origin(value.url) not in parsed.allowed_origins:return {'status':'policy_denied','untrusted':True}
            status,kind,body=self.read(value.url,headers={'Accept':'text/html,text/plain,application/json'},allowed_origins=parsed.allowed_origins)
            if 300<=status<400:return {'status':'unsupported','reason':'redirect_requires_explicit_url','untrusted':True}
            if status in {403,429}:return {'status':'challenge_required','untrusted':True}
            if status!=200:return {'status':'failed','http_status':status,'untrusted':True}
            if kind not in {'text/html','text/plain','application/json'}:return {'status':'unsupported','reason':'content_type','untrusted':True}
            text=body.decode('utf-8',errors='replace');title=''
            if kind=='text/html':
                page=PageText();page.feed(text);text=' '.join(' '.join(page.parts).split());title=' '.join(page.title)
            safe=redact_values({'text':text,'title':title},sensitive)
            return {'status':'complete' if text else 'empty','origin':origin(value.url),'title':safe['title'][:300],
                'text':safe['text'][:value.max_chars],'truncated':len(safe['text'])>value.max_chars,'untrusted':True}
        except (AppError,EgressDenied):return {'status':'policy_denied','untrusted':True}
        except (ValueError,TypeError,KeyError,RecursionError,httpx.HTTPError):return {'status':'failed','reason':'web_response_unavailable','untrusted':True}

    def reconcile(self,*args,**kwargs):return None
