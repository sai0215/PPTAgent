import os
import tempfile
import zipfile
from glob import glob
from os.path import join

import aiofiles
import aiohttp
from PIL import Image

from pptagent.llms import AsyncLLM
from pptagent.utils import (
    Language,
    get_logger,
    is_image_path,
)

logger = get_logger(__name__)

# Lazy loading cache for the language ID model
_LID_MODEL = None


def _get_lid_model():
    from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE

    """Get the language ID model, loading it lazily on first access."""
    global _LID_MODEL
    if _LID_MODEL is None:
        from fasttext import load_model
        from huggingface_hub import hf_hub_download

        lid_pattern = join(
            HUGGINGFACE_HUB_CACHE,
            "models--julien-c--fasttext-language-id",
            "*/*/lid.176.bin",
        )
        lid_files = glob(lid_pattern)
        if lid_files:
            _LID_MODEL = load_model(lid_files[0])
        else:
            _LID_MODEL = load_model(
                hf_hub_download(
                    repo_id="julien-c/fasttext-language-id",
                    filename="lid.176.bin",
                )
            )
    return _LID_MODEL


# PDF Parser Configuration
PDF_PARSER = os.environ.get("PDF_PARSER", "mineru")  # Options: "mineru" or "textract"
MINERU_API = os.environ.get("MINERU_API", None)

# AWS Textract Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET", None)  # Optional: for async processing
TEXTRACT_USE_ASYNC = os.environ.get("TEXTRACT_USE_ASYNC", "auto")  # auto, true, false

# Validate configuration
if PDF_PARSER == "mineru" and MINERU_API is None:
    logger.warning("PDF_PARSER is set to 'mineru' but MINERU_API is not set")
elif PDF_PARSER == "textract" and (AWS_ACCESS_KEY_ID is None or AWS_SECRET_ACCESS_KEY is None):
    logger.warning("PDF_PARSER is set to 'textract' but AWS credentials are not set")


class ModelManager:
    """
    A class to manage models.
    """

    def __init__(
        self,
        api_base: str | None = None,
        language_model_name: str | None = None,
        vision_model_name: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize models from environment variables after instance creation"""
        if api_base is None:
            api_base = os.environ.get("API_BASE", "https://api.perplexity.ai")
        if language_model_name is None:
            language_model_name = os.environ.get("LANGUAGE_MODEL", "sonar-pro")
        if vision_model_name is None:
            vision_model_name = os.environ.get("VISION_MODEL", "sonar-pro")
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key is None:
                raise ValueError(
                    "API key not provided. Please set OPENAI_API_KEY environment variable.\n"
                    "Create a .env file with:\n"
                    "  OPENAI_API_KEY=your_api_key_here\n"
                    "See .env.example for template."
                )
        self._image_model = None

        self.language_model = AsyncLLM(language_model_name, api_base, api_key)
        self.vision_model = AsyncLLM(vision_model_name, api_base, api_key)

    @property
    def image_model(self):
        import torch

        if self._image_model is None:
            self._image_model = get_image_model(
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
        return self._image_model

    async def test_connections(self) -> bool:
        """Test connections for all LLM models

        Returns:
            bool: True if all connections are successful, False otherwise
        """
        try:
            assert await self.language_model.test_connection()
            assert await self.vision_model.test_connection()
        except Exception as _:
            return False
        return True


def language_id(text: str) -> Language:
    model = _get_lid_model()
    return Language(
        lid=model.predict(text[:1024].replace("\n", ""))[0][0].replace("__label__", "")
    )


def get_image_model(device: str = None):
    import torch
    from transformers import AutoModel, AutoProcessor

    """
    Initialize and return an image model and its feature extractor.

    Args:
        device (str): The device to run the model on.

    Returns:
        tuple: A tuple containing the feature extractor and the image model.
    """
    model_base = "google/vit-base-patch16-224-in21k"
    return (
        AutoProcessor.from_pretrained(
            model_base,
            torch_dtype=torch.float16,
            device_map=device,
            use_fast=True,
        ),
        AutoModel.from_pretrained(
            model_base,
            torch_dtype=torch.float16,
            device_map=device,
        ).eval(),
    )


async def parse_pdf_textract_async(pdf_path: str, output_folder: str):
    """
    Parse a PDF file using AWS Textract ASYNC API (supports up to 500MB files).
    
    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The root directory to save the extracted content.
    
    Returns:
        str: The path to the extracted folder
    """
    try:
        import boto3
        from pdf2image import convert_from_path
        import time
        import asyncio
    except ImportError as e:
        raise RuntimeError(
            f"Required package not installed: {e}\n"
            "Install with: pip install boto3 pdf2image"
        )

    if AWS_ACCESS_KEY_ID is None or AWS_SECRET_ACCESS_KEY is None:
        raise RuntimeError(
            "AWS credentials are not set. Please set up AWS Textract.\n"
            "Set environment variables:\n"
            "  export AWS_ACCESS_KEY_ID='your_access_key'\n"
            "  export AWS_SECRET_ACCESS_KEY='your_secret_key'\n"
            "  export AWS_REGION='us-east-1'\n"
            "  export PDF_PARSER='textract'"
        )

    os.makedirs(output_folder, exist_ok=True)
    images_folder = os.path.join(output_folder, "images")
    os.makedirs(images_folder, exist_ok=True)

    # Initialize clients
    textract = boto3.client(
        'textract',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Check file size
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    logger.info(f"PDF file size: {file_size_mb:.2f} MB (using ASYNC processing)")
    
    if file_size_mb > 500:
        raise RuntimeError(
            f"PDF file is too large ({file_size_mb:.2f} MB). AWS Textract async limit is 500MB."
        )

    # Upload to S3 if bucket is configured, otherwise use image-based approach
    if AWS_S3_BUCKET:
        logger.info(f"Uploading PDF to S3 bucket: {AWS_S3_BUCKET}")
        
        # Generate unique S3 key
        import uuid
        s3_key = f"textract-input/{uuid.uuid4()}/{os.path.basename(pdf_path)}"
        
        try:
            # Upload PDF to S3
            async with aiofiles.open(pdf_path, 'rb') as f:
                pdf_bytes = await f.read()
            
            s3.put_object(
                Bucket=AWS_S3_BUCKET,
                Key=s3_key,
                Body=pdf_bytes
            )
            logger.info(f"Uploaded to S3: s3://{AWS_S3_BUCKET}/{s3_key}")
            
            # Start async Textract job
            logger.info("Starting async Textract job")
            response = textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': AWS_S3_BUCKET,
                        'Name': s3_key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            job_id = response['JobId']
            logger.info(f"Textract job started: {job_id}")
            
            # Poll for completion
            max_wait_time = 300  # 5 minutes max
            poll_interval = 2  # seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
                result = textract.get_document_analysis(JobId=job_id)
                status = result['JobStatus']
                
                logger.info(f"Job status: {status} (elapsed: {elapsed}s)")
                
                if status == 'SUCCEEDED':
                    logger.info("Textract job completed successfully")
                    
                    # Get all pages of results
                    all_blocks = result.get('Blocks', [])
                    next_token = result.get('NextToken')
                    
                    while next_token:
                        result = textract.get_document_analysis(
                            JobId=job_id,
                            NextToken=next_token
                        )
                        all_blocks.extend(result.get('Blocks', []))
                        next_token = result.get('NextToken')
                    
                    logger.info(f"Retrieved {len(all_blocks)} blocks from Textract")
                    
                    # Process results
                    markdown_content = _textract_blocks_to_markdown(all_blocks)
                    
                    # Clean up S3
                    try:
                        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
                        logger.info(f"Cleaned up S3 object: {s3_key}")
                    except:
                        pass
                    
                    break
                    
                elif status == 'FAILED':
                    error_msg = result.get('StatusMessage', 'Unknown error')
                    logger.error(f"Textract job failed: {error_msg}")
                    
                    # Clean up S3
                    try:
                        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
                    except:
                        pass
                    
                    raise RuntimeError(f"Textract async job failed: {error_msg}")
            
            if elapsed >= max_wait_time:
                raise RuntimeError(f"Textract job timed out after {max_wait_time}s")
            
        except Exception as e:
            logger.error(f"Async S3-based Textract failed: {e}")
            # Fall back to image-based processing
            logger.info("Falling back to image-based processing")
            return await parse_pdf_textract_sync(pdf_path, output_folder)
    else:
        # No S3 bucket configured, use image-based approach
        logger.info("No S3 bucket configured, using image-based processing")
        return await parse_pdf_textract_sync(pdf_path, output_folder)
    
    # Extract images for reference
    try:
        images = convert_from_path(pdf_path, dpi=150)
        for idx, img in enumerate(images):
            img_path = os.path.join(images_folder, f"page_{idx+1:03d}.png")
            img.save(img_path, "PNG")
        logger.info(f"Saved {len(images)} page images")
    except Exception as e:
        logger.warning(f"Failed to extract page images: {e}")

    # Save markdown file
    markdown_path = os.path.join(output_folder, "source.md")
    async with aiofiles.open(markdown_path, "w", encoding="utf-8") as f:
        await f.write(markdown_content)

    logger.info(f"PDF parsed successfully using AWS Textract ASYNC: {markdown_path}")
    return output_folder


async def parse_pdf_textract(pdf_path: str, output_folder: str):
    """
    Parse a PDF file using AWS Textract (intelligently chooses async vs sync).

    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The root directory to save the extracted content.

    Returns:
        str: The path to the extracted folder
    """
    # Check file size to decide between async and sync
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    use_async = TEXTRACT_USE_ASYNC.lower()
    
    # Decide which method to use
    if use_async == "true" or (use_async == "auto" and file_size_mb > 10):
        # Use async for files > 10MB or if explicitly requested
        logger.info(f"Using ASYNC Textract API (file: {file_size_mb:.2f} MB)")
        return await parse_pdf_textract_async(pdf_path, output_folder)
    else:
        # Use sync (image-based) for smaller files or if explicitly requested
        logger.info(f"Using SYNC Textract API (file: {file_size_mb:.2f} MB)")
        return await parse_pdf_textract_sync(pdf_path, output_folder)


async def parse_pdf_textract_sync(pdf_path: str, output_folder: str):
    """
    Parse a PDF file using AWS Textract SYNC API (image-based, up to 10MB).

    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The root directory to save the extracted content.

    Returns:
        str: The path to the extracted folder
    """
    try:
        import boto3
        from pdf2image import convert_from_path
    except ImportError as e:
        raise RuntimeError(
            f"Required package not installed: {e}\n"
            "Install with: pip install boto3 pdf2image"
        )

    if AWS_ACCESS_KEY_ID is None or AWS_SECRET_ACCESS_KEY is None:
        raise RuntimeError(
            "AWS credentials are not set. Please set up AWS Textract.\n"
            "Set environment variables:\n"
            "  export AWS_ACCESS_KEY_ID='your_access_key'\n"
            "  export AWS_SECRET_ACCESS_KEY='your_secret_key'\n"
            "  export AWS_REGION='us-east-1'  # Optional, defaults to us-east-1\n"
            "  export PDF_PARSER='textract'"
        )

    os.makedirs(output_folder, exist_ok=True)
    images_folder = os.path.join(output_folder, "images")
    os.makedirs(images_folder, exist_ok=True)

    # Initialize Textract client
    textract = boto3.client(
        'textract',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Check file size first
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    logger.info(f"PDF file size: {file_size_mb:.2f} MB")
    
    if file_size_mb > 10:
        logger.warning(f"PDF file is {file_size_mb:.2f} MB, which exceeds AWS Textract's 10MB limit for synchronous processing")
        raise RuntimeError(
            f"PDF file is too large ({file_size_mb:.2f} MB). AWS Textract synchronous limit is 10MB.\n"
            "Please use a smaller PDF or consider using MinerU parser instead:\n"
            "  export PDF_PARSER='mineru'"
        )

    # Extract images from PDF using pdf2image first
    logger.info(f"Converting PDF to images: {pdf_path}")
    try:
        # Convert PDF pages to images - this is more reliable than direct PDF processing
        images = convert_from_path(pdf_path, dpi=200)  # 200 DPI for good quality
        logger.info(f"Successfully converted PDF to {len(images)} images")
        
        # Save images for reference
        for idx, img in enumerate(images):
            img_path = os.path.join(images_folder, f"page_{idx+1:03d}.png")
            img.save(img_path, "PNG")
        logger.info(f"Saved {len(images)} page images to {images_folder}")
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        raise RuntimeError(
            f"Failed to convert PDF to images: {e}\n"
            "This usually means:\n"
            "  1. The PDF is corrupted or encrypted\n"
            "  2. Missing system dependencies (poppler-utils)\n"
            "  3. The PDF has an unsupported format\n"
            "Try using MinerU instead: export PDF_PARSER='mineru'"
        )

    # Process each page with Textract
    logger.info(f"Processing {len(images)} pages with AWS Textract")
    all_text_blocks = []
    
    for idx, img in enumerate(images):
        page_num = idx + 1
        logger.info(f"Processing page {page_num}/{len(images)}")
        
        try:
            # Convert PIL Image to bytes
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Check image size (should be under 10MB)
            img_size_mb = len(img_bytes) / (1024 * 1024)
            if img_size_mb > 10:
                logger.warning(f"Page {page_num} image is {img_size_mb:.2f} MB, reducing quality")
                # Reduce image size if too large
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG', optimize=True, quality=85)
                img_bytes = img_byte_arr.getvalue()
            
            # Try AnalyzeDocument with TABLES first
            response = None
            try:
                logger.info(f"Page {page_num}: Trying AnalyzeDocument with TABLES")
                response = textract.analyze_document(
                    Document={'Bytes': img_bytes},
                    FeatureTypes=['TABLES']
                )
                logger.info(f"Page {page_num}: AnalyzeDocument succeeded")
            except Exception as e:
                logger.warning(f"Page {page_num}: AnalyzeDocument failed: {e}")
                # Fall back to DetectDocumentText
                try:
                    logger.info(f"Page {page_num}: Falling back to DetectDocumentText")
                    response = textract.detect_document_text(
                        Document={'Bytes': img_bytes}
                    )
                    logger.info(f"Page {page_num}: DetectDocumentText succeeded")
                except Exception as e2:
                    logger.error(f"Page {page_num}: Both methods failed: {e2}")
                    # Continue with next page instead of failing completely
                    continue
            
            if response:
                # Add page number marker
                all_text_blocks.append(f"\n## Page {page_num}\n")
                # Extract text from this page's response
                page_text = _textract_response_to_text(response)
                all_text_blocks.append(page_text)
                
        except Exception as e:
            logger.error(f"Failed to process page {page_num}: {e}")
            # Continue with next page
            continue
    
    if not all_text_blocks:
        raise RuntimeError(
            "Failed to extract any text from the PDF using AWS Textract.\n"
            "The PDF might be:\n"
            "  1. Image-based without searchable text\n"
            "  2. Encrypted or password protected\n"
            "  3. Corrupted\n"
            "Try using MinerU instead: export PDF_PARSER='mineru'"
        )
    
    # Combine all text
    markdown_content = "\n".join(all_text_blocks)
    
    # Add reference to extracted page images
    if os.path.exists(images_folder):
        image_files = sorted([f for f in os.listdir(images_folder) if f.endswith('.png')])
        if image_files:
            markdown_content += "\n\n## Extracted Page Images\n"
            for img_file in image_files:
                img_path = os.path.join(images_folder, img_file)
                markdown_content += f"\n![{img_file}]({img_path})"

    # Save markdown file
    markdown_path = os.path.join(output_folder, "source.md")
    async with aiofiles.open(markdown_path, "w", encoding="utf-8") as f:
        await f.write(markdown_content)

    logger.info(f"PDF parsed successfully using AWS Textract: {markdown_path}")
    return output_folder


def _textract_blocks_to_markdown(blocks: list) -> str:
    """
    Convert Textract blocks to markdown format.
    
    Args:
        blocks (list): List of Textract blocks.
    
    Returns:
        str: Markdown formatted content.
    """
    text_lines = []
    tables = []
    
    # Process blocks
    for block in blocks:
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '').strip()
            if text:
                # Simple heuristic for headings
                if len(text) < 50 and text.isupper():
                    text_lines.append(f"\n## {text}\n")
                else:
                    text_lines.append(text)
        elif block.get('BlockType') == 'TABLE':
            # Process table
            table_md = _process_textract_table(block, blocks)
            if table_md:
                tables.append(f"\n{table_md}\n")
    
    # Combine text and tables
    result = "\n".join(text_lines)
    if tables:
        result += "\n" + "\n".join(tables)
    
    return result


def _textract_response_to_text(response: dict) -> str:
    """
    Extract text from a single Textract response.
    
    Args:
        response (dict): The Textract API response.
    
    Returns:
        str: The extracted text content.
    """
    blocks = response.get('Blocks', [])
    text_lines = []
    tables = []
    
    # Extract LINE blocks for text content
    for block in blocks:
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '').strip()
            if text:
                # Simple heuristic for headings
                if len(text) < 50 and text.isupper():
                    text_lines.append(f"\n### {text}\n")
                else:
                    text_lines.append(text)
        elif block.get('BlockType') == 'TABLE':
            # Process table
            table_md = _process_textract_table(block, blocks)
            if table_md:
                tables.append(f"\n{table_md}\n")
    
    # Combine text and tables
    result = "\n".join(text_lines)
    if tables:
        result += "\n" + "\n".join(tables)
    
    return result


def _textract_to_markdown(response: dict, images_folder: str) -> str:
    """
    Convert AWS Textract response to Markdown format.

    Args:
        response (dict): The Textract API response.
        images_folder (str): The folder containing extracted images.

    Returns:
        str: The markdown content.
    """
    blocks = response.get('Blocks', [])
    markdown_lines = []
    current_page = 1
    
    # Group blocks by type
    blocks_by_type = {
        'LINE': [],
        'WORD': [],
        'TABLE': [],
        'CELL': [],
        'LAYOUT': []
    }
    
    for block in blocks:
        block_type = block.get('BlockType')
        if block_type in blocks_by_type:
            blocks_by_type[block_type].append(block)

    # Process LINE blocks for text content
    for block in blocks:
        if block.get('BlockType') == 'LINE':
            text = block.get('Text', '').strip()
            if text:
                # Detect headings (simple heuristic: short lines in uppercase or with larger font)
                if len(text) < 50 and text.isupper():
                    markdown_lines.append(f"\n## {text}\n")
                else:
                    markdown_lines.append(text)
        
        elif block.get('BlockType') == 'TABLE':
            # Process tables
            table_md = _process_textract_table(block, blocks)
            if table_md:
                markdown_lines.append(f"\n{table_md}\n")

    # Add reference to extracted page images
    if os.path.exists(images_folder):
        image_files = sorted([f for f in os.listdir(images_folder) if f.endswith('.png')])
        if image_files:
            markdown_lines.append("\n## Extracted Page Images\n")
            for img_file in image_files:
                img_path = os.path.join(images_folder, img_file)
                markdown_lines.append(f"![{img_file}]({img_path})")

    return "\n".join(markdown_lines)


def _process_textract_table(table_block: dict, all_blocks: list) -> str:
    """
    Process a Textract TABLE block and convert it to Markdown table format.

    Args:
        table_block (dict): The TABLE block from Textract.
        all_blocks (list): All blocks from the Textract response.

    Returns:
        str: Markdown table representation.
    """
    # Create a mapping of block IDs to blocks
    block_map = {block['Id']: block for block in all_blocks}
    
    # Get table cells
    relationships = table_block.get('Relationships', [])
    cell_ids = []
    for relationship in relationships:
        if relationship.get('Type') == 'CHILD':
            cell_ids.extend(relationship.get('Ids', []))
    
    # Organize cells by row and column
    cells = {}
    max_row = 0
    max_col = 0
    
    for cell_id in cell_ids:
        if cell_id not in block_map:
            continue
        cell = block_map[cell_id]
        if cell.get('BlockType') != 'CELL':
            continue
        
        row_index = cell.get('RowIndex', 1) - 1
        col_index = cell.get('ColumnIndex', 1) - 1
        max_row = max(max_row, row_index)
        max_col = max(max_col, col_index)
        
        # Get cell text
        cell_text = ""
        cell_relationships = cell.get('Relationships', [])
        for rel in cell_relationships:
            if rel.get('Type') == 'CHILD':
                for word_id in rel.get('Ids', []):
                    if word_id in block_map:
                        word_block = block_map[word_id]
                        if word_block.get('BlockType') == 'WORD':
                            cell_text += word_block.get('Text', '') + " "
        
        cells[(row_index, col_index)] = cell_text.strip()
    
    # Build markdown table
    if max_row < 0 or max_col < 0 or len(cells) == 0:
        # No valid table data
        return ""
    
    # Ensure we have at least a 1x1 table
    if max_row == 0 and max_col == 0 and (0, 0) not in cells:
        return ""
    
    markdown_rows = []
    
    # Build each row
    for row in range(max_row + 1):
        row_cells = []
        for col in range(max_col + 1):
            cell_content = cells.get((row, col), "")
            # Escape pipe characters in cells and clean up
            cell_content = cell_content.replace("|", "\\|").strip()
            # Ensure cell is not empty (use space if needed)
            if not cell_content:
                cell_content = " "
            row_cells.append(cell_content)
        
        # Build the row
        markdown_rows.append("| " + " | ".join(row_cells) + " |")
        
        # Add separator after first row (header row)
        if row == 0:
            # Ensure separator has correct number of columns
            separator = "| " + " | ".join(["---"] * (max_col + 1)) + " |"
            markdown_rows.append(separator)
    
    # Validate table has content
    if len(markdown_rows) < 2:  # Must have at least header + separator
        return ""
    
    return "\n".join(markdown_rows)


async def parse_pdf_mineru(pdf_path: str, output_folder: str):
    """
    Parse a PDF file using MinerU and extract text and images.

    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The root directory to save the extracted content.

    Returns:
        str: The path to the extracted folder
    """
    if MINERU_API is None:
        raise RuntimeError(
            "MINERU_API is not set. Please set up MinerU API service.\n"
            "Quick setup: Install MinerU following https://opendatalab.github.io/MinerU/\n"
            "Then set: export MINERU_API='http://localhost:8000/file_parse'"
        )
    os.makedirs(output_folder, exist_ok=True)

    async with aiofiles.open(pdf_path, "rb") as f:
        pdf_content = await f.read()

    data = aiohttp.FormData()
    data.add_field(
        "files",
        pdf_content,
        filename=os.path.basename(pdf_path),
        content_type="application/pdf",
    )
    data.add_field("return_images", "True")
    data.add_field("response_format_zip", "True")

    async with aiohttp.ClientSession() as session:
        async with session.post(MINERU_API, data=data) as response:
            response.raise_for_status()
            content = await response.read()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(content)
                zip_path = tmp.name

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                top_level = {
                    name.split("/", 1)[0] for name in zip_ref.namelist() if name.strip()
                }
                if len(top_level) != 1:
                    raise RuntimeError("Expected exactly one top-level folder in zip")
                prefix = list(top_level)[0] + "/"

                for member in zip_ref.infolist():
                    filename = member.filename
                    dest_path = os.path.join(
                        output_folder, filename.removeprefix(prefix)
                    )

                    if not member.is_dir():
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with zip_ref.open(member) as src, open(dest_path, "wb") as dst:
                            dst.write(src.read())

    logger.info(f"PDF parsed successfully using MinerU: {output_folder}")
    return output_folder


async def parse_pdf(pdf_path: str, output_folder: str):
    """
    Parse a PDF file and extract text and images using the configured parser.
    
    The parser is selected via the PDF_PARSER environment variable:
    - "mineru": Use MinerU API (requires MINERU_API to be set)
    - "textract": Use AWS Textract (requires AWS credentials)
    
    Args:
        pdf_path (str): The path to the PDF file.
        output_folder (str): The root directory to save the extracted content.
    
    Returns:
        str: The path to the extracted folder
    
    Raises:
        RuntimeError: If the selected parser is not configured properly.
    """
    parser = PDF_PARSER.lower()
    
    if parser == "textract":
        logger.info(f"Using AWS Textract to parse PDF: {pdf_path}")
        return await parse_pdf_textract(pdf_path, output_folder)
    elif parser == "mineru":
        logger.info(f"Using MinerU to parse PDF: {pdf_path}")
        return await parse_pdf_mineru(pdf_path, output_folder)
    else:
        raise RuntimeError(
            f"Invalid PDF_PARSER value: '{PDF_PARSER}'. Valid options are 'mineru' or 'textract'.\n"
            f"Set with: export PDF_PARSER='textract'  # or 'mineru'"
        )


def get_image_embedding(
    image_dir: str, extractor, model, batchsize: int = 16
) -> dict[str, list[float]]:
    """
    Generate image embeddings for images in a directory.

    Args:
        image_dir (str): The directory containing images.
        extractor: The feature extractor for images.
        model: The model used for generating embeddings.
        batchsize (int): The batch size for processing images.

    Returns:
        dict: A dictionary mapping image filenames to their embeddings.
    """
    import torch
    import torchvision.transforms as T

    transform = T.Compose(
        [
            T.Resize(int((256 / 224) * extractor.size["height"])),
            T.CenterCrop(extractor.size["height"]),
            T.ToTensor(),
            T.Normalize(mean=extractor.image_mean, std=extractor.image_std),
        ]
    )

    inputs = []
    embeddings = []
    images = [i for i in sorted(os.listdir(image_dir)) if is_image_path(i)]
    for file in images:
        image = Image.open(join(image_dir, file)).convert("RGB")
        inputs.append(transform(image))
        if len(inputs) % batchsize == 0 or file == images[-1]:
            batch = {"pixel_values": torch.stack(inputs).to(model.device)}
            embeddings.extend(model(**batch).last_hidden_state.detach())
            inputs.clear()
    return {
        image: embedding.flatten().tolist()
        for image, embedding in zip(images, embeddings)
    }


def images_cosine_similarity(embeddings: list[list[float]]) -> list[float]:
    """
    Calculate the cosine similarity matrix for a list of embeddings.
    Args:
        embeddings (list[torch.Tensor]): A list of image embeddings.

    Returns:
        torch.Tensor: A NxN similarity matrix.
    """
    import torch

    embeddings = [torch.tensor(embedding) for embedding in embeddings]
    sim_matrix = torch.zeros((len(embeddings), len(embeddings)))
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            sim_matrix[i, j] = sim_matrix[j, i] = torch.nn.functional.cosine_similarity(
                embeddings[i], embeddings[j], -1
            )
    return sim_matrix.tolist()


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def average_distance(
    similarity: list[list[float]], idx: int, cluster_idx: list[int]
) -> float:
    """
    Calculate the average distance between a point (idx) and a cluster (cluster_idx).

    Args:
        similarity (list[list[float]]): The similarity matrix.
        idx (int): The index of the point.
        cluster_idx (list): The indices of the cluster.

    Returns:
        float: The average distance.
    """
    import torch

    similarity = torch.tensor(similarity)
    if idx in cluster_idx:
        return 0
    total_similarity = 0
    for idx_in_cluster in cluster_idx:
        total_similarity += similarity[idx, idx_in_cluster]
    return total_similarity / len(cluster_idx)


def get_cluster(similarity: list[list[float]], sim_bound: float = 0.65):
    """
    Cluster points based on similarity.

    Args:
        similarity (list[list[float]]): The similarity matrix.
        sim_bound (float): The similarity threshold for clustering.

    Returns:
        list: A list of clusters.
    """
    import torch

    similarity = torch.tensor(similarity)
    sim_copy = similarity.clone()
    num_points = sim_copy.shape[0]
    clusters = []
    added = [False] * num_points

    while True:
        max_avg_dist = sim_bound
        best_cluster = None
        best_point = None

        for c in clusters:
            for point_idx in range(num_points):
                if added[point_idx]:
                    continue
                avg_dist = average_distance(sim_copy, point_idx, c)
                if avg_dist > max_avg_dist:
                    max_avg_dist = avg_dist
                    best_cluster = c
                    best_point = point_idx

        if best_point is not None:
            best_cluster.append(best_point)
            added[best_point] = True
            sim_copy[best_point, :] = 0
            sim_copy[:, best_point] = 0
        else:
            if sim_copy.max() < sim_bound:
                # append the remaining points individual cluster
                for i in range(num_points):
                    if not added[i]:
                        clusters.append([i])
                break
            i, j = torch.unravel_index(torch.argmax(sim_copy), sim_copy.shape)
            clusters.append([int(i), int(j)])
            added[i] = True
            added[j] = True
            sim_copy[i, :] = 0
            sim_copy[:, i] = 0
            sim_copy[j, :] = 0
            sim_copy[:, j] = 0

    return clusters
