from enum import Enum


class NotificationType(str, Enum):
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"
    REVIEW = "REVIEW"
    SELLER = "SELLER"
    SYSTEM = "SYSTEM"
    LOGISTICS = "LOGISTICS"
