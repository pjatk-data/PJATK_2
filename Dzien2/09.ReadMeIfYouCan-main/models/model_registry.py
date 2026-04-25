"""
Model Registry to dynamically load and register all document models.

This module provides a registry for document models that can be used to dynamically
load and access all available document models in the system.
"""

import inspect
import importlib
import os
import sys
import logging
from typing import Dict, Type, Optional, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModelRegistry:
    """A registry for document models used in document extraction."""

    def __init__(self):
        self._models: Dict[str, Type[BaseModel]] = {}

    def register_model(self, model_name: str, model_class: Type[BaseModel]) -> None:
        """
        Register a model class with the registry.

        Args:
            model_name: The name to register the model under
            model_class: The model class to register
        """
        if not issubclass(model_class, BaseModel):
            raise TypeError(
                f"Model class {model_class.__name__} must be a subclass of pydantic.BaseModel"
            )

        self._models[model_name] = model_class
        logger.info(f"Registered model '{model_name}'")

    def get_model(self, model_name: str) -> Optional[Type[BaseModel]]:
        """
        Get a model class by name.

        Args:
            model_name: The name of the model to get

        Returns:
            The model class if found, None otherwise
        """
        return self._models.get(model_name)

    def get_all_models(self) -> Dict[str, Type[BaseModel]]:
        """
        Get all registered models.

        Returns:
            A dictionary mapping model names to model classes
        """
        return self._models.copy()

    def discover_models(self, package_path: str = None) -> None:
        """
        Automatically discover and register all model classes in the given package.

        Args:
            package_path: The path to the package to search for models in.
                          If None, uses the 'models' directory relative to this file.
        """
        if package_path is None:
            # Default to the models directory (current directory containing this file)
            package_path = os.path.dirname(os.path.abspath(__file__))

        # Get the package name
        package_name = os.path.basename(package_path)
        if package_name not in sys.modules:
            logger.error(f"Package {package_name} not found in sys.modules")
            return

        # Get all Python files in the package
        for file_name in os.listdir(package_path):
            if (
                not file_name.endswith(".py")
                or file_name == "__init__.py"
                or file_name == "model_registry.py"
            ):
                continue

            module_name = f"{package_name}.{file_name[:-3]}"  # Remove .py extension

            try:
                # Import the module
                module = importlib.import_module(module_name)

                # Find all pydantic model classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseModel) and obj.__module__ == module.__name__:
                        # Register the model with its class name
                        self.register_model(name, obj)

            except ImportError as e:
                logger.error(f"Error importing module {module_name}: {e}")

    def get_model_for_document_type(
        self, document_type: str
    ) -> Optional[Type[BaseModel]]:
        """
        Get a model class based on the document type.

        Args:
            document_type: A string describing the document type (e.g., 'invoice', 'policy')

        Returns:
            The appropriate model class if found, None otherwise
        """
        document_type_lower = document_type.lower()

        # Direct match
        if document_type_lower in self._models:
            return self._models[document_type_lower]

        # Try to find a model that contains the document type in its name
        for name, model in self._models.items():
            if document_type_lower in name.lower():
                return model

        # If no match found
        return None

    def get_model_from_content(
        self, content: Dict[str, Any]
    ) -> Optional[Type[BaseModel]]:
        """
        Attempt to determine the appropriate model based on document content.

        This is a heuristic approach and may not be 100% accurate.

        Args:
            content: A dictionary of document content extracted from a document

        Returns:
            The best matching model class if found, None otherwise
        """
        # Score each model based on field matches
        scores = {}

        for name, model in self._models.items():
            score = 0
            model_fields = model.__annotations__.keys()

            # Count how many model fields appear in the content
            for field in model_fields:
                if field in content:
                    score += 1

            scores[name] = score

        # Return the model with the highest score, if any
        if scores:
            best_match = max(scores.items(), key=lambda x: x[1])
            if best_match[1] > 0:  # Ensure we have at least one field match
                return self._models[best_match[0]]

        return None


# Create a singleton instance
_registry = ModelRegistry()

# Export convenience functions
register_model = _registry.register_model
get_model = _registry.get_model
get_all_models = _registry.get_all_models
discover_models = _registry.discover_models
get_model_for_document_type = _registry.get_model_for_document_type
get_model_from_content = _registry.get_model_from_content
