#!/usr/bin/env python3
"""
OCR Image Preprocessing Script

Usage:
    python3 preprocess.py --input captcha.png --output processed.png --method otsu
    python3 preprocess.py --input image.png --output result.png --method adaptive --show
"""

import argparse
import cv2
import numpy as np
import sys


def preprocess_threshold(img, value=127):
    """Simple thresholding"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, value, 255, cv2.THRESH_BINARY)
    return binary


def preprocess_otsu(img):
    """Otsu's thresholding - automatic"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def preprocess_adaptive(img):
    """Adaptive thresholding - good for uneven lighting"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return binary


def preprocess_morphology(img):
    """Morphology-based - good for captcha with lines"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY)
    
    # Morphology operations
    kernel = np.ones((2, 2), np.uint8)
    result = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # Remove small contours
    contours, _ = cv2.findContours(result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(result)
    for cnt in contours:
        if cv2.contourArea(cnt) > 30:
            cv2.drawContours(mask, [cnt], -1, 255, -1)
    
    return mask


def preprocess_captcha(img):
    """Specialized captcha preprocessing"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Multiple preprocessing steps
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Try Otsu first
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphology to remove noise
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
    
    # Remove small areas
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(morph)
    for cnt in contours:
        if cv2.contourArea(cnt) > 50:
            cv2.drawContours(mask, [cnt], -1, 255, -1)
    
    return mask


def analyze_image(img):
    """Print image analysis info"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print(f"Size: {img.shape}")
    print(f"Gray range: {gray.min()} - {gray.max()}")
    
    dark = np.where(gray < 150)
    print(f"Dark pixels: {len(dark[0])}")


METHODS = {
    'threshold': preprocess_threshold,
    'otsu': preprocess_otsu,
    'adaptive': preprocess_adaptive,
    'morphology': preprocess_morphology,
    'captcha': preprocess_captcha,
}


def main():
    parser = argparse.ArgumentParser(description='OCR Image Preprocessing')
    parser.add_argument('--input', '-i', required=True, help='Input image path')
    parser.add_argument('--output', '-o', required=True, help='Output image path')
    parser.add_argument('--method', '-m', default='otsu', 
                       choices=list(METHODS.keys()),
                       help='Preprocessing method')
    parser.add_argument('--threshold', '-t', type=int, default=127,
                       help='Threshold value for threshold method')
    parser.add_argument('--show', action='store_true',
                       help='Show result in window')
    
    args = parser.parse_args()
    
    # Read image
    img = cv2.imread(args.input)
    if img is None:
        print(f"Error: Cannot read image {args.input}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Input: {args.input}")
    analyze_image(img)
    print(f"Method: {args.method}")
    
    # Process
    method_func = METHODS[args.method]
    if args.method == 'threshold':
        result = method_func(img, args.threshold)
    else:
        result = method_func(img)
    
    # Save
    cv2.imwrite(args.output, result)
    print(f"Output: {args.output}")
    
    if args.show:
        cv2.imshow('Original', img)
        cv2.imshow('Processed', result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
