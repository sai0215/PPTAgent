"""
Tests for PPTX Parser (Standard Template parsing)
"""

import os
import tempfile
from os.path import exists, join

import pytest

from pptagent.pptx_parser import (
    parse_standard_template_pptx,
    content_to_document_format,
    extract_font_info,
    FontInfo,
)
from test.conftest import test_config


@pytest.mark.asyncio
async def test_parse_standard_template_pptx():
    """Test parsing a Standard Template PPTX file"""
    pptx_path = join(test_config.presentation, "source.pptx")
    
    if not exists(pptx_path):
        pytest.skip(f"Test PPTX file not found: {pptx_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        content = await parse_standard_template_pptx(pptx_path, temp_dir)
        
        # Verify content structure
        assert content is not None
        assert content.num_slides > 0
        assert len(content.slides) > 0
        
        # Check first slide has content
        first_slide = content.slides[0]
        assert first_slide.slide_number == 1
        
        # Check markdown conversion
        markdown = content.to_markdown()
        assert "## Slide 1" in markdown
        
        # Check images folder created
        assert exists(join(temp_dir, "images"))


@pytest.mark.asyncio
async def test_content_to_document_format():
    """Test conversion of PPTX content to document format"""
    pptx_path = join(test_config.presentation, "source.pptx")
    
    if not exists(pptx_path):
        pytest.skip(f"Test PPTX file not found: {pptx_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        content = await parse_standard_template_pptx(pptx_path, temp_dir)
        doc_format = content_to_document_format(content)
        
        # Verify document format structure
        assert "sections" in doc_format
        assert "source_type" in doc_format
        assert doc_format["source_type"] == "pptx"
        assert doc_format["num_slides"] == content.num_slides
        
        # Verify sections have content
        if doc_format["sections"]:
            first_section = doc_format["sections"][0]
            assert "heading" in first_section
            assert "content" in first_section
            assert "metadata" in first_section


def test_font_info():
    """Test FontInfo dataclass"""
    font = FontInfo(
        name="Arial",
        size=18.0,
        bold=True,
        italic=False,
        underline=False,
        color_rgb=(255, 0, 0)
    )
    
    assert font.name == "Arial"
    assert font.size == 18.0
    assert font.bold is True
    assert font.italic is False
    assert font.color_rgb == (255, 0, 0)


@pytest.mark.asyncio
async def test_markdown_output_format():
    """Test that markdown output includes font comments"""
    pptx_path = join(test_config.presentation, "source.pptx")
    
    if not exists(pptx_path):
        pytest.skip(f"Test PPTX file not found: {pptx_path}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        content = await parse_standard_template_pptx(pptx_path, temp_dir)
        markdown = content.to_markdown()
        
        # Check markdown has slide markers
        assert "## Slide" in markdown
        
        # Check for font metadata comments (if fonts are present)
        # These are HTML comments with font information
        if content.slides and any(s.text_blocks for s in content.slides):
            assert "<!-- Font:" in markdown or len(content.slides[0].text_blocks) == 0

