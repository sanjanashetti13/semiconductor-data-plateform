"""Generic SQL Agent package — planning-based architecture with DB profiling."""

from ai.sql_agent.agent import ask_sql_agent
from ai.sql_agent.intent import QuestionIntent, classify_intent
from ai.sql_agent.planner import QuestionCategory, classify_question
from ai.sql_agent.profiler import (
    DatabaseProfile,
    build_database_profile,
    ensure_profile,
    get_profile,
    set_profile,
)
from ai.sql_agent.response_mode import ResponseMode, classify_response_mode
from ai.sql_agent.session_store import (
    SqlConnectionConfig,
    create_session,
    delete_session,
    get_schema,
    get_session,
    inspect_schema,
    set_schema,
    test_connection,
)

__all__ = [
    "DatabaseProfile",
    "QuestionCategory",
    "QuestionIntent",
    "ResponseMode",
    "SqlConnectionConfig",
    "ask_sql_agent",
    "build_database_profile",
    "classify_intent",
    "classify_question",
    "classify_response_mode",
    "create_session",
    "delete_session",
    "ensure_profile",
    "get_profile",
    "get_schema",
    "get_session",
    "inspect_schema",
    "set_profile",
    "set_schema",
    "test_connection",
]
