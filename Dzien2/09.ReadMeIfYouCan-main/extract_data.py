"""
Main script for document processing using the generic document processor.

This script uses the generic document processor to process documents
of any registered model type.
"""

import os
import logging
import argparse
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient

from document_processor import DocumentProcessor
from models import get_model, get_model_for_document_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("document_extraction.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# Configuration class
class Config:
    """Configuration class to centralize all settings."""

    def __init__(self):
        # Required Azure endpoints
        self.openai_endpoint = os.getenv("OPENAI_ENDPOINT")
        if not self.openai_endpoint:
            raise ValueError("OPENAI_ENDPOINT environment variable is not set")

        self.ai_services_endpoint = os.getenv("AI_SERVICES_ENDPOINT")
        if not self.ai_services_endpoint:
            raise ValueError("AI_SERVICES_ENDPOINT environment variable is not set")

        self.gpt4o_model_deployment_name = os.getenv("GPT4O_MODEL_DEPLOYMENT_NAME")
        if not self.gpt4o_model_deployment_name:
            raise ValueError(
                "GPT4O_MODEL_DEPLOYMENT_NAME environment variable is not set"
            )

        # Optional settings with defaults
        self.output_folder = os.getenv("OUTPUT_FOLDER", "./output")
        self.visualizations_folder = os.path.join(self.output_folder, "visualizations")
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Set up folder structure
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.visualizations_folder, exist_ok=True)

        # Adjust log level if specified
        numeric_level = getattr(logging, self.log_level.upper(), None)
        if isinstance(numeric_level, int):
            logger.setLevel(numeric_level)


def initialize_clients(config):
    """Initialize and return Azure clients with proper authentication."""
    try:
        # Use DefaultAzureCredential for authentication
        credential = DefaultAzureCredential()

        # Set up token provider for OpenAI
        openai_token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )

        # Initialize OpenAI client
        openai_client = AzureOpenAI(
            azure_endpoint=config.openai_endpoint,
            azure_ad_token_provider=openai_token_provider,
            api_version="2025-04-01-preview",  # Requires the latest API version for structured outputs
        )

        # Initialize Document Intelligence client
        doc_intel_client = DocumentIntelligenceClient(
            endpoint=config.ai_services_endpoint, credential=credential
        )

        logger.info("Azure clients initialized successfully")
        return openai_client, doc_intel_client

    except Exception as e:
        logger.error("Failed to initialize Azure clients: %s", str(e))
        raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Extract data from documents")
    parser.add_argument("--file", "-f", help="Path to the document file")
    parser.add_argument(
        "--model",
        "-m",
        help="Model type to use (e.g., Invoice, VehicleInsurancePolicy)",
    )
    parser.add_argument("--output", "-o", help="Output folder for extracted data")
    args = parser.parse_args()

    try:
        # Initialize configuration
        config = Config()

        # Override output folder if specified
        if args.output:
            config.output_folder = args.output
            config.visualizations_folder = os.path.join(
                config.output_folder, "visualizations"
            )
            os.makedirs(config.output_folder, exist_ok=True)
            os.makedirs(config.visualizations_folder, exist_ok=True)

        # Initialize clients
        openai_client, doc_intel_client = initialize_clients(config)

        # Create document processor
        processor = DocumentProcessor(
            openai_client=openai_client,
            doc_intel_client=doc_intel_client,
            config={
                "gpt4o_model_deployment_name": config.gpt4o_model_deployment_name,
                "max_workers": config.max_workers,
                "visualizations_folder": config.visualizations_folder,
            },
        )

        # Get model class if specified
        model_class = None
        if args.model:
            model_class = get_model(args.model)
            if not model_class:
                logger.warning("Model '%s' not found in registry", args.model)

        # Use default file if none provided
        file_path = args.file
        if file_path is None:
            file_path = "./assets/invoices/invoice_5.pdf"
            logger.info("Using default file path: %s", file_path)

        # Process document
        results = processor.process_document(file_path, model_class)

        # Save results
        processor.save_results(results, config.output_folder)

        # Print summary
        logger.info("Processing completed successfully")
        document = results["document"]
        if hasattr(document, "invoice_id"):
            logger.info("Invoice Number: %s", document.invoice_id or "N/A")
        elif hasattr(document, "policy_number"):
            logger.info("Policy Number: %s", document.policy_number or "N/A")
        logger.info("Document Type: %s", results["model_type"])
        logger.info("Confidence score: %.2f", results["confidence"].get("_overall", 0))
        logger.info("Processing time: %dms", results["performance"]["total_ms"])

        return results

    except Exception as e:
        logger.error("Error in main function: %s", str(e))
        raise


if __name__ == "__main__":
    main()
