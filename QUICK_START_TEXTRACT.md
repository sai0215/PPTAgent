# Quick Start: AWS Textract for PPTAgent

A 5-minute guide to get started with AWS Textract PDF parsing.

## ⚡ Quick Setup (3 Steps)

### 1. Install Dependencies
```bash
pip install "pptagent[textract]"
```

### 2. Set AWS Credentials
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="your_secret"
export PDF_PARSER="textract"
```

### 3. Run PPTAgent
```bash
python pptagent_ui/backend.py
```

That's it! 🎉

## 📋 Configuration Cheat Sheet

### MinerU (Default)
```bash
export PDF_PARSER="mineru"
export MINERU_API="http://localhost:8000/file_parse"
```

### AWS Textract
```bash
export PDF_PARSER="textract"
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_REGION="us-east-1"  # Optional
```

## 🔄 Switching Parsers

**To MinerU:**
```bash
export PDF_PARSER="mineru"
```

**To Textract:**
```bash
export PDF_PARSER="textract"
```

No code changes needed!

## 🐳 Docker Quick Start

```bash
docker run -dt --gpus all --ipc=host --name pptagent \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e PDF_PARSER="textract" \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -p 9297:9297 -p 8088:8088 \
  -v $HOME:/root \
  forceless/pptagent
```

## 🧪 Quick Test

```bash
# Test AWS Textract
python examples/textract_example.py \
  --pdf your_document.pdf \
  --output output_folder
```

## 💰 Cost Estimate

Typical 10-page document: **~$0.15**

[See AWS Pricing →](https://aws.amazon.com/textract/pricing/)

## 🆘 Common Issues

**"boto3 not found"**
```bash
pip install boto3
```

**"AWS credentials not set"**
```bash
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export PDF_PARSER="textract"
```

**"Access Denied"**
- Check IAM permissions for Textract

## 📚 Full Documentation

- [Complete Setup Guide](./AWS_TEXTRACT_SETUP.md)
- [Implementation Details](./TEXTRACT_IMPLEMENTATION.md)
- [PPTAgent Docs](./DOC.md)

## ✅ When to Use What

**Use AWS Textract if:**
- ✅ You want zero server setup
- ✅ You need excellent table extraction
- ✅ You're parsing scanned documents
- ✅ You want consistent performance

**Use MinerU if:**
- ✅ You want free/self-hosted solution
- ✅ You need offline processing
- ✅ You have infrastructure already
- ✅ You need data to stay local

## 🎯 One-Line Summary

**MinerU**: Free, self-hosted, requires server  
**Textract**: Managed, pay-per-use, no server

---

Need help? [Open an issue →](https://github.com/icip-cas/PPTAgent/issues)

