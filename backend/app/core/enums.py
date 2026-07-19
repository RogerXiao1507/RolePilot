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
