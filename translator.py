import sys
from deep_translator import GoogleTranslator
import base64
import os
from PIL import Image
import io
import fitz  # PyMuPDF
import concurrent.futures
from functools import partial
import argparse

# --- Worker Function for Parallel Processing ---
def process_page_worker(page_index, pdf_path, language):
    """
    Processes a single page of a PDF: extracts and translates text, and extracts images.
    This function is designed to be called by a thread pool executor.
    """
    page_num = page_index + 1
    print(f"  -> Starting page {page_num}")

    try:
        # Each thread gets its own file handle and translator instance for thread safety
        translator = GoogleTranslator(source='auto', target=language)
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_index)

        # --- Text Extraction and Translation ---
        text = page.get_text("text")
        translated_page_html = ""
        if text:
            paragraphs = text.split('\n')
            translated_paragraphs = []
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            if paragraphs:
                try:
                    translated_batch = translator.translate_batch(paragraphs)
                    translated_paragraphs = [f"<p>{p}</p>" for p in translated_batch if p]
                except Exception as e:
                    print(f"    [Page {page_num}] Batch translation error. Trying single paragraphs. Error: {e}")
                    for p in paragraphs:
                        try:
                            translated_paragraphs.append(f"<p>{translator.translate(p)}</p>")
                        except Exception as trans_error:
                            print(f"      [Page {page_num}] Could not translate paragraph: {p[:30]}... Error: {trans_error}")
            translated_page_html = "\n".join(translated_paragraphs)

        # --- Image Extraction ---
        page_images_html = ""
        image_list = page.get_images(full=True)
        if image_list:
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # --- Start Filter ---
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    if pil_img.width < 100 or pil_img.height < 100:
                        continue
                    
                    page_width = page.rect.width
                    page_height = page.rect.height
                    if abs(pil_img.width - page_width) < 20 and abs(pil_img.height - page_height) < 20:
                        continue
                    # --- End Filter ---

                    image_ext = base_image["ext"]
                    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    content_type = f"image/{image_ext}"

                    page_images_html += f'''
                    <div class="image-container">
                        <img src="data:{content_type};base64,{img_base64}" />
                        <div class="image-caption">Image from page {page_num} (Object {img_index+1})</div>
                    </div>
                    '''
                except Exception:
                    pass
        
doc.close()
        print(f"  <- Finished page {page_num}")
        return {
            "page_num": page_num,
            "text_html": translated_page_html,
            "image_html": page_images_html,
        }
    except Exception as e:
        print(f"  !! Critical error while processing page {page_num}: {e}")
        return {
            "page_num": page_num,
            "text_html": f"<p>Error processing page {page_num}.</p>",
            "image_html": "",
        }


def translate_pdf_to_html(pdf_path, html_path, language='it'):
    """
    Translates a PDF, extracts images using PyMuPDF, and saves it as a styled HTML file.
    Uses a thread pool to process pages in parallel.
    """
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Translation</title>
        <style>
            body {{
                font-family: serif;
                line-height: 1.4;
                max-width: 800px;
                margin: 40px auto;
                padding: 0 20px;
                color: #333;
            }}
            h1 {{
                text-align: center;
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
                margin-bottom: 40px;
            }}
            .page-container {{
                border-bottom: 2px solid #ccc;
                padding-bottom: 30px;
                margin-bottom: 50px;
            }}
            .page-content p {{
                margin-bottom: 0.8em;
                text-align: justify;
            }}
            .page-number {{
                text-align: right;
                font-size: 0.9em;
                color: #999;
                border-top: 1px solid #eee;
                padding-top: 10px;
                margin-top: 30px;
            }}
            .all-images-container {{
                /* This container is just a wrapper */
            }}
            .image-container {{
                display: block; /* Each image on its own line */
                margin: 30px auto; /* Center the block and add vertical space */
                padding: 5px;
                border: 1px solid #ddd;
                max-width: 95%; /* A bit wider is fine if it's centered */
                box-sizing: border-box; /* Includes padding/border in the width */
            }}
            .image-container img {{
                display: block;
                margin: 0 auto;
                max-width: 100%;
                height: auto;
                max-height: 80vh;
            }}
            .image-caption {{
                font-size: 0.9em;
                color: #555;
                margin-top: 10px;
                text-align: center; /* Center the caption text */
            }}
        </style>
    </head>
    <body>
        <h1>Translated Content</h1>
        {all_pages_content}

        <hr style="margin: 60px 0;">
        <h1>Document Images</h1>
        <div class="all-images-container">
            {all_images_content}
        </div>
    </body>
    </html>
    '''

    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()

        print(f"Found {num_pages} pages. Starting parallel processing for language '{language}'...")

        worker = partial(process_page_worker, pdf_path=pdf_path, language=language)
        page_indices = range(num_pages)
        
        all_results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            all_results = list(executor.map(worker, page_indices))

        print("Parallel processing complete. Assembling HTML file...")

        all_results.sort(key=lambda r: r['page_num'])

        all_pages_html_content = ""
        all_images_html_content = ""
        for result in all_results:
            page_num = result["page_num"]
            translated_page_html = result["text_html"]
            page_images_html = result["image_html"]

            all_pages_html_content += f'''
            <div class="page-container">
                <div class="page-content">
                    {translated_page_html}
                </div>
                <div class="page-number">Page {page_num}</div>
            </div>
            '''
            all_images_html_content += page_images_html

        final_html = html_template.format(
            all_pages_content=all_pages_html_content,
            all_images_content=all_images_html_content
        )

        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(final_html)

        print(f"Translation complete! File saved to: {html_path}")

    except FileNotFoundError:
        print(f"Error: File '{pdf_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate a PDF file to a styled HTML document.')
    parser.add_argument('input_pdf', type=str, help='The path to the input PDF file.')
    parser.add_argument('output_html', type=str, help='The path for the output HTML file.')
    parser.add_argument('--lang', type=str, default='it', help='The target language for translation (e.g., "en", "fr", "es"). Defaults to "it" (Italian).')
    
    args = parser.parse_args()
    
    translate_pdf_to_html(args.input_pdf, args.output_html, args.lang)