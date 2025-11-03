"""
Error codes and custom exception classes for immich-gpx-linker.

Defines application exit codes and exception hierarchy for proper error handling
and reporting throughout the codebase. Each exception maps to a specific error code
for consistent CLI exit status reporting.

Error code mapping (for CLI exit codes):
    0 - Success
    1 - Configuration error (invalid arguments, missing credentials)
    2 - File not found (GPX file doesn't exist)
    3 - Parse error (invalid GPX/JSON format)
    4 - Connection error (server unreachable)
    5 - Authentication error (invalid API key)
    6 - Matching error (GPS matching algorithm failure)
    7 - Update error (photo update failure)
    99 - Unknown error

Classes:
    ErrorCodes: Constant definitions and helper methods for exit codes
    ImmichGPXLinkerError: Base exception class (all others inherit from this)
    [Specific exceptions for different error conditions]
    
Usage:
    >>> try:
    ...     do_something()
    ... except ConfigurationError as e:
    ...     print(f"Error: {e.message}")
    ...     sys.exit(e.error_code)
"""


class ErrorCodes:
    """
    Standard application exit codes for different error conditions.
    
    Used to report error status to the operating system and caller.
    Success returns 0, various errors return 1-99.
    
    Attributes:
        SUCCESS (int): Operation completed successfully (0)
        CONFIG_ERROR (int): Configuration validation failed (1)
        FILE_NOT_FOUND (int): Required file not found (2)
        PARSE_ERROR (int): Format parsing failed (3)
        CONNECTION_ERROR (int): Server connection failed (4)
        AUTH_ERROR (int): Authentication failed (5)
        MATCH_ERROR (int): GPS matching failed (6)
        UPDATE_ERROR (int): Photo update failed (7)
        UNKNOWN_ERROR (int): Unknown error occurred (99)
        
    Example:
        >>> sys.exit(ErrorCodes.CONFIG_ERROR)  # Exit with code 1
    """
    SUCCESS = 0
    CONFIG_ERROR = 1
    FILE_NOT_FOUND = 2
    PARSE_ERROR = 3
    CONNECTION_ERROR = 4
    AUTH_ERROR = 5
    MATCH_ERROR = 6
    UPDATE_ERROR = 7
    UNKNOWN_ERROR = 99
    
    @classmethod
    def get_description(cls, code: int) -> str:
        """
        Get human-readable description for an exit code.
        
        Args:
            code: Exit code number
            
        Returns:
            Description string for the error code
            
        Example:
            >>> ErrorCodes.get_description(ErrorCodes.CONFIG_ERROR)
            'Configuration error'
        """
        descriptions = {
            cls.SUCCESS: "Operation completed successfully",
            cls.CONFIG_ERROR: "Configuration error",
            cls.FILE_NOT_FOUND: "File not found",
            cls.PARSE_ERROR: "Parsing error",
            cls.CONNECTION_ERROR: "Connection error",
            cls.AUTH_ERROR: "Authentication error",
            cls.MATCH_ERROR: "Matching error",
            cls.UPDATE_ERROR: "Update error",
            cls.UNKNOWN_ERROR: "Unknown error"
        }
        return descriptions.get(code, "Unknown error code")


class ImmichGPXLinkerError(Exception):
    """
    Base exception class for all immich-gpx-linker errors.
    
    All specific exceptions inherit from this class, allowing for generic
    exception handling while maintaining specific error type information.
    Each exception instance carries an error code for CLI exit status reporting.
    
    Attributes:
        message (str): Human-readable error message
        error_code (int): Application exit code (see ErrorCodes)
        
    Example:
        >>> try:
        ...     raise ImmichGPXLinkerError("Something went wrong", ErrorCodes.UNKNOWN_ERROR)
        ... except ImmichGPXLinkerError as e:
        ...     print(f"Error code {e.error_code}: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        error_code: int = ErrorCodes.UNKNOWN_ERROR,
    ) -> None:
        """
        Initialize base error with message and error code.
        
        Args:
            message: Description of the error
            error_code: Application exit code (default: UNKNOWN_ERROR)
            
        Returns:
            None
        """
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ConfigurationError(ImmichGPXLinkerError):
    """
    Configuration validation or setup error.
    
    Raised when configuration parameters are invalid, missing, or cannot be applied.
    Examples: missing API key, invalid URL format, nonexistent file path.
    Exit code: 1
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and CONFIG_ERROR exit code."""
        super().__init__(message, ErrorCodes.CONFIG_ERROR)


class GPXValidationError(ImmichGPXLinkerError):
    """
    GPX file validation error.
    
    Raised when a required GPX file doesn't exist, is not readable, or fails
    basic validation checks (file format, encoding, etc.).
    Exit code: 2 (FILE_NOT_FOUND)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and FILE_NOT_FOUND exit code."""
        super().__init__(message, ErrorCodes.FILE_NOT_FOUND)


class GPXParsingError(ImmichGPXLinkerError):
    """
    GPX file format parsing error.
    
    Raised when GPX file cannot be parsed due to invalid XML, missing required
    fields, or corrupted data.
    Exit code: 3 (PARSE_ERROR)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and PARSE_ERROR exit code."""
        super().__init__(message, ErrorCodes.PARSE_ERROR)


class ConnectionError(ImmichGPXLinkerError):
    """
    Network or server connection error.
    
    Raised when connection to Immich server fails due to network issues,
    server being down, or DNS resolution failures.
    Exit code: 4 (CONNECTION_ERROR)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and CONNECTION_ERROR exit code."""
        super().__init__(message, ErrorCodes.CONNECTION_ERROR)


class AuthenticationError(ImmichGPXLinkerError):
    """
    API key authentication failure.
    
    Raised when API key is invalid, expired, or doesn't have required permissions
    for the requested operation.
    Exit code: 5 (AUTH_ERROR)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and AUTH_ERROR exit code."""
        super().__init__(message, ErrorCodes.AUTH_ERROR)


class MatchingError(ImmichGPXLinkerError):
    """
    GPS point to photo matching error.
    
    Raised when the photo-to-GPS matching algorithm encounters an error
    (e.g., invalid input data, algorithm failure).
    Exit code: 6 (MATCH_ERROR)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and MATCH_ERROR exit code."""
        super().__init__(message, ErrorCodes.MATCH_ERROR)


class UpdateError(ImmichGPXLinkerError):
    """
    Photo GPS coordinate update error.
    
    Raised when updating photo GPS coordinates in Immich fails
    (e.g., API error, permission denied, invalid photo ID).
    Exit code: 7 (UPDATE_ERROR)
    """
    
    def __init__(self, message: str) -> None:
        """Initialize with message and UPDATE_ERROR exit code."""
        super().__init__(message, ErrorCodes.UPDATE_ERROR)
