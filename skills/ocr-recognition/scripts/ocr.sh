#!/bin/bash
#
# OCR Quick Command Wrapper
# Usage: ./ocr.sh image.png [options]
#

set -e

# Default values
IMAGE=""
OUTPUT=""
PSM=6
WHITELIST="0123456789"
LANGUAGE="eng"
PREPROCESS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <image> [options]"
    echo ""
    echo "Options:"
    echo "  -o, --output <file>   Output file (default: stdout)"
    echo "  -p, --psm <num>       PSM mode (default: 6)"
    echo "  -w, --whitelist <str> Character whitelist (default: digits)"
    echo "  -l, --lang <lang>     Language (default: eng)"
    echo "  --preprocess <method> Preprocessing method (otsu, adaptive, morphology)"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 screenshot.png                    # Recognize digits"
    echo "  $0 screenshot.png -o result.txt      # Save to file"
    echo "  $0 captcha.png -p 8                 # Use PSM 8"
    echo "  $0 image.png -w ABCD                 # Only ABCD"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -p|--psm)
            PSM="$2"
            shift 2
            ;;
        -w|--whitelist)
            WHITELIST="$2"
            shift 2
            ;;
        -l|--lang)
            LANGUAGE="$2"
            shift 2
            ;;
        --preprocess)
            PREPROCESS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
        *)
            IMAGE="$1"
            shift
            ;;
    esac
done

# Check required
if [ -z "$IMAGE" ]; then
    echo -e "${RED}Error: Image file required${NC}"
    usage
fi

if [ ! -f "$IMAGE" ]; then
    echo -e "${RED}Error: File not found: $IMAGE${NC}"
    exit 1
fi

# Check docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found${NC}"
    exit 1
fi

# Check traineddata - use directory approach
TESSDATA_DIR="/tmp/tessdata"
TRAINEDDATA="$TESSDATA_DIR/${LANGUAGE}.traineddata"

if [ ! -d "$TESSDATA_DIR" ]; then
    echo -e "${YELLOW}Creating tessdata directory...${NC}"
    mkdir -p "$TESSDATA_DIR"
fi

if [ ! -f "$TRAINEDDATA" ]; then
    echo -e "${YELLOW}Downloading $LANGUAGE traineddata...${NC}"
    wget -L -q -O "$TRAINEDDATA" "https://github.com/tesseract-ocr/tessdata/raw/main/${LANGUAGE}.traineddata"
fi

# Build docker command - use directory mapping
DOCKER_CMD="docker run --rm -v $(pwd):/output -v $TESSDATA_DIR:/usr/share/tessdata:ro minidocks/tesseract:latest"

# Preprocessing
if [ -n "$PREPROCESS" ]; then
    if ! python3 -c "import cv2" 2>/dev/null; then
        echo -e "${YELLOW}Warning: OpenCV not available, skipping preprocessing${NC}"
    else
        BASE=$(basename "$IMAGE" .png)
        PROCESSED="${BASE}_processed.png"
        python3 -c "
import cv2
import numpy as np
img = cv2.imread('$IMAGE')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
if '$PREPROCESS' == 'otsu':
    _, img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
elif '$PREPROCESS' == 'adaptive':
    img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
elif '$PREPROCESS' == 'morphology':
    _, img = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    kernel = np.ones((2,2), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
cv2.imwrite('$PROCESSED', img)
"
        IMAGE="$PROCESSED"
        echo -e "${GREEN}Preprocessed: $IMAGE${NC}"
    fi
fi

# Build tesseract command
CMD="$DOCKER_CMD tesseract /output/$IMAGE"
if [ -n "$OUTPUT" ]; then
    CMD="$CMD /output/$OUTPUT"
else
    CMD="$CMD stdout"
fi
CMD="$CMD --psm $PSM -c tessedit_char_whitelist=$WHITELIST -l $LANGUAGE"

# Run
echo -e "${GREEN}Running OCR...${NC}"
$CMD
