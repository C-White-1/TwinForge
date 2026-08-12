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
from .cross_layer_device_correlation import (
    CorrelatedSoftwareDevice,
    CrossLayerCorrelationError,
    CrossLayerDeviceCorrelationResult,
    correlate_software_devices_with_routed_modules,
    cross_layer_device_correlation_data,
    cross_layer_device_correlation_json,
)
from .gateway_descriptions import (
    GatewayDescriptionAssemblyResult,
    assemble_gateway_descriptions,
)
from .gateway_mappings import (
    GatewayMappingApplicationResult,
    apply_gateway_mapping_document,
)
from .network_graph import (
    AcceptedNetworkGraph,
    NetworkGraphLink,
    NetworkGraphLoweringError,
    NetworkGraphNode,
    NetworkInterfaceEvidence,
    accepted_network_graph_data,
    accepted_network_graph_json,
    lower_accepted_network_graph,
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
from .plx50_gateway_configuration import (
    Plx50GatewayConfigurationResult,
    apply_plx50_gateway_configuration,
)
from .sqlite_promotion_repository import SqlitePromotionRepository

__all__ = [
    "AssembledSoftwareDevice",
    "AcceptedNetworkGraph",
    "ConfiguredMessageEvidence",
    "ControllerCommunicationBinding",
    "ControllerCommunicationEdge",
    "ControllerCommunicationGraph",
    "ControllerCommunicationGraphError",
    "ControllerCommunicationNode",
    "CorrelatedSoftwareDevice",
    "CrossLayerCorrelationError",
    "CrossLayerDeviceCorrelationResult",
    "DeviceAssemblyProvider",
    "GatewayDescriptionAssemblyResult",
    "GatewayMappingApplicationResult",
    "InMemoryPromotionRepository",
    "NetworkGraphLink",
    "NetworkGraphLoweringError",
    "NetworkGraphNode",
    "NetworkInterfaceEvidence",
    "PowerFlex525AssemblyProvider",
    "Plx50GatewayConfigurationResult",
    "PromotionPersistenceItem",
    "PromotionPersistenceResult",
    "PromotionPersistenceStatus",
    "PromotionRepository",
    "PromotionRepositoryError",
    "SqlitePromotionRepository",
    "assemble_corpus_devices",
    "assemble_gateway_descriptions",
    "apply_gateway_mapping_document",
    "apply_plx50_gateway_configuration",
    "accepted_network_graph_data",
    "accepted_network_graph_json",
    "build_controller_communication_graph",
    "controller_communication_graph_data",
    "controller_communication_graph_json",
    "correlate_software_devices_with_routed_modules",
    "cross_layer_device_correlation_data",
    "cross_layer_device_correlation_json",
    "lower_accepted_network_graph",
    "persist_promotions",
]
