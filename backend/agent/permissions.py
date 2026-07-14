from enum import Enum
from typing import Dict, Any

class PermissionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    FILESYSTEM = "FILESYSTEM"

class PermissionManager:
    # Set default values for whether a permission requires user confirmation before run
    CONFIRMATION_RULES: Dict[PermissionType, bool] = {
        PermissionType.READ: False,
        PermissionType.WRITE: True,
        PermissionType.EXECUTE: True,
        PermissionType.NETWORK: False,
        PermissionType.FILESYSTEM: False # Base reading is permitted, writing/executing triggers confirmation via WRITE/EXECUTE
    }

    @classmethod
    def requires_confirmation(cls, permission: PermissionType) -> bool:
        return cls.CONFIRMATION_RULES.get(permission, False)
