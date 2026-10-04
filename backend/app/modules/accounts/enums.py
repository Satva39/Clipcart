from enum import Enum

class UserRole(Enum):
    ADMIN = "ADMIN"
    SUPPLIER = "SUPPLIER"
    CUSTOMER = "CUSTOMER"
    LOGISTICS_MANAGER = "LOGISTICS_MANAGER"


class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"