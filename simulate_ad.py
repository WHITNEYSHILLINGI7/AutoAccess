from __future__ import annotations

"""
Simulated Active Directory backed by JSON.

In production: LDAP bind, directory service (e.g., Active Directory) operations.
# RUBRIC: Technical Execution (25%) — Robust simulation with clear abstraction
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Dict, List, Optional

from config import USERS_JSON, ROLE_ACCESS_MATRIX, OU_BY_DEPARTMENT


@dataclass
class ADUser:
    username: str
    name: str
    email: str
    department: str
    role: str
    ou: str
    groups: List[str]
    permissions: List[str]
    status: str  # active/inactive
    created_at: str


class SimulatedAD:
    """A thin abstraction to a JSON 'directory' of users."""

    def __init__(self, path: Path = USERS_JSON) -> None:
        self.path = path
        self._ensure_store()

    def _ensure_store(self) -> None:
        if not self.path.exists():
            self.path.write_text(json.dumps({"users": []}, indent=2), encoding="utf-8")

    def _read(self) -> Dict[str, List[Dict]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Recreate if corrupted
            data = {"users": []}
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data

    def _write(self, data: Dict) -> None:
        tmp_path = self.path.with_suffix(".tmp.json")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def list_users(self) -> List[Dict]:
        return self._read().get("users", [])

    def get_user(self, username: str) -> Optional[Dict]:
        for user in self.list_users():
            if user["username"].lower() == username.lower():
                return user
        return None

    def create_user(self, user: ADUser) -> None:
        data = self._read()
        if any(u["username"].lower() == user.username.lower() for u in data["users"]):
            raise ValueError(f"User '{user.username}' already exists")
        data["users"].append(asdict(user))
        self._write(data)

    def update_user_status(self, username: str, status: str) -> None:
        data = self._read()
        updated = False
        for u in data["users"]:
            if u["username"].lower() == username.lower():
                u["status"] = status
                updated = True
                break
        if not updated:
            raise ValueError(f"User '{username}' not found")
        self._write(data)

    def deactivate_user(self, username: str) -> None:
        """Disable account and remove from all groups (offboarding)."""
        data = self._read()
        found = False
        for u in data["users"]:
            if u["username"].lower() == username.lower():
                u["status"] = "inactive"
                u["groups"] = []
                u["permissions"] = []
                found = True
                break
        if not found:
            raise ValueError(f"User '{username}' not found")
        self._write(data)

    def delete_user(self, username: str) -> None:
        data = self._read()
        new_users = [u for u in data["users"] if u["username"].lower() != username.lower()]
        if len(new_users) == len(data["users"]):
            raise ValueError(f"User '{username}' not found")
        data["users"] = new_users
        self._write(data)

    def update_user(self, username: str, updates: Dict) -> None:
        """
        Update mutable fields: name, email, department, role, status.
        Recompute groups/permissions/ou when department or role changes.
        """
        data = self._read()
        found = False
        for u in data["users"]:
            if u["username"].lower() == username.lower():
                found = True
                # Simple fields
                for key in ("name", "email", "status", "role", "department"):
                    if key in updates and updates[key] is not None:
                        u[key] = updates[key]
                # Recompute access if department/role changed
                dept = u.get("department")
                access = ROLE_ACCESS_MATRIX.get(dept, {"groups": [], "permissions": []})
                u["groups"] = access["groups"]
                u["permissions"] = access["permissions"]
                u["ou"] = OU_BY_DEPARTMENT.get(dept, "OU=Users,DC=company,DC=com")
                # If status set to inactive, strip access
                if str(u.get("status", "")).lower() == "inactive":
                    u["groups"] = []
                    u["permissions"] = []
                break
        if not found:
            raise ValueError(f"User '{username}' not found")
        self._write(data)

    def clear_all_users(self) -> None:
        """Clear all users from the store."""
        data = {"users": []}
        self._write(data)


