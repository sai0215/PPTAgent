# Designer & Standard Template Guide

## 🎨 New Workflow Overview

PPTAgent now supports a **powerful new workflow** for creating presentations by combining two PPTX files:

1. **Designer Template (PPTX)** - Provides style, layout, and design
2. **Standard Template (PPTX)** - Provides content with fonts preserved

### Result: Perfect merge of professional design with your existing content!

## 📋 Terminology

| Old Name | New Name | Purpose |
|----------|----------|---------|
| Upload PPTX (template) | **Designer Template** | Style/layout reference |
| Upload PDF (content) | **Standard Template** | Content source (now PPTX) |

## 🔄 What Changed

### Before (Old Workflow)
```
PDF (content) + PPTX Template (design) → Generated PPT
```
- ❌ PDF parsing loses font information
- ❌ No control over fonts in generated slides
- ❌ Limited to PDF format for content

### After (New Workflow)
```
Standard Template PPTX (content + fonts) + Designer Template PPTX (design) → Generated PPT
```
- ✅ Preserves font names from Standard Template
- ✅ Preserves font sizes from Standard Template
- ✅ Preserves font styles (bold, italic, underline)
- ✅ Preserves font colors
- ✅ Better content extraction from PPTX

## 🎯 How It Works

### Step 1: Upload Designer Template (Optional)
**What it is:** A PPTX file with your desired design/layout

This provides:
- Slide layouts
- Color schemes
- Design elements
- Visual style

**If not provided:** Uses built-in default template

### Step 2: Upload Standard Template (Required)
**What it is:** A PPTX file with your content

This provides:
- Text content
- Font names (Arial, Calibri, etc.)
- Font sizes (11pt, 14pt, etc.)
- Font styles (bold, italic, underline)
- Font colors
- Images
- Tables

### Step 3: Generation
The system:
1. Analyzes Designer Template layouts
2. Extracts content + fonts from Standard Template
3. Generates new presentation with:
   - Layout/design from Designer Template
   - Content from Standard Template
   - **Fonts preserved from Standard Template**

## 🚀 Usage Guide

### Via WebUI

1. **Start the backend:**
   ```bash
   ./run_with_textract.sh
   ```

2. **Open the UI:**
   ```
   http://localhost:8080
   ```

3. **Upload files:**
   - **Designer Template (PPTX)**: Your design reference (optional)
   - **Standard Template (PPTX)**: Your content source (required)
   - **Number of Slides**: How many slides to generate

4. **Click "Next"** and wait for generation!

### Programmatically

```python
from pptagent.pptx_parser import parse_standard_template_pptx

# Parse Standard Template PPTX
content = await parse_standard_template_pptx(
    "standard_template.pptx",
    "output_folder"
)

# Content includes:
# - content.slides[0].title
# - content.slides[0].title_font (name, size, bold, etc.)
# - content.slides[0].text_blocks (with font info)
# - content.slides[0].images
```

## 📊 Standard Template Content Extraction

### What Gets Extracted

From each slide of Standard Template:

```python
SlideContent:
  - title: "Slide Title"
  - title_font:
      name: "Calibri"
      size: 32.0  # points
      bold: True
      italic: False
  - text_blocks:
      - TextBlock:
          runs:
            - TextRun:
                text: "Important point"
                font:
                  name: "Arial"
                  size: 18.0
                  bold: True
                  color_rgb: (255, 0, 0)
  - images: ["path/to/image1.png", ...]
```

### Font Preservation

**Preserved attributes:**
- ✅ Font name (Arial, Calibri, Times New Roman, etc.)
- ✅ Font size (in points)
- ✅ Bold style
- ✅ Italic style
- ✅ Underline style
- ✅ Font color (RGB values)

**Applied to:**
- ✅ Titles
- ✅ Body text
- ✅ Bullet points
- ✅ All text content

## 💡 Use Cases

### Use Case 1: Rebranding Presentations

**Scenario:** You have content in corporate template A, need to convert to template B

**Solution:**
- Designer Template: New brand template B
- Standard Template: Existing presentation with template A
- Result: Content moved to new brand template

### Use Case 2: Standardizing Fonts

**Scenario:** Multiple presentations with different fonts, need consistency

**Designer Template:** Corporate design template  
**Standard Template:** Any existing presentation  
**Result:** Consistent design with original content fonts preserved where appropriate

### Use Case 3: Content Reuse

**Scenario:** Reuse content from old presentations with new design

**Designer Template:** Modern, fresh design  
**Standard Template:** Old presentation with good content  
**Result:** Fresh-looking presentation with proven content

## 🔧 Technical Details

### Files Created/Modified

**New Files:**
- `pptagent/pptx_parser.py` - Standard Template PPTX parser
  - `parse_standard_template_pptx()` - Main parsing function
  - `FontInfo` - Font information dataclass
  - `TextRun` - Text with font info
  - `TextBlock` - Paragraph with runs
  - `SlideContent` - Complete slide content
  - `PPTXContent` - Full presentation content

**Modified Files:**
- `pptagent_ui/backend.py` - Updated upload and generation workflow
- `pptagent_ui/src/components/Upload.vue` - Updated UI labels and logic
- `.gitignore` - Added protection for runtime scripts

### API Changes

**Upload Endpoint `/api/upload`:**

**Before:**
```python
pptxFile: UploadFile  # Template
pdfFile: UploadFile   # Content
```

**After:**
```python
designerTemplate: UploadFile  # Designer (style)
standardTemplate: UploadFile  # Standard (content)
```

### Processing Stages

**Updated stages:**
1. "Designer Template Parsing" (was "PPT Parsing")
2. "Standard Template Parsing" (was "PDF Parsing")
3. "Content Analysis" (was "PPT Analysis")
4. "PPT Generation"
5. "Success!"

## 📝 Example Workflow

### Complete Example

**1. Prepare your files:**
```
designer_template.pptx - Modern design you want to use
standard_template.pptx - Your content presentation
```

**2. Upload via UI:**
- Designer Template: `designer_template.pptx`
- Standard Template: `standard_template.pptx`
- Number of Slides: 10

**3. System processes:**
```
✅ Designer Template Parsing - Analyzing layouts & design
✅ Standard Template Parsing - Extracting content & fonts
✅ Content Analysis - Understanding structure
✅ PPT Generation - Merging design + content
✅ Success! - Download your presentation
```

**4. Result:**
- Layout from Designer Template
- Content from Standard Template
- Fonts from Standard Template
- Professional, consistent output

## 🎨 Font Handling Details

### How Fonts Are Preserved

**From Standard Template:**
```
Slide 1:
  Title: "Product Launch" 
    → Font: Helvetica, 44pt, Bold
  
  Content: "Key features include..."
    → Font: Arial, 18pt, Regular
```

**Applied to Designer Template:**
```
Uses Designer Template layout/design
But applies:
  - Title fonts from Standard Template
  - Body fonts from Standard Template
  - Preserves emphasis (bold/italic/underline)
```

### Dominant Font Detection

For each text block:
- Analyzes all text runs
- Finds the longest run's font
- Uses that as the "dominant font" for the block
- Ensures consistency while preserving intent

## 🔍 Debugging & Verification

### Check Parsed Content

After parsing, check:
```bash
cat runs/standard/<hash>/content.json
```

You'll see:
```json
{
  "sections": [
    {
      "heading": "Slide 1",
      "metadata": {
        "title_font": {
          "name": "Calibri",
          "size": 32
        }
      },
      "content": [
        {
          "type": "text",
          "text": "Content here",
          "font": {
            "name": "Arial",
            "size": 18,
            "bold": false,
            "italic": false
          }
        }
      ]
    }
  ]
}
```

### Logs to Watch For

```
INFO - task created: 2025-10-16/xxx
INFO - Designer Template uploaded: my_design.pptx
INFO - Standard Template uploaded: my_content.pptx
INFO - Parsing Designer Template
INFO - Parsing Standard Template PPTX
INFO - Parsed 15 slides from Standard Template
INFO - Analyzing content structure
INFO - Generating presentation with Designer Template style and Standard Template content
INFO - Presentation generated successfully!
```

## 💡 Best Practices

### For Best Results

1. **Designer Template:**
   - Use a well-designed professional template
   - Ensure it has varied layouts
   - Include all layout types you need

2. **Standard Template:**
   - Use consistent fonts throughout
   - Clear hierarchy (titles, subtitles, body)
   - Good quality images
   - Well-structured content

3. **Number of Slides:**
   - Start with fewer slides (3-5) to test
   - Increase once you're happy with results
   - Match roughly to your content amount

### Common Scenarios

**Scenario 1: No Designer Template**
```
Designer: (not provided)
Standard: your_content.pptx
Result: Uses default template with your content & fonts
```

**Scenario 2: Both Templates**
```
Designer: corporate_brand.pptx
Standard: your_content.pptx
Result: Corporate design with your content & fonts
```

## 🎯 Benefits of This Approach

| Benefit | Description |
|---------|-------------|
| **Font Preservation** | Keeps your carefully chosen fonts |
| **Style Consistency** | Designer Template ensures uniform look |
| **Content Reuse** | Easily repurpose existing presentations |
| **Brand Compliance** | Apply corporate templates to any content |
| **Time Savings** | No manual copying/formatting |
| **Quality** | Professional design + your content |

## 🔧 Troubleshooting

### Issue: "Standard Template is required"

**Solution:** Upload a PPTX file in the Standard Template field

### Issue: Fonts not preserved

**Check:**
1. Standard Template has actual font variations
2. Check `content.json` to verify fonts were extracted
3. Ensure text has explicit font settings (not theme fonts)

### Issue: Designer Template not applied

**Check:**
1. Designer Template uploaded correctly
2. Check logs for "Designer Template uploaded"
3. Verify template has multiple layouts

## 🚀 Getting Started

### Quick Test

1. Create/use a simple PPTX with your content
2. Upload as Standard Template
3. Use default Designer Template (don't upload one)
4. Generate 3 slides
5. Check the result!

### Full Workflow

1. Prepare Designer Template (or use default)
2. Prepare Standard Template with your content
3. Upload both
4. Generate
5. Download and review
6. Adjust and regenerate as needed

## 📚 Related Documentation

- [Quick Start](./QUICK_START_TEXTRACT.md)
- [Environment Setup](./ENV_SETUP_GUIDE.md)
- [Credentials Security](./CREDENTIALS_SECURED.md)
- [Main Documentation](./DOC.md)

## ✅ Summary

**New Capability:**
- ✅ PPTX-to-PPTX workflow
- ✅ Font preservation
- ✅ Design + Content merging
- ✅ Professional results

**Key Features:**
- Designer Template for style
- Standard Template for content  
- Automatic font extraction
- Intelligent merging

**Benefits:**
- Saves time
- Maintains consistency
- Preserves formatting
- Professional quality

---

**Ready to try it?** 

1. `./run_with_textract.sh`
2. Go to http://localhost:8080
3. Upload your PPTX files
4. Generate!

🎉 **Enjoy your new Designer + Standard Template workflow!**

