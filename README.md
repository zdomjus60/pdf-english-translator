# PDF Translator

A Python script to translate the text content of a PDF file and render it as an HTML document, preserving images.

## Features

- Extracts text and images from a PDF file.
- Translates text to a user-specified language (defaults to Italian) using Google Translate.
- Processes pages in parallel for improved speed (multithreading).
- Intelligently filters out full-page scans and small decorative images.
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
python3 translator.py <input.pdf> <output.html> [options]
```

### Arguments

-   `<input.pdf>`: (Required) The path to the PDF file you want to translate.
-   `<output.html>`: (Required) The name of the HTML file to be created.

### Options

-   `--lang <language_code>`: (Optional) The target language for the translation (e.g., `en`, `fr`, `es`). Defaults to `it` (Italian) if not provided.

### Examples

**Translate to Italian (default):**
```bash
python3 translator.py "my-document.pdf" "traduzione_it.html"
```

**Translate to English:**
```bash
python3 translator.py "my-document.pdf" "translation_en.html" --lang en
```

## Supported Languages

The script can translate to any language supported by Google Translate. The target language is specified with the `--lang` option, followed by an ISO 639-1 language code.

Here is a list of common languages:

| Language | Code |
|----------|------|
| English  | `en` |
| Italian  | `it` |
| French   | `fr` |
| Spanish  | `es` |
| German   | `de` |
| Portuguese| `pt` |
| Russian  | `ru` |
| Chinese (Simp.)| `zh-cn` |
| Japanese | `ja` |
| Arabic   | `ar` |

For a complete list of supported languages, please refer to the official [Google Cloud Translate documentation](https://cloud.google.com/translate/docs/languages).