"""
Models package for document extraction.

This package contains Pydantic models that define the structure of documents
to be extracted and the registry for managing them.
"""

from .model_registry import (
    register_model,
    get_model,
    get_all_models,
    discover_models,
    get_model_for_document_type,
    get_model_from_content,
)

# Import specific models to ensure they're loaded
from .invoice import Invoice
from .vehicle_insurance_policy import VehicleInsurancePolicy

# Auto-discover and register all models in this package
discover_models()
