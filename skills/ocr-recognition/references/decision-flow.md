# OCR Decision Flow

## Start Here

```
User needs OCR
     │
     ▼
System has tesseract?
     │
     ├─ YES → Use tesseract directly
     │
     └─ NO
          │
          ▼
     Have sudo/apt permission?
          │
          ├─ YES → apt install tesseract-ocr
          │         (optional: tesseract-ocr-chi-sim for Chinese)
          │
          └─ NO
               │
               ▼
          Use Docker: minidocks/tesseract:latest
```

## After Basic OCR Fails

```
OCR results poor?
     │
     ├─ NO → Done!
     │
     └─ YES
          │
          ▼
     Try image preprocessing
          │
          ├─ Success → Done!
          │
          └─ Still poor
               │
               ▼
          Is it a captcha?
               │
               ├─ YES → Use commercial solution
               │         (see commercial-solutions.md)
               │
               └─ NO
                    │
                    ▼
               Try: different PSM + whitelist + preprocessing
                    │
                    ▼
               Still poor? → Commercial API
```

## Preprocessing Decision

```
Image type           → Recommended method
─────────────────────────────────────────
Simple text          → No preprocessing needed
Noisy image          → Gaussian blur + threshold
Uneven lighting      → Adaptive threshold
Captcha with lines   → Morphology + contour filter
Blurry               → Sharpen kernel
```

## PSM Selection Guide

```
Content type              → PSM
────────────────────────────────
Page of text              → 3 (auto)
Single column             → 4
Single line               → 5
Single block (captcha)    → 6
Single word               → 7
Single character          → 8, 10
```

## Quick Commands Reference

```bash
# 1. System tesseract
tesseract image.png stdout --psm 6

# 2. Docker basic
docker run --rm -v $PWD:/img minidocks/tesseract:latest tesseract /img/image.png stdout

# 3. Docker with language
docker run --rm -v $PWD:/img -v /tmp/chi_sim.traineddata:/usr/share/tessdata/chi_sim.traineddata:ro \
  minidocks/tesseract:latest tesseract /img/image.png stdout -l chi_sim

# 4. Docker digits only
docker run --rm -v $PWD:/img -v /tmp/eng.traineddata:/usr/share/tessdata/eng.traineddata:ro \
  minidocks/tesseract:latest tesseract /img/image.png stdout --psm 6 -c tessedit_char_whitelist=0123456789
```
