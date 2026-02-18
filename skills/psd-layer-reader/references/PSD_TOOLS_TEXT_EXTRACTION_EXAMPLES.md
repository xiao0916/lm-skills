# Real-World psd-tools Text Layer Extraction Examples

## Summary
This document provides real-world code examples and patterns for extracting text layer properties from PSD files using `psd-tools`. Includes attribute names, file paths, and GitHub repositories.

---

## Core Attribute Access Patterns

### 1. TypeLayer Properties (Official psd-tools API)

**File**: `psd-tools/psd-tools` - `src/psd_tools/api/layers.py`  
**GitHub**: https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/layers.py  
**License**: MIT

#### TypeLayer Class Properties:

```python
from psd_tools import PSDImage

psd = PSDImage.open('document.psd')

# Iterate through text layers
for layer in psd.descendants():
    if layer.kind == 'type':  # TypeLayer
        # Primary text attributes:
        text_content = layer.text                    # str - actual text content
        engine_dict = layer.engine_dict              # dict - styling information
        resource_dict = layer.resource_dict          # dict - document resources (fonts, etc.)
        
        # Transform and warp:
        transform = layer.transform                  # tuple (xx, xy, yx, yy, tx, ty)
        warp = layer.warp                            # DescriptorBlock or None
```

**Key Attributes Accessed**:
- `layer.text` → string (text content)
- `layer.kind` → string ('type' for text layers)
- `layer.engine_dict` → dict (styling, font info)
- `layer.resource_dict` → dict (FontSet, font definitions)

---

### 2. Extracting Font Information from engine_dict

**File**: `psd-tools/psd-tools` - Official Documentation  
**URL**: https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.api.layers.html  

#### Pattern for Font & Color Extraction:

```python
if layer.kind == 'type':
    # Extract text
    text = layer.engine_dict['Editor']['Text'].value
    
    # Get font definitions
    fontset = layer.resource_dict['FontSet']
    
    # Get style runs (character styling)
    runlength = layer.engine_dict['StyleRun']['RunLengthArray']
    rundata = layer.engine_dict['StyleRun']['RunArray']
    
    # Iterate over styled text segments
    index = 0
    for length, style in zip(runlength, rundata):
        substring = text[index:index + length]
        stylesheet = style['StyleSheet']['StyleSheetData']
        
        # Extract individual properties:
        font_index = stylesheet['Font']                    # int - index into FontSet
        font_name = fontset[font_index]['Name']            # str - font name
        font_size = stylesheet['FontSize']                 # float - point size
        
        # Color information (RGBA):
        fill_color = stylesheet['FillColor']               # dict with 'Type' and 'Values'
        color_values = fill_color['Values']                # list [A, R, G, B]
        
        index += length
```

**Exact Attributes**:
| Attribute | Type | Path | Notes |
|-----------|------|------|-------|
| `text` | string | `layer.text` | Raw text content |
| `FontSize` | float | `engine_dict['StyleRun']['RunArray'][i]['StyleSheet']['StyleSheetData']['FontSize']` | Point size |
| `Font` | int | `engine_dict['StyleRun']['RunArray'][i]['StyleSheet']['StyleSheetData']['Font']` | Index into FontSet |
| `FillColor` | dict | `engine_dict['StyleRun']['RunArray'][i]['StyleSheet']['StyleSheetData']['FillColor']` | Color descriptor |
| `Values` | list | `FillColor['Values']` | [Alpha, Red, Green, Blue] as 0-1 range |

---

### 3. Real Implementation: py-psd-engineData

**GitHub Repository**: https://github.com/firstplacelabs/py-psd-engineData  
**License**: MIT  
**Description**: Extracts text, font type, font size, and color from Photoshop PSD files

#### Code Pattern (Legacy but functional):

```python
from psd_tools import PSDImage
from engineData import getFontAndColorDict

# Open PSD
psd = PSDImage.load('myPsdName.psd')

for layer in reversed(psd.layers):
    # Access raw engine data
    rawData = layer._tagged_blocks['TySh'][-1][-1][-1][-1]
    rawDataValue = rawData.value
    
    # Parse engine data structure
    propDict = {
        'FontSet': '',
        'Text': '',
        'FontSize': '',
        'A': '',  # Alpha (0-255 range)
        'R': '',  # Red
        'G': '',  # Green
        'B': ''   # Blue
    }
    
    getFontAndColorDict(propDict, rawDataValue)
    
    # Access extracted values
    text = propDict['Text']
    font = propDict['FontSet']
    size = propDict['FontSize']
    color = (propDict['R'], propDict['G'], propDict['B'])
```

**Accessed Attributes**:
- `layer._tagged_blocks['TySh']` → raw engine data block
- Text, Font, FontSize, Color values parsed from internal structure

---

### 4. Higher-Level Properties (All Layer Types)

**File**: `psd-tools/psd-tools` - `src/psd_tools/api/layers.py`  
**Location**: https://github.com/psd-tools/psd-tools/blob/main/src/psd_tools/api/layers.py

#### Properties Common to All Layers (including text):

```python
for layer in psd.descendants():
    # Positioning & sizing
    bbox = layer.bbox                          # tuple (left, top, right, bottom)
    width = layer.width                        # int
    height = layer.height                      # int
    left = layer.left                          # int - x coordinate
    top = layer.top                            # int - y coordinate
    
    # Visibility & opacity
    visible = layer.visible                    # bool
    opacity = layer.opacity                    # int (0-255)
    
    # Blending & clipping
    blend_mode = layer.blend_mode              # BlendMode enum
    clipping = layer.clipping                  # bool
    
    # Layer metadata
    name = layer.name                          # str
    layer_id = layer.layer_id                  # int
    kind = layer.kind                          # str ('type', 'pixel', 'group', etc.)
```

---

## Real-World Usages Found

### Example 1: ursina/texture_importer.py
**URL**: https://github.com/pokepetter/ursina/blob/master/ursina/texture_importer.py

```python
if application.development_mode and importlib.util.find_spec('psd_tools'):
    from psd_tools import PSDImage
    
    for folder in _folders:
        for filename in folder.glob('**/*.psd'):
            print('found uncompressed psd, compressing it...')
            compress_textures(name)
```
**Context**: Texture management with PSD support detection

---

### Example 2: ComfyUI_LayerStyle_Advance/py/loadpsd.py
**URL**: https://github.com/chflame163/ComfyUI_LayerStyle_Advance/blob/main/py/loadpsd.py

```python
from psd_tools import PSDImage
from psd_tools.api.layers import Layer

psd_image = PSDImage.open(psd_file_path)

# Layer iteration pattern
for layer in psd_image:
    if layer.kind == 'type':
        # Process text layer
        print(f"Text: {layer.text}")
```
**Context**: Layer extraction for ComfyUI node integration

---

### Example 3: Vtuber_Tutorial
**URL**: https://github.com/RimoChan/Vtuber_Tutorial/blob/master/3/虚境.py

```python
from psd_tools import PSDImage

def 提取图层(psd):
    所有图层 = []
    
    for layer in psd.descendants():
        if layer.kind == 'type':
            # Extract text layer data
            所有图层.append({
                'name': layer.name,
                'text': layer.text,
                'visible': layer.visible
            })
    
    return 所有图层
```
**Context**: Character rigging extraction for VTuber projects

---

## Font Size Unit Conversion Issue

**GitHub Issue**: https://github.com/psd-tools/psd-tools/issues/149

**Problem**: Font size in `engine_dict` is in pixels, but Photoshop displays in points.

**Conversion Formula**:
```python
# If document DPI = 300:
font_size_in_points = (font_size_in_pixels / document_dpi) * 72

# Example: 25 pixels @ 300 DPI = 6 points
font_size_pt = (25 / 300) * 72  # = 6.0
```

**Accessing DPI**:
```python
psd = PSDImage.open('file.psd')
# DPI info is in document resources, typically 72 or user-defined
dpi = 72  # Default assumption; actual value varies
```

---

## Summary of Exact Attribute Names

### TypeLayer-Specific:
| Attribute | Access Pattern | Type | Example Value |
|-----------|---|---|---|
| Text Content | `layer.text` | str | "Hello World" |
| Engine Dict | `layer.engine_dict` | dict | Complex nested structure |
| Font Size (pixels) | `engine_dict['StyleRun']['RunArray'][0]['StyleSheet']['StyleSheetData']['FontSize']` | float | 18.0 |
| Font Name | `resource_dict['FontSet'][font_index]['Name']` | str | "Helvetica" |
| Font Color (RGBA) | `engine_dict['StyleRun']['RunArray'][0]['StyleSheet']['StyleSheetData']['FillColor']['Values']` | list | [1.0, 0.85489, 0.1059, 0.23923] |
| Document Resources | `layer.document_resources` | dict | Font sets, color sets |
| Resource Dict | `layer.resource_dict` | dict | FontSet array |
| Transform Matrix | `layer.transform` | tuple (6 floats) | (xx, xy, yx, yy, tx, ty) |
| Warp Configuration | `layer.warp` | DescriptorBlock or None | Warp settings if present |

### Common to All Layers:
| Attribute | Type | Range |
|-----------|------|-------|
| `opacity` | int | 0-255 |
| `visible` | bool | True/False |
| `blend_mode` | BlendMode enum | NORMAL, SCREEN, etc. |
| `bbox` | tuple | (left, top, right, bottom) |

---

## References & Resources

1. **psd-tools Official Documentation**  
   https://psd-tools.readthedocs.io/en/latest/

2. **psd-tools GitHub Repository**  
   https://github.com/psd-tools/psd-tools  
   License: MIT

3. **py-psd-engineData Repository**  
   https://github.com/firstplacelabs/py-psd-engineData  
   Practical implementation for text extraction

4. **Stack Overflow Discussion**  
   https://stackoverflow.com/questions/37141958/parsing-photoshop-psd-to-get-font-size-of-layers

5. **Font Size Unit Issue**  
   https://github.com/psd-tools/psd-tools/issues/149

---

## Next Steps for psd_layers.py Extension

Based on findings, to extend `psd_layers.py` with text metadata:

1. **Check layer kind**: `if layer.kind == 'type':`
2. **Access text**: `layer.text`
3. **Parse styling**: `layer.engine_dict['StyleRun']['RunArray']` for per-substring styling
4. **Extract fonts**: `layer.resource_dict['FontSet']` with index lookup
5. **Get colors**: Nested in StyleSheetData under `FillColor['Values']`
6. **Handle size conversion**: Multiply by 72/DPI for point conversion (if needed)
7. **Store in JSON**: Flatten structure into flat object with prefixed keys (e.g., `"text_font_size"`, `"text_color_rgba"`)

