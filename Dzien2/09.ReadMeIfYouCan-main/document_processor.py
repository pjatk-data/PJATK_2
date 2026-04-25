"""
Generic document processor that can adapt to any document model type.

This module provides a generic document processor that can process documents
using any model type registered in the model registry.
"""

import io
import json
import os
import base64
import logging
from typing import Dict, Any, Type, Optional, Union, List
from concurrent.futures import ThreadPoolExecutor
import importlib
from datetime import datetime
from dateutil import parser as date_parser

from pydantic import BaseModel
from PIL import Image

try:
    from pdf2image import convert_from_bytes
    from pdf2image.exceptions import PDFInfoNotInstalledError
except ImportError:  # pragma: no cover
    convert_from_bytes = None

    class PDFInfoNotInstalledError(Exception):
        pass


from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from models.model_registry import (
    get_model,
    get_model_for_document_type,
    get_model_from_content,
)
from confidence.document_intelligence_confidence import (
    evaluate_confidence as evaluate_di_confidence,
)
from confidence.openai_confidence import (
    evaluate_confidence as evaluate_openai_confidence,
)
from confidence.confidence_utils import merge_confidence_values
from utils.custom_json_encoder import CustomJSONEncoder
from utils.stopwatch import Stopwatch
from utils.visualization import visualize_all_field_polygons

# Configure logging
logger = logging.getLogger(__name__)


def _render_pdf_to_images(document_bytes: bytes, dpi: int = 200) -> List[Image.Image]:
    """Render a PDF (bytes) into a list of PIL Images.

    Prefers `pdf2image` (Poppler) when available. Falls back to `pypdfium2`
    to avoid requiring external Poppler binaries (notably on Windows ARM64).
    """

    if convert_from_bytes is not None:
        try:
            return convert_from_bytes(document_bytes, dpi=dpi)
        except (PDFInfoNotInstalledError, FileNotFoundError, OSError) as exc:
            logger.warning(
                "pdf2image/Poppler unavailable (%s). Falling back to pypdfium2.",
                str(exc),
            )

    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PDF rendering failed. Install Poppler (for pdf2image) or install 'pypdfium2' to render PDFs without system dependencies."
        ) from exc

    pdf = pdfium.PdfDocument(document_bytes)
    images: List[Image.Image] = []
    scale = dpi / 72.0
    try:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            try:
                bitmap = page.render(scale=scale)
                images.append(bitmap.to_pil())
            finally:
                # pypdfium2 pages hold native resources
                try:
                    page.close()
                except Exception:
                    pass
    finally:
        try:
            pdf.close()
        except Exception:
            pass

    return images


def encode_page(page):
    """
    Encode a PIL Image to base64 for OpenAI API.

    Args:
        page: A PIL Image object

    Returns:
        dict: A dictionary with the encoded image in the format required by OpenAI API
    """
    try:
        byte_io = io.BytesIO()
        page.save(byte_io, format="PNG")
        base64_data = base64.b64encode(byte_io.getvalue()).decode("utf-8")
        return {
            "type": "image_url",
            "detail": "high",
            "image_url": {"url": f"data:image/png;base64,{base64_data}"},
        }
    except Exception as e:
        logger.error("Error encoding page: %s", str(e))
        raise


class DocumentProcessor:
    """
    A generic processor for extracting data from documents using
    Azure Document Intelligence and OpenAI APIs.
    """

    def __init__(
        self,
        openai_client: AzureOpenAI,
        doc_intel_client: DocumentIntelligenceClient,
        config: Dict[str, Any],
    ):
        """
        Initialize the document processor.

        Args:
            openai_client: The OpenAI client
            doc_intel_client: The Document Intelligence client
            config: Configuration parameters
        """
        self.openai_client = openai_client
        self.doc_intel_client = doc_intel_client
        self.config = config

    def determine_model_type(
        self, file_path: str, specified_model: Optional[str] = None
    ) -> Type[BaseModel]:
        """
        Determine the appropriate model type for the document.

        Args:
            file_path: The path to the document
            specified_model: An optional model name to use

        Returns:
            The appropriate model class
        """
        if specified_model:
            # If a model is specified, use it
            model_class = get_model(specified_model)
            if model_class:
                return model_class
            logger.warning(
                f"Specified model '{specified_model}' not found in registry."
            )

        # Try to determine model type from filename
        filename = os.path.basename(file_path).lower()

        # Check for common document type indicators in the filename
        for indicator, doc_type in [
            ("invoice", "invoice"),
            ("bill", "invoice"),
            ("receipt", "invoice"),
            ("policy", "vehicle_insurance_policy"),
            ("insurance", "vehicle_insurance_policy"),
        ]:
            if indicator in filename:
                model_class = get_model_for_document_type(doc_type)
                if model_class:
                    logger.info(
                        f"Using model '{model_class.__name__}' based on filename"
                    )
                    return model_class

        # Default to Invoice if we can't determine the type
        # This is a fallback and should be replaced with a more robust solution
        logger.warning("Could not determine document type, defaulting to Invoice")
        return get_model("Invoice") or get_model("VehicleInsurancePolicy")

    def process_document(
        self, file_path: str, model_class: Optional[Type[BaseModel]] = None
    ) -> Dict[str, Any]:
        """
        Process a document using Azure Document Intelligence and OpenAI.

        Args:
            file_path: Path to the document file
            model_class: Optional specific model class to use

        Returns:
            dict: Extracted data, confidence values, and other metrics
        """
        logger.info("Processing document: %s", file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        # Get filename for output files
        pdf_fname = os.path.basename(file_path)

        # Determine the model class if not provided
        if model_class is None:
            model_class = self.determine_model_type(file_path)

        try:
            # Read the document file
            with open(file_path, "rb") as document_file:
                document_bytes = document_file.read()

            # Step 1: Process with Document Intelligence
            logger.info("Processing with Azure Document Intelligence...")
            di_processing_ms = 0
            with Stopwatch() as di_stopwatch:
                try:
                    poller = self.doc_intel_client.begin_analyze_document(
                        model_id="prebuilt-layout",
                        body=document_bytes,
                        output_content_format=DocumentContentFormat.MARKDOWN,
                        content_type="application/pdf",
                    )
                    result: AnalyzeResult = poller.result()
                    di_processing_ms = di_stopwatch.elapsed_ms()
                    logger.info(
                        "Document Intelligence processing completed in %dms",
                        di_processing_ms,
                    )
                except Exception as e:
                    logger.error("Document Intelligence processing failed: %s", str(e))
                    raise

            markdown = result.content

            # Step 2: Process document images
            logger.info("Processing document images...")
            user_content = []

            # Process images
            image_processing_ms = 0
            with Stopwatch() as image_stopwatch:
                try:
                    # Convert PDF to images
                    orig_pages = _render_pdf_to_images(document_bytes)
                    rotated_pages = orig_pages.copy()

                    # Rotate pages based on detected angles
                    for page_num, page in enumerate(rotated_pages):
                        if page_num < len(result.pages):
                            page_angle = result.pages[page_num].angle
                            if page_angle > 10 or page_angle < -10:
                                logger.warning(
                                    "Rotating page %d by %d degrees",
                                    page_num,
                                    page_angle,
                                )
                                rotated_pages[page_num] = page.rotate(page_angle)

                    # Process each page in parallel
                    with ThreadPoolExecutor(
                        max_workers=self.config.get("max_workers", 4)
                    ) as executor:
                        encoded_pages = list(executor.map(encode_page, rotated_pages))

                    image_processing_ms = image_stopwatch.elapsed_ms()
                    logger.info(
                        "Image processing completed in %dms with %d pages",
                        image_processing_ms,
                        len(rotated_pages),
                    )
                except Exception as e:
                    logger.error("Image processing failed: %s", str(e))
                    raise

            # Prepare user content for OpenAI
            md_pages = markdown.split("\n<!-- PageBreak -->\n")
            if len(md_pages) != len(encoded_pages):
                logger.warning(
                    "Number of pages in markdown and images do not match: %d vs %d",
                    len(md_pages),
                    len(encoded_pages),
                )

            for md_page, encoded_page in zip(md_pages, encoded_pages):
                user_content.append({"type": "text", "text": md_page})
                user_content.append(encoded_page)

            # Step 3: Process with OpenAI
            model_name = model_class.__name__
            logger.info(
                "Processing with OpenAI (%s) using model: %s",
                self.config.get("gpt4o_model_deployment_name", "model"),
                model_name,
            )
            oai_processing_ms = 0

            # Create a dynamic system prompt based on the model type
            system_text_prompt = f"""You are an AI assistant that extracts data from documents. Extract the data from this {model_name.replace("Insurance", " Insurance").replace("Policy", " Policy").lower()}. 
- If a value is missing, enter null.  
- Do not make assumptions or modify any data.  
- Format all data exactly as in the original document.  
- Preserve date formats as shown.  
- Extract numeric values as strings, exactly as they appear.
"""
            with Stopwatch() as oai_stopwatch:
                try:
                    completion = self.openai_client.beta.chat.completions.parse(
                        model=self.config.get("gpt4o_model_deployment_name", "gpt-4o"),
                        messages=[
                            {
                                "role": "system",
                                "content": system_text_prompt,
                            },
                            {"role": "user", "content": user_content},
                        ],
                        response_format=model_class,
                        max_tokens=4096,
                        temperature=0.0,
                        logprobs=True,  # Enabled to determine the confidence of the response
                    )
                    oai_processing_ms = oai_stopwatch.elapsed_ms()
                    logger.info(
                        "OpenAI processing completed in %dms", oai_processing_ms
                    )
                except Exception as e:
                    logger.error("OpenAI processing failed: %s", str(e))
                    raise

            # Step 4: Get parsed results and calculate confidence
            document_obj = completion.choices[0].message.parsed
            document_dict = document_obj.model_dump()

            # Show number of tokens used in the request
            logger.info("Request tokens used: %d", completion.usage.prompt_tokens)
            logger.info("Response tokens used: %d", completion.usage.completion_tokens)

            # Calculate confidence scores
            logger.info("Calculating confidence scores...")
            di_confidence = evaluate_di_confidence(document_dict, result)
            oai_confidence = evaluate_openai_confidence(
                document_dict, completion.choices[0]
            )
            confidence = merge_confidence_values(di_confidence, oai_confidence)

            # Step 5: Generate visualizations
            logger.info("Generating visualizations...")
            visualizations_folder = self.config.get(
                "visualizations_folder", "./visualizations"
            )
            os.makedirs(visualizations_folder, exist_ok=True)

            result_images = visualize_all_field_polygons(
                di_confidence=di_confidence,
                pages=orig_pages,
                output_folder=visualizations_folder,
                outline_color="lime",
                outline_width=4,
                original_filename=pdf_fname,
            )

            logger.info(
                "Generated %d visualizations in %s",
                len(result_images),
                visualizations_folder,
            )

            # Return results
            return {
                "document": document_obj,
                "document_dict": document_dict,
                "model_type": model_name,
                "di_confidence": di_confidence,
                "oai_confidence": oai_confidence,
                "confidence": confidence,
                "pdf_filename": pdf_fname,
                "visualizations": result_images,
                "performance": {
                    "di_processing_ms": di_processing_ms,
                    "image_processing_ms": image_processing_ms,
                    "oai_processing_ms": oai_processing_ms,
                    "total_ms": di_processing_ms
                    + image_processing_ms
                    + oai_processing_ms,
                },
                "markdown": markdown,
            }

        except Exception as e:
            logger.error("Document processing failed: %s", str(e))
            raise

    def save_results(self, results: Dict[str, Any], output_folder: str) -> None:
        """
        Save processing results to output files.

        Args:
            results: Dictionary containing processing results
            output_folder: Folder to save output files
        """
        try:
            document = results["document"]
            document_dict = results["document_dict"]
            pdf_fname = results["pdf_filename"]
            di_confidence = results["di_confidence"]
            oai_confidence = results["oai_confidence"]
            confidence = results["confidence"]
            markdown = results["markdown"]

            # Ensure output folder exists
            os.makedirs(output_folder, exist_ok=True)

            # Define output filenames
            extracted_file = os.path.join(output_folder, pdf_fname)

            # Save extracted data to JSON file
            with open(f"{extracted_file}.json", "w", encoding="utf-8") as f:
                f.write(document.model_dump_json(indent=4))

            # Save extracted data with converted dates to JSON file
            # Convert date strings in the dictionary to a consistent format
            converted_dict = self._convert_dates(document_dict)
            with open(f"{extracted_file}_dates.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(converted_dict, indent=4, cls=CustomJSONEncoder))

            # Save confidence values to JSON files
            with open(f"{extracted_file}_di_conf.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(di_confidence, indent=4, cls=CustomJSONEncoder))

            with open(f"{extracted_file}_oai_conf.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(oai_confidence, indent=4, cls=CustomJSONEncoder))

            with open(f"{extracted_file}_confidence.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(confidence, indent=4, cls=CustomJSONEncoder))

            # Save markdown content to file
            with open(f"{extracted_file}.md", "w", encoding="utf-8") as f:
                f.write(markdown)

            logger.info("Results saved to %s", output_folder)

        except Exception as e:
            logger.error("Error saving results: %s", str(e))
            raise

    def _convert_dates(self, dictionary, date_format="%Y-%m-%d"):
        """
        Convert date strings in the dictionary to a consistent format.

        Args:
            dictionary: Dictionary containing extracted data
            date_format: Desired date format (default: "YYYY-MM-DD")

        Returns:
            dict: Dictionary with converted date strings
        """
        result = dictionary.copy()
        for key, value in result.items():
            if isinstance(value, dict):
                result[key] = self._convert_dates(value, date_format)
            elif isinstance(value, list):
                result[key] = [
                    (
                        self._convert_dates(item, date_format)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                # Attempt to parse and reformat date strings
                try:
                    if (
                        "date" in key.lower()
                        or "_from" in key.lower()
                        or "_to" in key.lower()
                    ):
                        date = date_parser.parse(value)
                        result[key] = date.strftime(date_format)
                except (ValueError, TypeError):
                    continue
        return result
