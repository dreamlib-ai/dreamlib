class ApiError(Exception):
    """An error the client sees as {"error": message} with this status."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class NotFound(Exception):
    """A dream that does not exist for this user."""


class Conflict(Exception):
    """A dream that changed while it was being edited."""
