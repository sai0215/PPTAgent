# AWS Textract Setup Guide for PPTAgent

This guide explains how to set up and use AWS Textract as an alternative PDF parser for PPTAgent.

## Why AWS Textract?

AWS Textract offers several advantages over MinerU:

✅ **No Server Setup Required** - Fully managed AWS service  
✅ **Superior Table Extraction** - Better handling of complex tables  
✅ **Built-in OCR** - Excellent for scanned documents  
✅ **Form Detection** - Automatically detects key-value pairs  
✅ **Pay-as-you-go** - No infrastructure costs  

## Prerequisites

1. **AWS Account** - You need an active AWS account
2. **AWS Credentials** - Access key ID and secret access key with Textract permissions
3. **Python Dependencies** - boto3 package

## Installation Steps

### Step 1: Install AWS Textract Dependencies

```bash
# Install PPTAgent with Textract support
pip install "pptagent[textract]"

# Or if installing from source
pip install -e ".[textract]"
```

### Step 2: Configure AWS Credentials

You have several options for providing AWS credentials:

#### Option A: Environment Variables (Recommended for Development)

```bash
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_REGION="us-east-1"  # Optional, defaults to us-east-1
export PDF_PARSER="textract"
```

#### Option B: AWS CLI Configuration

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
# Then just set the parser:
export PDF_PARSER="textract"
```

#### Option C: IAM Role (For EC2/ECS)

If running on AWS infrastructure, use an IAM role with Textract permissions:

```bash
# Just set the parser, credentials are auto-detected
export PDF_PARSER="textract"
```

### Step 3: Set Required IAM Permissions

Ensure your AWS credentials have the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage

### With WebUI

1. Set environment variables:
```bash
export OPENAI_API_KEY="your_key"
export API_BASE="http://your_service_provider/v1"
export LANGUAGE_MODEL="openai/gpt-4.1"
export VISION_MODEL="openai/gpt-4.1"

# AWS Textract Configuration
export PDF_PARSER="textract"
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"
```

2. Run backend:
```bash
python pptagent_ui/backend.py
```

3. Launch frontend:
```bash
cd pptagent_ui
npm install
npm run serve
```

### With Docker

```bash
docker run -dt --gpus all --ipc=host --name pptagent \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e PDF_PARSER="textract" \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_REGION="us-east-1" \
  -p 9297:9297 \
  -p 8088:8088 \
  -v $HOME:/root \
  forceless/pptagent
```

### Programmatically

```python
import os
from pptagent.model_utils import parse_pdf

# Set configuration
os.environ["PDF_PARSER"] = "textract"
os.environ["AWS_ACCESS_KEY_ID"] = "your_access_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "your_secret_key"
os.environ["AWS_REGION"] = "us-east-1"

# Parse PDF
import asyncio
result = asyncio.run(parse_pdf("path/to/document.pdf", "output/folder"))
```

## How It Works

When you use AWS Textract as the PDF parser:

1. **Upload PDF** - The PDF is read and sent to AWS Textract API
2. **Text Extraction** - Textract analyzes the document and extracts:
   - Text content with layout preservation
   - Tables in structured format
   - Document structure (headings, paragraphs)
3. **Image Extraction** - PDF pages are converted to images using `pdf2image`
4. **Markdown Conversion** - The Textract response is converted to markdown format
5. **Output** - Creates `source.md` and `images/` folder in the output directory

## Cost Considerations

AWS Textract pricing (as of 2024):
- **Detect Document Text**: $1.50 per 1,000 pages
- **Analyze Document (Tables/Forms)**: $15.00 per 1,000 pages

For most use cases, processing a typical 10-page document costs approximately $0.15.

See [AWS Textract Pricing](https://aws.amazon.com/textract/pricing/) for current rates.

## Troubleshooting

### Issue: "AWS credentials are not set"

**Solution**: Ensure you've exported the required environment variables:
```bash
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export PDF_PARSER="textract"
```

### Issue: "boto3 module not found"

**Solution**: Install the textract dependencies:
```bash
pip install "pptagent[textract]"
```

### Issue: "Access Denied" from AWS

**Solution**: Verify your IAM user/role has the required Textract permissions.

### Issue: "Unable to locate credentials"

**Solution**: Try one of these:
1. Use environment variables (most reliable)
2. Run `aws configure` to set up credentials
3. Use IAM role if on AWS infrastructure

### Issue: PDF parsing fails with large files

**Solution**: AWS Textract has size limits:
- Max file size: 10 MB (synchronous), 500 MB (asynchronous)
- For large files, consider splitting the PDF first

## Switching Back to MinerU

To switch back to MinerU:

```bash
export PDF_PARSER="mineru"
export MINERU_API="http://localhost:8000/file_parse"
```

## Comparison: AWS Textract vs MinerU

| Feature | AWS Textract | MinerU |
|---------|--------------|--------|
| Setup Complexity | Easy (managed service) | Moderate (self-hosted) |
| Table Extraction | Excellent | Good |
| OCR Quality | Excellent | Good |
| Cost | Pay-per-use | Free (self-hosted) |
| Speed | Fast | Varies |
| Infrastructure | None required | Need to run API server |
| Offline Support | No | Yes |

## Support

For issues or questions:
- [PPTAgent GitHub Issues](https://github.com/icip-cas/PPTAgent/issues)
- [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)

## License

This feature is part of PPTAgent and follows the same MIT license.

