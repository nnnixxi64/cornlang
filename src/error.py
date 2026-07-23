from typing import Optional


class CornError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None):
        self.line: Optional[int] = line
        self.col: Optional[int] = col
        super().__init__(message)
