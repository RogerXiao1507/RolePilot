from enum import Enum


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


class EvidenceIngestionStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class JobRecency(str, Enum):
    DAY = "24h"
    WEEK = "7d"
    TWO_WEEKS = "14d"
    MONTH = "30d"
    ALL = "all"


class JobSort(str, Enum):
    RECOMMENDED = "recommended"
    NEWEST = "newest"
    MOST_RELEVANT = "most_relevant"


class NotificationFrequency(str, Enum):
    OFF = "off"
    DAILY = "daily"
    WEEKLY = "weekly"


class DiscoveryActionState(str, Enum):
    SAVED = "saved"
    DISMISSED = "dismissed"
    DUPLICATE = "duplicate"
    CONVERTED = "converted"
