# Environment Variables Setup Guide

## ✅ Secure Credential Management

Your credentials are now safely stored in a `.env` file that's protected from git!

## 📁 File Structure

```
PPTAgent/
├── .env                # Your actual credentials (NEVER commit this!)
├── .env.example        # Template file (safe to commit)
├── .gitignore          # Already includes .env
└── run_with_textract.sh # Loads from .env automatically
```

## 🔒 Security Features

**✅ Protected:**
- `.env` is in `.gitignore` - won't be committed to git
- Your credentials stay local and private
- Safe to share your code without exposing keys

**✅ Easy to Use:**
- One command to run: `./run_with_textract.sh`
- Automatically loads all variables from `.env`
- No need to export variables manually

## 🚀 Quick Start

### 1. Your `.env` File is Already Set Up!

Located at: `.env`

Contains your:
- AWS Textract credentials
- Perplexity API key
- PDF parser configuration

### 2. Run the Backend

```bash
./run_with_textract.sh
```

That's it! The script automatically:
1. Loads all variables from `.env`
2. Validates the file exists
3. Starts the backend with your credentials

## 📝 How It Works

### Before (❌ Exposed Credentials)
```bash
#!/bin/bash
PDF_PARSER=textract \
AWS_ACCESS_KEY_ID=AKIA... \  # Exposed in script!
AWS_SECRET_ACCESS_KEY=Zaz... \  # Visible in git!
python pptagent_ui/backend.py
```

### After (✅ Secure)
```bash
#!/bin/bash
# Load from .env (protected from git)
export $(cat .env | grep -v '^#' | xargs)
python pptagent_ui/backend.py
```

## 🔧 Customizing Your Configuration

### Edit Your Credentials

```bash
# Safe to edit - won't be committed to git
nano .env
```

### Available Options

```bash
# PDF Parser
PDF_PARSER=textract          # or "mineru"

# AWS Textract
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1

# Optional: Async processing
AWS_S3_BUCKET=my-bucket      # For PDFs > 10MB
TEXTRACT_USE_ASYNC=auto      # auto, true, or false

# LLM Configuration
OPENAI_API_KEY=...
API_BASE=https://api.perplexity.ai
LANGUAGE_MODEL=sonar-pro
VISION_MODEL=sonar-pro
```

## 🔄 Switching LLM Providers

### Option 1: Use OpenAI

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-openai-key
API_BASE=https://api.openai.com/v1
LANGUAGE_MODEL=gpt-4o
VISION_MODEL=gpt-4o
```

### Option 2: Use Claude

Edit `.env`:
```bash
OPENAI_API_KEY=your-anthropic-key
API_BASE=https://api.anthropic.com
LANGUAGE_MODEL=claude-3-opus
VISION_MODEL=claude-3-opus
```

### Option 3: Stay with Perplexity (Current)

Already configured! Just wait for rate limits to reset.

## 📦 Sharing Your Project

### What to Share

✅ **Safe to commit:**
- `run_with_textract.sh`
- `.env.example`
- `.gitignore`
- All code files

❌ **NEVER commit:**
- `.env` (your actual credentials)

### For New Users

1. Clone the repository
2. Copy the template:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` with their own credentials
4. Run: `./run_with_textract.sh`

## 🛡️ Security Best Practices

### ✅ DO:
- Keep `.env` file local only
- Use different credentials for different environments (dev/prod)
- Rotate credentials regularly
- Use IAM roles when possible (on AWS EC2/ECS)

### ❌ DON'T:
- Commit `.env` to git
- Share `.env` file in chat/email
- Put credentials in code files
- Use production keys in development

## 🔍 Verification

### Check if `.env` is Protected

```bash
# This should show .env is ignored
git status

# .env should NOT appear in untracked files
```

### Check if Variables are Loaded

```bash
./run_with_textract.sh

# You should see:
# ✅ Loaded configuration from .env
```

### Test the Setup

```bash
# Run and check for credential errors
./run_with_textract.sh

# If you see AWS/Perplexity errors, credentials are being used
# If you see "not set" errors, .env isn't loading
```

## 🎯 Common Issues

### Issue 1: "No such file or directory"

**Problem:** `.env` file doesn't exist

**Solution:**
```bash
cp .env.example .env
nano .env  # Add your credentials
```

### Issue 2: "Permission denied"

**Problem:** Script not executable

**Solution:**
```bash
chmod +x run_with_textract.sh
```

### Issue 3: "credentials not set"

**Problem:** `.env` not loading properly

**Solution:**
```bash
# Check file exists
ls -la .env

# Check content format (no spaces around =)
cat .env

# Should be:
AWS_ACCESS_KEY_ID=value  # ✅ Correct
# AWS_ACCESS_KEY_ID = value  # ❌ Wrong (spaces)
```

### Issue 4: Variables not updating

**Problem:** Old environment variables cached

**Solution:**
```bash
# Close terminal and open a new one
# Or restart the backend
./run_with_textract.sh
```

## 📊 Environment File Comparison

| File | Purpose | Commit to Git? | Contains Real Keys? |
|------|---------|----------------|---------------------|
| `.env` | Your actual credentials | ❌ NO | ✅ YES |
| `.env.example` | Template for others | ✅ YES | ❌ NO (placeholders) |
| `.gitignore` | Protects .env | ✅ YES | ❌ NO |

## 🎉 Benefits of This Setup

**Before:**
- ❌ Credentials exposed in scripts
- ❌ Risk of committing to git
- ❌ Hard to manage multiple environments
- ❌ Difficult to share safely

**After:**
- ✅ Credentials protected in `.env`
- ✅ Safe to commit code
- ✅ Easy environment management
- ✅ Simple for team collaboration

## 🔐 Rotating Credentials

If your credentials are exposed:

1. **Immediately revoke** old credentials in AWS/provider
2. **Generate new** credentials
3. **Update** `.env` file:
   ```bash
   nano .env
   # Update the exposed credentials
   ```
4. **Restart** backend:
   ```bash
   ./run_with_textract.sh
   ```

## 📚 Additional Resources

- [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [12-Factor App Config](https://12factor.net/config)
- [Environment Variables Guide](https://en.wikipedia.org/wiki/Environment_variable)

## ✅ Summary

**Your setup is now secure!**

- ✅ Credentials in `.env` (protected)
- ✅ Template in `.env.example` (shareable)
- ✅ One command to run: `./run_with_textract.sh`
- ✅ Safe to commit your code
- ✅ Easy to manage different environments

**Next steps:**
1. Keep `.env` secure and local
2. Share `.env.example` with your team
3. Run with: `./run_with_textract.sh`

🎉 **You're all set!**

