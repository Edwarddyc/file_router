from enum import StrEnum


class BatchStatus(StrEnum):
    RECEIVING = "receiving"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class FileStatus(StrEnum):
    REGISTERED = "registered"
    FAILED = "failed"


class IntegrityStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    CORRUPT = "corrupt"


class SourceKind(StrEnum):
    USER_UPLOAD = "user-upload"
    SYSTEM_IMPORT = "system-import"
    WATCHER = "watcher"

