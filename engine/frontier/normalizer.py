import re
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Tuple, Optional, Set

TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_reader", "fbclid", "gclid", "spm", "_hsenc", "_hsmi",
    "mc_cid", "mc_eid", "ref", "from", "source", "yclid", "zanpid"
}

def normalize_url(raw_url: str) -> Tuple[str, str, str]:
    """
    Normalize raw URL and return (normalized_url, url_hash, domain).
    - Lowercase scheme and domain
    - Strip fragments (#...)
    - Remove tracking query parameters
    - Alphabetically sort query parameters
    - Remove default ports (80 for http, 443 for https)
    - Remove trailing slash if path != '/'
    """
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower() or "http"
    netloc = parsed.netloc.lower()

    # Strip default ports
    if ":" in netloc:
        host, port = netloc.split(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    # Normalize path
    path = parsed.path
    if not path:
        path = "/"
    elif len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Filter & sort query parameters
    filtered_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            if k.lower() not in TRACKING_PARAMS:
                filtered_params.append((k, v))
        filtered_params.sort(key=lambda x: x[0])

    new_query = urlencode(filtered_params)
    normalized = urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
    url_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    domain = netloc.split(":")[0]

    return normalized, url_hash, domain

def is_valid_http_url(url: str) -> bool:
    """Check whether URL is a valid http or https URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def is_safe_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """
    Validate whether URL is safe to fetch and prevent SSRF attacks.
    Blocks localhost, 127.0.0.1, link-local (169.254.x.x), and RFC1918 private subnets.
    """
    if not is_valid_http_url(url):
        return False, "无效的 HTTP/HTTPS URL 格式"

    if allow_private:
        return True, ""

    try:
        import ipaddress
        import socket

        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "URL 缺少有效主机名"

        hostname_lower = hostname.lower()
        if hostname_lower in ("localhost", "127.0.0.1", "::1"):
            return False, "禁止访问本地回环地址 (localhost / 127.0.0.1)"

        # Check IP address directly or resolve hostname
        try:
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"禁止访问私有/保留 IP 地址: {hostname}"
        except ValueError:
            # Not an IP literal, resolve domain
            try:
                resolved_ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(resolved_ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False, f"域名解析指向私有局域网 IP ({resolved_ip_str})，已拦截"
            except Exception:
                pass  # DNS resolution failure will be handled by fetcher

        return True, ""
    except Exception as e:
        return False, f"URL 安全校验异常: {e}"

def is_in_scope(target_url: str, base_url: str, scope: str = "domain",
                scope_regex: Optional[str] = None) -> bool:
    """
    Verify if target_url falls within the allowed crawl scope.
    Scope options:
    - 'page': Only exact base_url
    - 'path': Under base_url's path prefix
    - 'domain': Same domain and port
    - 'subdomain': Matches base domain and all subdomains
    - 'regex': Matches custom regex pattern
    """
    if scope == "page":
        norm_t, _, _ = normalize_url(target_url)
        norm_b, _, _ = normalize_url(base_url)
        return norm_t == norm_b

    if scope == "regex" and scope_regex:
        return bool(re.search(scope_regex, target_url))

    parsed_t = urlparse(target_url)
    parsed_b = urlparse(base_url)

    domain_t = parsed_t.netloc.split(":")[0].lower()
    domain_b = parsed_b.netloc.split(":")[0].lower()

    if scope == "domain":
        return domain_t == domain_b

    if scope == "path":
        if domain_t != domain_b:
            return False
        import posixpath
        if parsed_b.path.endswith("/"):
            prefix = parsed_b.path.rstrip("/")
        else:
            dir_prefix = posixpath.dirname(parsed_b.path).rstrip("/")
            prefix = dir_prefix if dir_prefix else parsed_b.path.rstrip("/")
        return parsed_t.path.startswith(prefix)

    if scope == "subdomain":
        # Check if domain_t ends with .domain_b or equals domain_b
        return domain_t == domain_b or domain_t.endswith("." + domain_b)

    return domain_t == domain_b
