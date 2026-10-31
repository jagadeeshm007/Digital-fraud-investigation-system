from app.exceptions import PermissionDenied

PERMISSION_MATRIX: dict[str, dict[str, bool]] = {
    "analyst": {
        "upload_file": True,
        "run_detection": False,
        "view_alerts": True,
        "view_cases": True,
        "record_case_decision": False,
        "escalate_case": False,
        "change_rule": False,
        "reveal_pii": False,
        "view_audit": True,
        "view_ai_log": True,
        "add_case_note": False,
        "approve_recommendation": False,
    },
    "investigator": {
        "upload_file": True,
        "run_detection": True,
        "view_alerts": True,
        "view_cases": True,
        "record_case_decision": True,
        "escalate_case": True,
        "change_rule": False,
        "reveal_pii": False,
        "view_audit": True,
        "view_ai_log": True,
        "add_case_note": True,
        "approve_recommendation": False,
    },
    "supervisor": {
        "upload_file": True,
        "run_detection": True,
        "view_alerts": True,
        "view_cases": True,
        "record_case_decision": True,
        "escalate_case": True,
        "change_rule": True,
        "reveal_pii": True,
        "view_audit": True,
        "view_ai_log": True,
        "add_case_note": True,
        "approve_recommendation": True,
    },
}


def resolve_role(x_role: str | None) -> str:
    if x_role and x_role.lower() in PERMISSION_MATRIX:
        return x_role.lower()
    return "analyst"


def resolve_user(x_user: str | None, role: str) -> str:
    """Who is acting (X-User). Maker-checker compares this, so the default is per role."""
    name = (x_user or "").strip()[:64]
    return name or f"{role}-1"


def check_permission(role: str, action: str) -> None:
    if not PERMISSION_MATRIX.get(role, PERMISSION_MATRIX["analyst"]).get(action, False):
        raise PermissionDenied(role, action)
