from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import streamlit as st

from config import DASHBOARD_TITLE, USERS_JSON, DB_PATH, EMAIL_LOG, SAMPLE_XLSX
from database import fetch_recent_users, fetch_errors, init_db


st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide")
st.title(DASHBOARD_TITLE)
st.caption("Live table of created users, errors, and activity metrics.")


def read_users_json(path: Path = USERS_JSON) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return pd.DataFrame(data.get("users", []))
    except Exception:
        return pd.DataFrame(columns=["username", "name", "email", "department", "role", "status", "created_at"])


@st.cache_data(ttl=2.0)
def get_users_df() -> pd.DataFrame:
    return read_users_json()


@st.cache_data(ttl=2.0)
def get_audit_log(limit: int = 50) -> pd.DataFrame:
    init_db(DB_PATH)
    rows = fetch_recent_users(limit=limit)
    df = pd.DataFrame(rows, columns=["event_time", "action", "username", "details"])
    return df


@st.cache_data(ttl=2.0)
def get_errors_df(limit: int = 50) -> pd.DataFrame:
    init_db(DB_PATH)
    rows = fetch_errors(limit=limit)
    df = pd.DataFrame(rows, columns=["event_time", "source", "message", "row_data"])
    return df


col1, col2, col3, col4 = st.columns(4)
users_df = get_users_df()
audit_df = get_audit_log()
errors_df = get_errors_df()

col1.metric("Users Created", int((audit_df["action"] == "create_user").sum()))
col2.metric("Emails Sent", int((audit_df["action"] == "email_sent").sum()))
col3.metric("Errors", int(len(errors_df)))
if not audit_df.empty:
    last_time = audit_df["event_time"].max()
    col4.metric("Last processed", last_time)
else:
    col4.metric("Last processed", "—")

st.success(f"{len(users_df)} accounts created", icon="✅")

st.subheader("Created Users")
st.dataframe(
    users_df[["created_at", "username", "name", "department", "role", "status", "email"]].sort_values(
        by="created_at", ascending=False
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Recent Activity")
st.dataframe(audit_df, use_container_width=True, hide_index=True)

st.subheader("Error Log")
st.dataframe(errors_df, use_container_width=True, hide_index=True)



