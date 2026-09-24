class NormalizationError(ValueError):
    def __init__(self, reason: str, raw_source_record_id: str, projection_locator: str = '$') -> None:
        self.reason = reason
        self.raw_source_record_id = raw_source_record_id
        self.projection_locator = projection_locator
        super().__init__(f'{reason}: {raw_source_record_id} ({projection_locator})')


class InvalidNormalizationInput(NormalizationError):
    pass


class UnsupportedNormalizationInput(NormalizationError):
    pass


class NormalizationInvariantError(RuntimeError):
    pass
