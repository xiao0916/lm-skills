# Commercial OCR Solutions

When free tools (Tesseract) don't work well, consider these alternatives.

## Captcha Solving Services

| Service | Type | Price | Accuracy |
|---------|------|-------|----------|
| 超级鹰 | API | ¥1/1000次 | >95% |
| 云打码 | API | ¥0.5/100次 | >95% |
| 打码兔 | API | ¥1/1000次 | >95% |

### 超级鹰 API Example

```python
import requests

def recognize_captcha(image_path, username, password, app_id, app_key):
    """超级鹰打码API"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    base64_image = base64.b64encode(image_data).decode()
    
    data = {
        'username': username,
        'password': password,
        'codetype': 1902,  # 4位数字字母混合
        'appid': app_id,
        'appkey': app_key,
        'base64': base64_image,
    }
    
    response = requests.post('http://api.chaojiying.net/Upload/ProcessingImages.cgi', data=data)
    result = response.json()
    
    if result['err_no'] == 0:
        return result['pic_str']  # 识别结果
    else:
        raise Exception(f"Error: {result['err_msg']}")
```

## General OCR APIs

| Service | Free Tier | Price | Best For |
|---------|-----------|-------|----------|
| 腾讯云 OCR | 1000次/月 | ¥1/1000次 | General text |
| 阿里云 OCR | 500次/月 | ¥1.5/1000次 | General text |
| Google Vision | 1000次/月 | $1.5/1000次 | High accuracy |
| AWS Textract | 100页/月 | $1.5/1000次 | Documents |

### 腾讯云 OCR Example

```python
from tencentcloud.ocr.v20181119 import ocr_client
from tencentcloud.common import credential

cred = credential.Credential("secret_id", "secret_key")
client = ocr_client.OcrClient(cred, "ap-guangzhou")

req = GeneralFastOCRRequest()
req.ImageUrl = "https://example.com/image.png"

resp = client.GeneralFastOCR(req)
for line in resp.TextDetections:
    print(line.DetectedText)
```

## Self-Hosted Options

### OCR Server with Tesseract

```yaml
# docker-compose.yml
services:
  ocr:
    image: minidocks/tesseract
    volumes:
      - ./images:/images
    command: tesseract /images/input.png stdout --psm 6
```

### PaddleOCR (Better than Tesseract)

```bash
# Install
pip install paddlepaddle paddleocr

# Use
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')
result = ocr.ocr('image.png', cls=True)
```

## Decision Guide

| Scenario | Recommendation |
|----------|----------------|
| Simple screenshot | Tesseract (free) |
| Clean document | Tesseract + preprocessing |
| Poor quality scan | PaddleOCR |
| High-volume captcha | 打码平台 API |
| Production OCR | 腾讯云/阿里云 |
| Highest accuracy | Google Vision |

## Cost Comparison (Monthly)

| Solution | Volume | Cost |
|----------|--------|------|
| Tesseract (self) | Unlimited | $0 (compute only) |
| PaddleOCR | Unlimited | $0 (compute only) |
| 打码平台 | 10,000次 | ~¥100 |
| 腾讯云 OCR | 10,000次 | ~¥10 |
| Google Vision | 10,000次 | ~$15 |
