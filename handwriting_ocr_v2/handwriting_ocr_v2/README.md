# Handwriting OCR (v2)

A simple beginner-friendly desktop app that extracts text from images of
handwritten (or printed) notes using OCR.

## Features
- Upload a JPG / PNG / JPEG image
- Preview the image inside the app
- Convert the image to grayscale (OpenCV) and run OCR (EasyOCR)
- View extracted text in a text box
- Save extracted text to a `.txt` file
- Clear everything and start fresh
- Simple, clean Tkinter interface (900x600)

## Project Files
- `main.py` – The GUI application (run this file to start the app)
- `ocr_helper.py` – Handles grayscale conversion and OCR text extraction
- `requirements.txt` – Python libraries needed to run the project

## Setup Instructions

1. Make sure you have Python 3.8+ installed.

2. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```
   (Note: the first time EasyOCR runs, it will download some model files —
   this requires an internet connection and may take a minute or two.)

3. Run the app:
   ```
   python main.py
   ```

## How to Use
1. Click **Upload Image** and select a JPG/PNG/JPEG file.
2. The image will appear in the preview panel.
3. Click **Extract Text** to run OCR on the image.
4. The extracted text will appear in the text box on the right.
5. Click **Save Text** to save the extracted text as a `.txt` file.
6. Click **Clear** to reset the app, or **Exit** to close it.

## Notes
- This project is intentionally kept simple for learning purposes.
- It does not include advanced preprocessing, translation, PDF export,
  databases, or cloud features — just straightforward image-to-text OCR.
