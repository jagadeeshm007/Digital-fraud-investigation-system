class PermissionDenied(Exception):
    def __init__(self, role: str, action: str):
        self.role = role
        self.action = action
        super().__init__(f"Role '{role}' cannot perform '{action}'")


class IngestionError(Exception):
    def __init__(self, code: str, detail: str, field: str = ""):
        self.code = code
        self.detail = detail
        self.field = field or detail.split(":")[0].strip()
        super().__init__(detail)
