"""Evidence-driven assembly of higher-level automation assets."""

from .controller_communication_graph import (
    ConfiguredMessageEvidence,
    ControllerCommunicationBinding,
    ControllerCommunicationEdge,
    ControllerCommunicationGraph,
    ControllerCommunicationGraphError,
    ControllerCommunicationNode,
    build_controller_communication_graph,
    controller_communication_graph_data,
    controller_communication_graph_json,
)
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
    "ConfiguredMessageEvidence",
    "ControllerCommunicationBinding",
    "ControllerCommunicationEdge",
    "ControllerCommunicationGraph",
    "ControllerCommunicationGraphError",
    "ControllerCommunicationNode",
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
    "build_controller_communication_graph",
    "controller_communication_graph_data",
    "controller_communication_graph_json",
    "persist_promotions",
]
