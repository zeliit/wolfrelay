import json
import ipaddress
import logging
import os
import re
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("wolfrelay")

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
)
ACCEPT_LANGUAGE = os.getenv("ACCEPT_LANGUAGE", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")
HTML_ACCEPT = os.getenv(
    "HTML_ACCEPT",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
)
IMAGE_ACCEPT = os.getenv(
    "IMAGE_ACCEPT",
    "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://flaresolverr:8191/v1").strip()

ALLOWED_HOST_REGEX = re.compile(r"^wftoon\d+\.com$", re.IGNORECASE)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept-Language": ACCEPT_LANGUAGE,
        "Connection": "close",
    }
)


def parse_target_url(raw_url: str):
    target_url = (raw_url or "").strip()
    if not target_url:
        raise ValueError("url is required")

    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http/https is allowed")

    if not parsed.hostname:
        raise ValueError("host is required")

    return target_url, parsed


def validate_allowed_site_url(raw_url: str) -> str:
    target_url, parsed = parse_target_url(raw_url)
    hostname = parsed.hostname or ""
    if not ALLOWED_HOST_REGEX.fullmatch(hostname):
        raise ValueError(f"host is not allowed: {hostname}")

    return target_url


def validate_public_asset_url(raw_url: str) -> str:
    target_url, parsed = parse_target_url(raw_url)
    hostname = parsed.hostname or ""

    if hostname.lower() == "localhost":
        raise ValueError("localhost is not allowed")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError(f"private host is not allowed: {hostname}")

    return target_url


def optional_referer(*, allow_public_asset: bool = False) -> str | None:
    referer = (request.args.get("referer") or "").strip()
    if not referer:
        return None
    if allow_public_asset:
        return validate_public_asset_url(referer)
    return validate_allowed_site_url(referer)


def direct_fetch(target_url: str, accept: str, referer: str | None = None) -> requests.Response:
    headers = {"Accept": accept}
    if referer:
        headers["Referer"] = referer

    response = session.get(
        target_url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def flaresolverr_fetch(target_url: str) -> tuple[bytes, str, str]:
    if not FLARESOLVERR_URL:
        raise RuntimeError("flaresolverr is not configured")

    payload = {
        "cmd": "request.get",
        "url": target_url,
        "maxTimeout": REQUEST_TIMEOUT * 1000,
    }

    try:
        response = requests.post(
            FLARESOLVERR_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=REQUEST_TIMEOUT + 10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"flaresolverr is unavailable: {FLARESOLVERR_URL}") from e

    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message") or "flaresolverr request failed")

    solution = data.get("solution") or {}
    body = (solution.get("response") or "").encode("utf-8")
    final_url = (solution.get("url") or target_url).strip()
    content_type = "text/html; charset=utf-8"
    return body, content_type, final_url


def build_response(body: bytes, content_type: str, final_url: str, source: str) -> Response:
    response = Response(body)
    response.headers["Content-Type"] = content_type or "application/octet-stream"
    response.headers["X-WolfRelay-Source"] = source
    response.headers["X-WolfRelay-Url"] = final_url
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> Response:
    return jsonify({"status": "ok"})


@app.get("/html")
def html() -> Response:
    try:
        target_url = validate_allowed_site_url(request.args.get("url", ""))
        referer = optional_referer()
        logger.info("html request url=%s referer=%s", target_url, referer or "")

        try:
            response = direct_fetch(target_url, HTML_ACCEPT, referer=referer)
            return build_response(
                response.content,
                response.headers.get("Content-Type", "text/html; charset=euc-kr"),
                response.url,
                "direct",
            )
        except Exception as direct_error:
            logger.warning("direct html fetch failed url=%s error=%s", target_url, direct_error)
            body, content_type, final_url = flaresolverr_fetch(target_url)
            return build_response(body, content_type, final_url, "flaresolverr")
    except Exception as e:
        logger.exception("html relay failed")
        return jsonify({"error": str(e)}), 400


@app.get("/binary")
def binary() -> Response:
    try:
        target_url = validate_public_asset_url(request.args.get("url", ""))
        referer = optional_referer()
        logger.info("binary request url=%s referer=%s", target_url, referer or "")

        response = direct_fetch(target_url, IMAGE_ACCEPT, referer=referer)
        return build_response(
            response.content,
            response.headers.get("Content-Type", "application/octet-stream"),
            response.url,
            "direct",
        )
    except Exception as e:
        logger.exception("binary relay failed")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8911")))
