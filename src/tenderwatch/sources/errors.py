class RawSourceError(Exception):
    pass


class ArtifactReadError(RawSourceError):
    pass


class IntegrityError(RawSourceError):
    pass


class SourceFormatError(RawSourceError):
    pass


class UnsupportedFormatError(SourceFormatError):
    pass


class LocatorError(RawSourceError):
    pass
