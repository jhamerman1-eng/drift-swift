#!/usr/bin/env python3
"""
Drift API Error Classifications
Provides proper error taxonomy for Swift API and DriftPy operations
"""

class DriftError(Exception):
    """Base exception for all Drift-related errors"""
    pass

class TransientError(DriftError):
    """Errors that should be retried (network, rate limits, temporary failures)"""
    pass

class ValidationError(DriftError):
    """Errors that should NOT be retried (bad payload, auth, etc.)"""
    pass

class SwiftAPIError(DriftError):
    """Swift-specific API errors"""
    pass

class SigVerificationFailed(ValidationError):
    """Swift signature verification failed"""
    pass

class InvalidSwiftOrderParam(ValidationError):
    """Swift order parameters are invalid"""
    pass

class MarketIndexMismatch(ValidationError):
    """Market index doesn't match expected value"""
    pass

class SwiftTimeoutError(TransientError):
    """Swift API request timed out"""
    pass

class SwiftRateLimitError(TransientError):
    """Swift API rate limit exceeded (429)"""
    pass

class SwiftServerError(TransientError):
    """Swift API server error (5xx)"""
    pass

class SwiftNetworkError(TransientError):
    """Network connectivity issues with Swift API"""
    pass

def classify_swift_error(status_code: int, response_text: str = "") -> DriftError:
    """Classify Swift API errors into appropriate exception types"""
    
    if status_code == 400:
        if "signature" in response_text.lower():
            return SigVerificationFailed(f"Swift signature verification failed: {response_text}")
        elif "market" in response_text.lower():
            return MarketIndexMismatch(f"Market index mismatch: {response_text}")
        else:
            return InvalidSwiftOrderParam(f"Invalid Swift order parameters: {response_text}")
    
    elif status_code == 401:
        return ValidationError(f"Swift authentication failed: {response_text}")
    
    elif status_code == 422:
        return ValidationError(f"Swift unprocessable entity: {response_text}")
    
    elif status_code == 429:
        return SwiftRateLimitError(f"Swift rate limit exceeded: {response_text}")
    
    elif status_code == 408:
        return SwiftTimeoutError(f"Swift request timeout: {response_text}")
    
    elif 500 <= status_code <= 599:
        return SwiftServerError(f"Swift server error {status_code}: {response_text}")
    
    else:
        return SwiftAPIError(f"Swift API error {status_code}: {response_text}")
