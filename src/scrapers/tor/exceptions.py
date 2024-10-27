class TorException(Exception):
    """Base exception for Tor-related errors"""
    pass

class TorConnectionError(TorException):
    """Raised when there's an error connecting to the Tor network"""
    pass

class TorInitializationError(TorException):
    """Raised when Tor service fails to initialize"""
    pass

class TorCircuitError(TorException):
    """Raised when there's an error creating or managing Tor circuits"""
    pass

class OnionServiceError(TorException):
    """Raised when there's an error accessing an onion service"""
    pass

class TorProxyError(TorException):
    """Raised when there's an error with the Tor SOCKS proxy"""
    pass