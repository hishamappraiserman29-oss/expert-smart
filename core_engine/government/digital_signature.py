"""
digital_signature.py — Digital Signature Manager

PKI-ready document signing for government-official property valuations.
Uses HMAC-SHA256 for signing; designed to accept RSA keys when available.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SignatureAlgorithm(str, Enum):
    HMAC_SHA256 = "hmac_sha256"    # Symmetric — for internal signing
    SHA256_HASH = "sha256_hash"    # Hash-only — tamper detection without key


@dataclass
class SignedDocument:
    """A government document with its integrity signature."""

    document_id: str
    document_type: str
    content_hash: str
    signature: str
    algorithm: SignatureAlgorithm
    signer_id: str
    signed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "content_hash": self.content_hash,
            "signature": self.signature,
            "algorithm": self.algorithm.value,
            "signer_id": self.signer_id,
            "signed_at": self.signed_at.isoformat(),
            "metadata": self.metadata,
        }


def _get_signing_key() -> str:
    key = os.environ.get("GOVT_SIGNING_KEY", "").strip()
    if not key:
        raise ValueError(
            "GOVT_SIGNING_KEY environment variable is required. "
            "Production deployments must set a strong random key. "
            "Test environments must set it via monkeypatch."
        )
    return key


class DigitalSignatureManager:
    """Sign and verify government documents using HMAC-SHA256."""

    def __init__(self) -> None:
        self._secret = _get_signing_key().encode("utf-8")

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_signature(self, content_hash: str, document_id: str) -> str:
        payload = f"{document_id}:{content_hash}"
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign_document(
        self,
        content: str,
        document_type: str,
        signer_id: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256,
    ) -> SignedDocument:
        """Sign a document and return a SignedDocument record.

        Args:
            content: Plain-text or JSON content to sign.
            document_type: e.g. "cbe_101", "tax_50", "egfsa_30".
            signer_id: Identity of the signing authority.
            metadata: Optional additional metadata to embed.
            algorithm: Signing algorithm to use.

        Returns:
            SignedDocument dataclass.
        """
        document_id = str(uuid.uuid4())
        content_hash = self._compute_hash(content)

        if algorithm == SignatureAlgorithm.HMAC_SHA256:
            signature = self._compute_signature(content_hash, document_id)
        else:
            signature = content_hash  # SHA256_HASH — hash is the "signature"

        doc = SignedDocument(
            document_id=document_id,
            document_type=document_type,
            content_hash=content_hash,
            signature=signature,
            algorithm=algorithm,
            signer_id=signer_id,
            signed_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        logger.info(
            "Document signed: %s (%s) by %s via %s",
            document_id, document_type, signer_id, algorithm.value,
        )
        return doc

    def verify_document(self, content: str, signed_doc: SignedDocument) -> bool:
        """Verify that content matches the signed document.

        Returns True if the content is intact and the signature is valid.
        """
        current_hash = self._compute_hash(content)
        if current_hash != signed_doc.content_hash:
            return False

        if signed_doc.algorithm == SignatureAlgorithm.HMAC_SHA256:
            expected_sig = self._compute_signature(current_hash, signed_doc.document_id)
            return hmac.compare_digest(expected_sig, signed_doc.signature)

        # SHA256_HASH — signature IS the hash
        return signed_doc.signature == current_hash

    def sign_valuation_report(
        self,
        report_data: Dict[str, Any],
        signer_id: str = "system",
    ) -> SignedDocument:
        """Convenience wrapper: sign a valuation report dict."""
        content = json.dumps(report_data, sort_keys=True, default=str)
        return self.sign_document(
            content,
            document_type="valuation_report",
            signer_id=signer_id,
            metadata={"property_id": report_data.get("property_id", "")},
        )


