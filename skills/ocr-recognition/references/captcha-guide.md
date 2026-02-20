# Captcha Recognition Guide

## The Hard Truth

> **Tesseract is NOT suitable for high-interference captchas**
> 
> If the captcha has dense interference lines, overlapping characters, or distortion, free OCR tools will fail.

## When to Give Up on Tesseract

- Multiple intersecting干扰 lines
- Characters touching/overlapping
- Heavy distortion/rotation
- Noise dots throughout
- Complex backgrounds

## What to Try Before Giving Up

### 1. Aggressive Preprocessing

```python
import cv2
import numpy as np

img = cv2.imread('captcha.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Method 1: Heavy blur + threshold
blur = cv2.GaussianBlur(gray, (5, 5), 0)
_, binary = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY)

# Method 2: Otsu
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2OTSU)

#.THRESH_ Method 3: Adaptive
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)

# Method 4: Morphology (remove lines)
kernel = np.ones((2, 2), np.uint8)
morph = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

# Method 5: Remove small contours
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
mask = np.zeros_like(binary)
for cnt in contours:
    if cv2.contourArea(cnt) > 30:
        cv2.drawContours(mask, [cnt], -1, 255, -1)
```

### 2. Try Multiple PSM Modes

```bash
for psm in 3 4 5 6 8 10; do
  docker run --rm -v $PWD:/img minidocks/tesseract:latest \
    tesseract /img/captcha.png stdout --psm $psm \
    -c tessedit_char_whitelist=0123456789
done
```

### 3. Analyze Character Regions

```python
# If you know digit count, analyze each region
img = cv2.imread('captcha.png')
width = img.shape[1]
digit_count = 6
per_digit = width / digit_count

for i in range(digit_count):
    start = int(i * per_digit)
    end = int((i + 1) * per_digit)
    # Process each region separately
```

## When All Fails

Accept that free tools won't work. Options:

1. **Manual input** - User enters captcha
2. **Commercial solution** - See commercial-solutions.md
3. **Alternative login** - SMS login, OAuth, etc.

## Real-World Results

From testing on a 6-digit captcha with interference lines:

| Method | Accuracy |
|--------|----------|
| Raw Tesseract | ~10% |
| With preprocessing | ~30% |
| Multiple PSM voting | ~30% |
| Commercial API | >95% |

**Conclusion**: For production use, invest in commercial solution.
