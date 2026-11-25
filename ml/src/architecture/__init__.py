"""
ADIP Architecture Intelligence Package (Phase 6)
Lead Deliverable — Anshika (AI/ML & Data Intelligence Lead)

Exports architecture schemas, NetworkX graph feature extractor,
and ML-compatible architecture representation engine.
"""

from ml.src.architecture.schemas import (
    ArchitecturePattern,
    ArchitectureStyle,
    ApiStyle,
    DeploymentType,
    CloudProvider,
    ComponentCategory,
    ComponentType,
    ArchitectureComponent,
    ArchitectureDependency,
    ArchitectureGraph,
)
from ml.src.architecture.graph_extractor import ArchitectureGraphExtractor
from ml.src.architecture.representation import MLArchitectureRepresentation

__all__ = [
    "ArchitecturePattern",
    "ArchitectureStyle",
    "ApiStyle",
    "DeploymentType",
    "CloudProvider",
    "ComponentCategory",
    "ComponentType",
    "ArchitectureComponent",
    "ArchitectureDependency",
    "ArchitectureGraph",
    "ArchitectureGraphExtractor",
    "MLArchitectureRepresentation",
]
