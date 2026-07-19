"""
ocr_helper.py
--------------
This file contains simple helper functions for the Handwriting OCR project.

It handles:
1. Converting an image to grayscale using OpenCV.
2. Running EasyOCR on the image to extract handwritten/printed text.

Keeping this logic in a separate file makes main.py (the GUI file)
easier to read and understand.
"""

import cv2          # OpenCV - used for basic image processing
import easyocr       # EasyOCR - used for extracting text from images


# We create the EasyOCR reader ONCE (not every time we scan an image).
# Creating it repeatedly is slow, so we do it a single time here and reuse it.
# 'en' means we are reading English text.
# gpu=False makes sure it works even without a graphics card.
reader = easyocr.Reader(['en'], gpu=False)


def convert_to_grayscale(image_path):
    """
    Reads an image from disk and converts it to grayscale using OpenCV.

    Parameters:
        image_path (str): The full path to the image file.

    Returns:
        A grayscale OpenCV image (as a NumPy array).
    """

    # Read the image from the given file path
    image = cv2.imread(image_path)

    # Convert the image from color (BGR) to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return gray_image


def extract_text_from_image(image_path):
    """
    Extracts text from an image using EasyOCR.

    Steps:
    1. Convert the image to grayscale (simple preprocessing).
    2. Pass the grayscale image to EasyOCR.
    3. Combine all detected text pieces into one final string.

    Parameters:
        image_path (str): The full path to the image file.

    Returns:
        str: The extracted text, or an empty string if nothing was found.
    """

    # Step 1: Convert image to grayscale for cleaner OCR results
    gray_image = convert_to_grayscale(image_path)

    # Step 2: Run EasyOCR on the grayscale image
    # readtext() returns a list of results like:
    # [ (bounding_box, "detected text", confidence_score), ... ]
    results = reader.readtext(gray_image)

    # Step 3: Extract just the text portion from each result
    extracted_lines = []
    for (bounding_box, text, confidence) in results:
        extracted_lines.append(text)

    # Join all the detected lines into a single block of text
    final_text = "\n".join(extracted_lines)

    return final_text
