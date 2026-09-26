class DomainError(Exception):
    code = "domain-error"
    status_code = 400
    title = "Domain error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidRequestError(DomainError):
    code = "invalid-request"
    status_code = 422
    title = "Invalid request"


class MissingIdempotencyKeyError(DomainError):
    code = "missing-idempotency-key"
    status_code = 400
    title = "Missing idempotency key"


class IdempotencyConflictError(DomainError):
    code = "idempotency-conflict"
    status_code = 409
    title = "Idempotency key conflict"


class TooManyFilesError(DomainError):
    code = "too-many-files"
    status_code = 413
    title = "Too many files"


class FileTooLargeError(DomainError):
    code = "file-too-large"
    status_code = 413
    title = "File exceeds configured size limit"


class BatchTooLargeError(DomainError):
    code = "batch-too-large"
    status_code = 413
    title = "Batch exceeds configured size limit"


class UnsupportedExtensionError(DomainError):
    code = "unsupported-extension"
    status_code = 415
    title = "Unsupported file extension"


class EmptyFileError(DomainError):
    code = "empty-file"
    status_code = 422
    title = "Empty file"


class IntegrityConflictError(DomainError):
    code = "integrity-conflict"
    status_code = 409
    title = "Stored file integrity conflict"


class BatchNotFoundError(DomainError):
    code = "batch-not-found"
    status_code = 404
    title = "Batch not found"


class FileNotFoundError(DomainError):
    code = "file-not-found"
    status_code = 404
    title = "File not found"

