"""Read-only provider metadata clients."""

from chakra_vault.providers.huggingface import (
    HuggingFaceMetadataClient,
    HuggingFaceMetadataError,
)

__all__ = [
    "HuggingFaceMetadataClient",
    "HuggingFaceMetadataError",
]
