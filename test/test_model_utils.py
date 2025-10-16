import os
import tempfile
from os.path import exists, join

import pytest

from pptagent.model_utils import parse_pdf, parse_pdf_textract, parse_pdf_mineru
from test.conftest import test_config


@pytest.mark.parse
@pytest.mark.asyncio
async def test_parse_pdf():
    """Test PDF parsing with the configured parser (MinerU or Textract)"""
    with tempfile.TemporaryDirectory() as temp_dir:
        await parse_pdf(
            join(test_config.document, "source.pdf"),
            temp_dir,
        )
        assert exists(join(temp_dir, "source.md"))


@pytest.mark.skipif(
    not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"),
    reason="AWS credentials not configured"
)
@pytest.mark.asyncio
async def test_parse_pdf_textract():
    """Test PDF parsing specifically with AWS Textract"""
    with tempfile.TemporaryDirectory() as temp_dir:
        await parse_pdf_textract(
            join(test_config.document, "source.pdf"),
            temp_dir,
        )
        assert exists(join(temp_dir, "source.md"))
        # Check if images folder was created
        assert exists(join(temp_dir, "images"))


@pytest.mark.skipif(
    not os.environ.get("MINERU_API"),
    reason="MINERU_API not configured"
)
@pytest.mark.asyncio
async def test_parse_pdf_mineru():
    """Test PDF parsing specifically with MinerU"""
    with tempfile.TemporaryDirectory() as temp_dir:
        await parse_pdf_mineru(
            join(test_config.document, "source.pdf"),
            temp_dir,
        )
        assert exists(join(temp_dir, "source.md"))
