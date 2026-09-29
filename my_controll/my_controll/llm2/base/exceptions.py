class NotStartedError(Exception):
    def __init__(self, source):
        msg = (
            f"'{source}' is not started, and a run was requested."
        )
        super().__init__(msg)
        

class IncorrectConfigurationError(Exception):
    def __init__(
            self, 
            source, 
            correct_config,
            passed_config
    ):
        msg = (
            f"Invalid config type for '{source}'. "
            f"Expected '{correct_config}', got '{passed_config}'."
        )
        super().__init__(msg)
