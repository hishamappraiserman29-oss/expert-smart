"""
oauth_manager.py — OAuth 2.0 authentication for integrations.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)


class OAuthConfig:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        scopes: List[str],
        redirect_uri: str = "http://localhost:5000/oauth/callback",
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.scopes = scopes
        self.redirect_uri = redirect_uri


class OAuthToken:
    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: int = 3600,
        refresh_token: Optional[str] = None,
    ) -> None:
        self.access_token = access_token
        self.token_type = token_type
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.refresh_token = refresh_token

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def to_dict(self) -> Dict:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat(),
            "refresh_token": self.refresh_token,
        }


class OAuthManager:
    """Manage OAuth 2.0 authorization-code flows."""

    def __init__(self) -> None:
        self.configs: Dict[str, OAuthConfig] = {}
        self.tokens: Dict[str, OAuthToken] = {}
        self.states: Dict[str, str] = {}

    def register_oauth(self, service_name: str, config: OAuthConfig) -> None:
        self.configs[service_name] = config
        logger.info("OAuth registered: %s", service_name)

    def get_authorization_url(
        self, service_name: str, state: Optional[str] = None
    ) -> str:
        if service_name not in self.configs:
            raise ValueError(f"Service not registered: {service_name}")
        config = self.configs[service_name]
        if not state:
            state = str(uuid.uuid4())
        self.states[state] = service_name
        params = urlencode({
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(config.scopes),
            "response_type": "code",
            "state": state,
        })
        return f"{config.authorize_url}?{params}"

    def exchange_code_for_token(
        self, service_name: str, code: str, state: Optional[str] = None
    ) -> Optional[OAuthToken]:
        if state and state not in self.states:
            logger.error("Invalid OAuth state — possible CSRF")
            return None
        if service_name not in self.configs:
            logger.error("Service not registered: %s", service_name)
            return None

        config = self.configs[service_name]
        try:
            resp = requests.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config.redirect_uri,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                logger.error("Token exchange HTTP %s", resp.status_code)
                return None
            data = resp.json()
            token = OAuthToken(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
                refresh_token=data.get("refresh_token"),
            )
            self.tokens[service_name] = token
            if state and state in self.states:
                del self.states[state]
            logger.info("Token obtained for %s", service_name)
            return token
        except Exception as exc:
            logger.error("Error exchanging code: %s", exc)
            return None

    def refresh_token(self, service_name: str) -> Optional[OAuthToken]:
        token = self.tokens.get(service_name)
        if not token or not token.refresh_token:
            logger.error("No refresh token for %s", service_name)
            return None
        config = self.configs[service_name]
        try:
            resp = requests.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "refresh_token": token.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            if resp.status_code != 200:
                logger.error("Token refresh HTTP %s", resp.status_code)
                return None
            data = resp.json()
            new_token = OAuthToken(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
                refresh_token=data.get("refresh_token", token.refresh_token),
            )
            self.tokens[service_name] = new_token
            logger.info("Token refreshed for %s", service_name)
            return new_token
        except Exception as exc:
            logger.error("Error refreshing token: %s", exc)
            return None

    def get_token(self, service_name: str) -> Optional[OAuthToken]:
        token = self.tokens.get(service_name)
        if token is None:
            return None
        if token.is_expired():
            return self.refresh_token(service_name)
        return token

    def make_authenticated_request(
        self, service_name: str, method: str, url: str, **kwargs: Any
    ) -> Optional[Any]:
        token = self.get_token(service_name)
        if not token:
            logger.error("No token for %s", service_name)
            return None
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"{token.token_type} {token.access_token}"
        kwargs["headers"] = headers
        try:
            func = getattr(requests, method.lower(), None)
            if func is None:
                logger.error("Unsupported HTTP method: %s", method)
                return None
            resp = func(url, **kwargs)
            if resp.status_code >= 400:
                logger.error("API error %s: %s", resp.status_code, resp.text)
                return None
            return resp.json()
        except Exception as exc:
            logger.error("Request error: %s", exc)
            return None


oauth_manager = OAuthManager()
