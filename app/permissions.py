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
    },
}


def resolve_role(x_role: str | None) -> str:
    if x_role and x_role.lower() in PERMISSION_MATRIX:
        return x_role.lower()
    return "analyst"


def check_permission(role: str, action: str) -> None:
    if not PERMISSION_MATRIX.get(role, PERMISSION_MATRIX["analyst"]).get(action, False):
        raise PermissionDenied(role, action)
