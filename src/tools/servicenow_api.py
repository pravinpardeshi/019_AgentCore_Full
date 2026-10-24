"""Reusable ServiceNow Table API tool.

Reads connection settings from config/.env:
    SERVICENOW_URL        https://dev389543.service-now.com/
    SERVICENOW_USER       API username (basic auth)
    SERVICENOW_PASSWORD   API password / password token
    SERVICENOW_TOKEN      (optional) OAuth bearer token — used if set, overrides basic auth

Usage:
    from src.tools.servicenow_api import servicenow
    servicenow.get_open_incidents(limit=10)
    servicenow.get_change_records(limit=10)
    servicenow.get_user_email("John Smith")
"""
import os
from typing import Optional
import httpx

DEFAULT_FIELDS = {
    "incident": "number,short_description,state,priority,category,assigned_to,opened_at",
    "change_request": "number,short_description,state,type,risk,assigned_to,planned_start_date",
    "sys_user": "name,user_name,email,department",
}


def _cfg(env_key: str, setting_name: str) -> str:
    val = os.getenv(env_key, "")
    if not val:
        try:
            from config.config import settings
            val = getattr(settings, setting_name, "") or ""
        except Exception:
            val = ""
    return val


class ServiceNowTool:
    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None,
                 password: Optional[str] = None, token: Optional[str] = None, timeout: float = 30.0):
        self._base_url = base_url
        self._username = username
        self._password = password
        self._token = token
        self.timeout = timeout

    @property
    def base_url(self) -> str:
        return (self._base_url or _cfg("SERVICENOW_URL", "servicenow_url")).rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url) and bool(self._token or self._username or _cfg("SERVICENOW_USER", "servicenow_user"))

    def _headers_and_auth(self):
        token = self._token or _cfg("SERVICENOW_TOKEN", "servicenow_token")
        if token:
            return {"Accept": "application/json", "Authorization": f"Bearer {token}"}, None
        user = self._username or _cfg("SERVICENOW_USER", "servicenow_user")
        password = self._password or _cfg("SERVICENOW_PASSWORD", "servicenow_password")
        if not user:
            return {"Accept": "application/json"}, None
        return {"Accept": "application/json"}, (user, password)

    def _get(self, path: str, params: dict) -> dict:
        if not self.is_configured:
            raise RuntimeError("ServiceNow not configured (set SERVICENOW_USER/SERVICENOW_PASSWORD or SERVICENOW_TOKEN)")
        headers, auth = self._headers_and_auth()
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout, verify=True) as client:
            resp = client.get(url, params=params, headers=headers, auth=auth)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _fmt(records: list, fields: list, empty_msg: str) -> str:
        if not records:
            return empty_msg
        lines = []
        for r in records:
            parts = [f"{f}={r.get(f) or '-'}" for f in fields if f in r]
            lines.append(" | ".join(str(p) for p in parts))
        return "\n".join(lines)

    def get_open_incidents(self, limit: int = 10, query: str = "") -> str:
        """Open (active) incidents. Optional extra query uses ServiceNow encoded query syntax."""
        encoded = "active=true^ORDERBYDESCsys_created_on" + (f"^{query}" if query else "")
        params = {
            "sysparm_query": encoded,
            "sysparm_limit": limit,
            "sysparm_fields": DEFAULT_FIELDS["incident"],
        }
        data = self._get("/api/now/table/incident", params)
        return self._fmt(data.get("result", []), DEFAULT_FIELDS["incident"].split(","), "No open incidents found.")

    def get_change_records(self, limit: int = 10, query: str = "") -> str:
        """Open change records (change_request table)."""
        encoded = "active=true^ORDERBYDESCsys_created_on" + (f"^{query}" if query else "")
        params = {
            "sysparm_query": encoded,
            "sysparm_limit": limit,
            "sysparm_fields": DEFAULT_FIELDS["change_request"],
        }
        data = self._get("/api/now/table/change_request", params)
        return self._fmt(data.get("result", []), DEFAULT_FIELDS["change_request"].split(","), "No open change records found.")

    def get_user_email(self, name: str) -> str:
        """Look up a user's email by name (partial match) or user_name."""
        if not name or not name.strip():
            return "Provide a user name to look up."
        safe = name.strip().replace("^", " ").replace(",", " ")
        encoded = f"nameLIKE{safe}^ORuser_nameLIKE{safe}"
        params = {
            "sysparm_query": encoded,
            "sysparm_limit": 5,
            "sysparm_fields": DEFAULT_FIELDS["sys_user"],
        }
        data = self._get("/api/now/table/sys_user", params)
        rows = data.get("result", [])
        if not rows:
            return f"No user found matching: {name}"
        return self._fmt(rows, ["name", "user_name", "email", "department"], f"No user found matching: {name}")


servicenow = ServiceNowTool()
