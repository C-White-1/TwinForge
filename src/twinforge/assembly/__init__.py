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
from .sqlite_promotion_repository import SqlitePromotionRepository

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
    "SqlitePromotionRepository",
    "assemble_corpus_devices",
    "persist_promotions",
]
