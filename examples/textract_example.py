"""
Example script demonstrating how to use AWS Textract with PPTAgent for PDF parsing.

This script shows:
1. How to configure AWS Textract
2. How to parse a PDF using AWS Textract
3. How to generate a presentation from the parsed PDF

Requirements:
- AWS account with Textract access
- boto3 package installed: pip install "pptagent[textract]"
- AWS credentials configured

Usage:
    python examples/textract_example.py --pdf path/to/document.pdf --output output/folder
"""

import argparse
import asyncio
import os
from pathlib import Path

from pptagent.model_utils import parse_pdf


async def parse_pdf_with_textract(pdf_path: str, output_folder: str):
    """
    Parse a PDF using AWS Textract.
    
    Args:
        pdf_path: Path to the PDF file
        output_folder: Output directory for parsed content
    """
    print(f"📄 Parsing PDF: {pdf_path}")
    print(f"📁 Output folder: {output_folder}")
    
    # Configure AWS Textract
    os.environ["PDF_PARSER"] = "textract"
    
    # Parse the PDF
    try:
        result = await parse_pdf(pdf_path, output_folder)
        print(f"✅ PDF parsed successfully!")
        print(f"📝 Markdown file: {os.path.join(output_folder, 'source.md')}")
        print(f"🖼️  Images folder: {os.path.join(output_folder, 'images')}")
        
        # Show a preview of the markdown content
        md_path = os.path.join(output_folder, "source.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                preview = content[:500] + "..." if len(content) > 500 else content
                print(f"\n📋 Content Preview:\n{preview}\n")
        
        return result
    except Exception as e:
        print(f"❌ Error parsing PDF: {e}")
        raise


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    if not access_key or not secret_key:
        print("❌ AWS credentials not found!")
        print("\nPlease set your AWS credentials:")
        print("  export AWS_ACCESS_KEY_ID='your_access_key'")
        print("  export AWS_SECRET_ACCESS_KEY='your_secret_key'")
        print("  export AWS_REGION='us-east-1'  # Optional")
        return False
    
    print("✅ AWS credentials found")
    print(f"   Region: {region}")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Parse PDF using AWS Textract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a PDF with AWS Textract
  python examples/textract_example.py --pdf document.pdf --output output/

  # Parse with specific AWS region
  AWS_REGION=eu-west-1 python examples/textract_example.py --pdf doc.pdf --output out/
        """
    )
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--output", required=True, help="Output folder for parsed content")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.pdf):
        print(f"❌ PDF file not found: {args.pdf}")
        return
    
    # Check AWS credentials
    if not check_aws_credentials():
        return
    
    # Create output folder
    os.makedirs(args.output, exist_ok=True)
    
    # Parse PDF
    await parse_pdf_with_textract(args.pdf, args.output)


if __name__ == "__main__":
    asyncio.run(main())

