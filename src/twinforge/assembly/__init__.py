"""Evidence-driven assembly of higher-level automation assets."""

from .software_devices import (
    AssembledSoftwareDevice,
    DeviceAssemblyProvider,
    PowerFlex525AssemblyProvider,
    assemble_corpus_devices,
)
from .promotion_repository import (
    InMemoryPromotionRepository,
    PromotionPersistenceItem,
    PromotionPersistenceResult,
    PromotionPersistenceStatus,
    PromotionRepository,
    PromotionRepositoryError,
    persist_promotions,
)

__all__ = [
    "AssembledSoftwareDevice",
    "DeviceAssemblyProvider",
    "InMemoryPromotionRepository",
    "PowerFlex525AssemblyProvider",
    "PromotionPersistenceItem",
    "PromotionPersistenceResult",
    "PromotionPersistenceStatus",
    "PromotionRepository",
    "PromotionRepositoryError",
    "assemble_corpus_devices",
    "persist_promotions",
]
