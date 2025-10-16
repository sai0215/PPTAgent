# Quick Start: Designer + Standard Template Workflow

## 🎨 Your New Capability

**Merge two PPTX files to create the perfect presentation!**

## 🚀 In 3 Steps

### Step 1: Start Backend
```bash
./run_with_textract.sh
```

### Step 2: Upload Two PPTX Files

Open http://localhost:8080

**Designer Template (PPTX)** - Optional
- Your design/layout reference
- Professional template
- Corporate branding
- *Leave empty to use default*

**Standard Template (PPTX)** - Required  
- Your content presentation
- **Fonts will be preserved!**
- Images included
- Existing presentation to reformat

### Step 3: Generate!

Click "Next" and wait ~1-2 minutes

## 📊 What You Get

**Input:**
- Designer Template: `corporate_brand.pptx` (design)
- Standard Template: `my_content.pptx` (content + fonts)

**Output:**
- `final.pptx` with:
  - ✅ Layouts from Designer Template
  - ✅ Content from Standard Template
  - ✅ **Fonts from Standard Template**
  - ✅ Professional appearance

## 💡 Key Features

| Feature | Description |
|---------|-------------|
| **Font Preservation** | Arial, Calibri, etc. from Standard Template |
| **Font Size** | 12pt, 18pt, etc. from Standard Template |
| **Font Style** | Bold, italic, underline preserved |
| **Font Color** | RGB colors maintained |
| **Images** | Extracted and included |
| **Layout** | From Designer Template |

## 🎯 Use Cases

### Rebrand Presentations
**Before:** Old brand template  
**After:** New brand template  
**Fonts:** Preserved from original

### Standardize Design
**Before:** Many different designs  
**After:** Consistent corporate template  
**Fonts:** Keep your carefully chosen fonts

### Content Reuse
**Before:** Outdated design  
**After:** Modern professional template  
**Fonts:** Your content fonts maintained

## ⚡ Quick Example

```bash
# 1. Start
./run_with_textract.sh

# 2. Open browser
http://localhost:8080

# 3. Upload
Designer: corporate_template.pptx (or leave empty)
Standard: my_presentation.pptx

# 4. Generate
Click "Next" → Wait → Download!
```

## 🔍 What Happens Behind the Scenes

```
1. Designer Template Parsing
   → Analyzes layouts, extracts design patterns

2. Standard Template Parsing
   → Extracts content, preserves fonts
   
3. Content Analysis
   → Understands structure and hierarchy
   
4. PPT Generation
   → Merges design + content with fonts
   
5. Success!
   → Download your presentation
```

## 📁 File Requirements

### Designer Template (PPTX)
- ✅ Professional PowerPoint template
- ✅ Multiple slide layouts preferred
- ✅ Good design/branding
- ⚠️ Optional (uses default if not provided)

### Standard Template (PPTX)
- ✅ PowerPoint file with your content
- ✅ Any fonts you want preserved
- ✅ Images included in slides
- ⚠️ **Required**

## 💡 Tips for Best Results

### Designer Template:
- Use a well-designed professional template
- Ensure it has varied layouts (title, content, etc.)
- Include all layout types you need

### Standard Template:
- Use consistent fonts throughout
- Clear hierarchy (titles → subtitles → body)
- Good quality images
- Well-structured content

### Generation:
- Start with 3-5 slides to test
- Increase slides once satisfied
- Review and iterate

## ✅ Verification

### Check Designer Template Parsed
Look for logs:
```
INFO - Designer Template uploaded: my_design.pptx
INFO - Parsing Designer Template
```

### Check Standard Template Parsed
Look for logs:
```
INFO - Standard Template uploaded: my_content.pptx
INFO - Parsing Standard Template PPTX
INFO - Parsed 15 slides from Standard Template
```

### Check Fonts Extracted
Check the generated file:
```bash
cat runs/standard/<hash>/content.json | grep "font"
```

Should show font information!

## 🐛 Troubleshooting

**Issue:** "Standard Template is required"
→ Upload a PPTX in Standard Template field

**Issue:** Fonts not preserved
→ Check Standard Template has explicit font settings
→ Verify content.json has font information

**Issue:** Design not applied
→ Check Designer Template uploaded successfully
→ Verify it has multiple layouts

## 📚 Full Documentation

- [Complete Guide](./DESIGNER_STANDARD_TEMPLATE_GUIDE.md)
- [Implementation Details](./IMPLEMENTATION_COMPLETE.md)
- [Environment Setup](./ENV_SETUP_GUIDE.md)

## 🎉 Summary

**New Workflow:**
```
Designer Template (design) + Standard Template (content+fonts) = Perfect PPT
```

**Benefits:**
- ✅ Font preservation
- ✅ Design consistency  
- ✅ Content reuse
- ✅ Time savings
- ✅ Professional quality

**Ready to use!**

---

**Quick Command:**
```bash
./run_with_textract.sh
```

**Then open:** http://localhost:8080

🎨 **Create amazing presentations!**

