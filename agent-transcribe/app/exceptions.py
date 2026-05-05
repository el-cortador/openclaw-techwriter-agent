from __future__ import annotations


class TranscribeError(Exception):
    pass


class FileValidationError(TranscribeError):
    pass


class ConversionError(TranscribeError):
    pass


class TranscriptionError(TranscribeError):
    pass


class PostprocessError(TranscribeError):
    pass
