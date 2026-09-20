"""
DMZ Secure OT Access Gateway - Dual-World Reverse Proxy Router
"""
import requests
from flask import request, Response
try:
    from . import config
except (ImportError, ValueError):
    import config

HOP_BY_HOP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate',
    'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
}

def forward_request(target_base_url, subpath="", user="operator", role="operator"):
    """
    Reverse-proxies incoming HTTP requests to the target workstation backend,
    preserving cookies, query parameters, form data, and streaming responses.
    """
    clean_subpath = subpath.lstrip('/')
    url = f"{target_base_url}/{clean_subpath}" if clean_subpath else target_base_url

    # Prepare forwarding headers
    headers = {k: v for k, v in request.headers if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != 'host'}
    headers['X-Forwarded-For'] = request.headers.get('X-Forwarded-For', request.remote_addr)
    headers['X-Forwarded-Host'] = request.host
    headers['X-Gateway-Auth'] = 'true'
    headers['X-Gateway-User'] = user or 'operator'
    headers['X-Gateway-Role'] = role or 'operator'

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=8.0
        )

        response_headers = []
        for k, v in resp.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != 'content-length':
                # Rewrite redirect Location headers if pointing to backend port 5001
                if k.lower() == 'location':
                    v = v.replace(':5001', f':{config.GATEWAY_PORT}').replace('/dashboard', '/proxy/dashboard')
                response_headers.append((k, v))

        return Response(
            resp.content,
            status=resp.status_code,
            headers=response_headers,
            content_type=resp.headers.get('Content-Type')
        )
    except Exception as e:
        return Response(
            f"Gateway Routing Error: Backend unreachable ({e})",
            status=502,
            content_type="text/plain"
        )
