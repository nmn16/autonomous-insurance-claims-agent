"""Custom exceptions so the API can map each failure to an HTTP status."""


class ClaimProcessingError(Exception):
    """Base class for all claim-processing errors."""


class UnsupportedFileTypeError(ClaimProcessingError):
    """The uploaded file is not a PDF or TXT file."""


class EmptyDocumentError(ClaimProcessingError):
    """The file is empty or contains no readable text."""


class InvalidPdfError(ClaimProcessingError):
    """The PDF is corrupted, encrypted, or not a PDF at all."""


class ExtractionError(ClaimProcessingError):
    """No recognisable FNOL fields could be extracted from the text."""
