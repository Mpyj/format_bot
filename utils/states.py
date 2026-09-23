from typing import Any

_user_states: dict[int, dict[str, Any]] = {}

def set_state(user_id: int, **kwargs):
    _user_states.setdefault(user_id, {}).update(kwargs)

def get_state(user_id: int) -> dict[str, Any]:
    return _user_states.get(user_id, {})

def clear_state(user_id: int):
    _user_states.pop(user_id, None)