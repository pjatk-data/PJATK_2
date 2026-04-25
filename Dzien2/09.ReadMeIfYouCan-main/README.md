# ReadMeIfYouCan - Document Intelligence with Azure AI and OpenAI

A comprehensive document processing solution that combines Azure Document Intelligence and OpenAI to extract structured data from various document types like invoices and vehicle insurance policies.

## Overview

ReadMeIfYouCan is designed to automatically extract, classify, and analyze information from documents with high accuracy. The solution leverages advanced AI technologies:

- **Azure Document Intelligence** for OCR and layout analysis
- **Azure OpenAI Services** for understanding document context and content extraction
- **Confidence scoring** to provide reliability metrics for extracted data

## Features

- **Generic Document Processing**: Process any type of document, with automatic model detection
- **Multiple Document Types**: Built-in support for invoices and vehicle insurance policies, easily extendable to other document types
- **High Accuracy Extraction**: Combines the strengths of OCR and AI to achieve better results than either technology alone
- **Confidence Scoring**: Detailed confidence metrics for every extracted field
- **Visualizations**: Visual feedback with highlighted extraction areas
- **Document Rotation**: Automatic correction of skewed documents
- **Date Normalization**: Standardization of dates for consistency
- **Output Formats**: Multiple output formats including JSON and Markdown

## Getting Started

### Prerequisites

- Python 3.10 or later
- An Azure subscription with:
  - Azure Document Intelligence resource
  - Azure OpenAI Service with GPT-4o model deployment

Optional (PDF rendering):
- `pdf2image` uses Poppler for PDF rendering. If Poppler isn't available (common on Windows ARM64), this project falls back to `pypdfium2`.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pbubacz/ReadMeIfYouCan.git
   cd ReadMeIfYouCan
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

  Notes for Windows ARM64 (Python ARM64):
  - `tiktoken` may require a Rust toolchain to build from source.
  - This repo treats `tiktoken` as optional on Windows ARM64; confidence scoring will use a lightweight fallback.

3. Set up environment variables (create a `.env` file in the project root):
   ```
   OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
   AI_SERVICES_ENDPOINT=https://your-document-intelligence-resource.cognitiveservices.azure.com/
   GPT4O_MODEL_DEPLOYMENT_NAME=your-model-deployment-name
   OUTPUT_FOLDER=./output
   MAX_WORKERS=4
   LOG_LEVEL=INFO
   ```

### Usage

#### Basic Usage

Process a document using the default settings:

```bash
python extract_data.py
```

This will process the default sample document (`./assets/invoices/invoice_5.pdf`) and save results to the `output` folder.

#### Specifying Documents and Models

Process a specific document with a specific model:

```bash
python extract_data.py --file ./assets/invoices/invoice_1.pdf --model Invoice
```

Available models:
- `Invoice`
- `VehicleInsurancePolicy`

#### Custom Output Location

Specify a custom output folder:

```bash
python extract_data.py --output ./my_results
```

## Project Structure

- **extract_data.py**: Main script for document processing
- **document_processor.py**: Core document processing logic
- **models/**: Data models for different document types
  - **invoice.py**: Invoice data model
  - **vehicle_insurance_policy.py**: Vehicle insurance policy data model
  - **model_registry.py**: Dynamic model registration and discovery
  - **classification.py**: Document classification models
  - **redaction.py**: Data redaction models
- **confidence/**: Confidence scoring logic
  - **document_intelligence_confidence.py**: Confidence metrics from Document Intelligence
  - **openai_confidence.py**: Confidence metrics from OpenAI
  - **confidence_utils.py**: Utilities for confidence scoring
- **utils/**: Utility functions
  - **visualization.py**: Visualization of extraction results
  - **image.py**: Image processing utilities
  - **stopwatch.py**: Performance measurement
  - **custom_json_encoder.py**: Custom JSON encoding
  - **value_utils.py**: Value normalization and formatting
- **assets/**: Sample documents for testing
  - **invoices/**: Sample invoice documents
  - **vehicle_insurance/**: Sample vehicle insurance policy documents
- **output/**: Output files (extraction results, visualizations, etc.)

## How It Works

1. **Document Upload**: The document is loaded and sent to Azure Document Intelligence.
2. **OCR and Layout Analysis**: Document Intelligence extracts text, tables, and positions.
3. **Image Processing**: Document pages are processed, including rotation correction.
4. **Model Selection**: The appropriate data model is selected based on document content.
5. **AI Processing**: OpenAI analyzes the document content and extracts structured data.
6. **Confidence Calculation**: Confidence scores are generated for all extracted fields.
7. **Visualization**: Visual feedback is generated showing extraction locations.
8. **Results Output**: Extracted data is saved in multiple formats.

## Output Files

For each processed document, the following output files are generated:

- **{filename}.json**: Raw extraction result in JSON format
- **{filename}_dates.json**: Extraction result with standardized dates
- **{filename}_di_conf.json**: Document Intelligence confidence scores
- **{filename}_oai_conf.json**: OpenAI confidence scores
- **{filename}_confidence.json**: Combined confidence scores
- **{filename}.md**: Document content in Markdown format
- **visualizations/{filename}_page_{n}.png**: Visualization of extraction results for each page

## Extending the System

### Adding New Document Types

1. Create a new model class in the `models` directory:
   ```python
   # models/my_new_document_type.py
   from pydantic import BaseModel, Field
   
   class MyNewDocumentType(BaseModel):
       field1: Optional[str] = Field(description="Description of field1")
       field2: Optional[int] = Field(description="Description of field2")
       # Add more fields as needed
   ```

2. The model will be automatically discovered and registered by the model registry.

### Custom Confidence Scoring

You can customize confidence scoring by modifying the evaluation functions in the `confidence` module.

## Performance Considerations

- **Multi-threading**: The system uses thread pooling for parallel processing of document pages.
- **Memory Usage**: Large documents with many pages may require significant memory.
- **API Costs**: Be aware of Azure Document Intelligence and OpenAI API usage costs.

## Sample Documents

The `assets` folder contains sample documents for testing:

### Invoices
- Various invoice types with different layouts and complexities
- Includes both digitized and scanned documents
- Some with handwriting, skewed scans, and other challenging elements

### Vehicle Insurance Policies
- Multi-page policy documents with complex information spread across pages
- Contains details on policy terms, coverage, and holder information

## License

See the [LICENSE](LICENSE) file for licensing information.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch (e.g., `feature/my-feature`)
3. Make your changes
4. Submit a pull request

## Acknowledgements

This project was inspired by real-world challenges in document processing and leverages ideas and code from several outstanding open-source initiatives. I gratefully acknowledge the following repositories for their valuable contributions:

- [Azure Samples - ARGUS](https://github.com/Azure-Samples/ARGUS): for foundational concepts in document intelligence and orchestration.
- [Azure Samples - multimodal-ai-llm-processing-accelerator](https://github.com/Azure/multimodal-ai-llm-processing-accelerator): for advanced patterns in integrating large language models with document workflows.
- [Azure Samples - azure-ai-document-processing-samples](https://github.com/Azure-Samples/azure-ai-document-processing-samples): for practical examples and reusable components in Azure AI Document Intelligence and sample documents.
These resources provided essential guidance and inspiration throughout the development of this project.

Sample documents sourced from [Kaggle - Tough Invoices](https://www.kaggle.com/datasets/dibyajyotimohanta/tough-invoices) and other sources
