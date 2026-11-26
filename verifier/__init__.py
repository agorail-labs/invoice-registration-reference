"""Public Python API for offline invoice-registration evidence verification."""

from .invoice_reference_verifier import VerifierConfig, verify

__all__ = ["VerifierConfig", "verify"]
