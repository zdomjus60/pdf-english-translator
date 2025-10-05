# PDF Translator

A Python script to translate the text content of a PDF file and render it as an HTML document, preserving images.

## Features

- Extracts text and images from a PDF file.
- Translates text to a specified language (default: Italian) using Google Translate.
- Processes pages in parallel for improved speed (multithreading).
- Intelligently filters out full-page scans from the image gallery.
- Renders the output as a clean, readable HTML file with the translated text first, followed by a gallery of extracted images.

## Dependencies

The script relies on the following Python libraries:

- `deep-translator`
- `PyMuPDF`
- `Pillow`

You can install them using pip:
```bash
pip install deep-translator PyMuPDF Pillow
```

## Usage

Run the script from your terminal:

```bash
python3 translator.py <input.pdf> <output.html>
```

- `<input.pdf>`: The path to the PDF file you want to translate.
- `<output.html>`: The name of the HTML file to be created.

Example:
```bash
python3 translator.py "my-document.pdf" "traduzione.html"
```