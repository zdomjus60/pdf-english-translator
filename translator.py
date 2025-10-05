import sys
from deep_translator import GoogleTranslator
import base64
import os
from PIL import Image
import io
import fitz  # PyMuPDF
import concurrent.futures
from functools import partial

# --- Worker Function for Parallel Processing ---
def process_page_worker(page_index, pdf_path):
    """
    Processes a single page of a PDF: extracts and translates text, and extracts images.
    This function is designed to be called by a thread pool executor.
    """
    page_num = page_index + 1
    print(f"  -> Inizio elaborazione pagina {page_num}")

    try:
        # Each thread gets its own file handle and translator instance for thread safety
        translator = GoogleTranslator(source='auto', target='it')
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
                    print(f"    [Pagina {page_num}] Errore traduzione batch. Tento con paragrafi singoli. Errore: {e}")
                    for p in paragraphs:
                        try:
                            translated_paragraphs.append(f"<p>{translator.translate(p)}</p>")
                        except Exception as trans_error:
                            print(f"      [Pagina {page_num}] Impossibile tradurre paragrafo: {p[:30]}... Errore: {trans_error}")
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
                    # Load image into PIL to get dimensions
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    
                    # Filter 1: Small images
                    if pil_img.width < 100 or pil_img.height < 100:
                        print(f"      - Immagine {img_index+1} ignorata (troppo piccola).")
                        continue

                    # Filter 2: Full-page images
                    page_width = page.rect.width
                    page_height = page.rect.height
                    if abs(pil_img.width - page_width) < 20 and abs(pil_img.height - page_height) < 20:
                        print(f"      - Immagine {img_index+1} ignorata (dimensioni quasi identiche alla pagina).")
                        continue
                    # --- End Filter ---

                    image_ext = base_image["ext"]
                    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    content_type = f"image/{image_ext}"

                    page_images_html += f'''
                    <div class="image-container">
                        <img src="data:{content_type};base64,{img_base64}" />
                        <div class="image-caption">Immagine da pagina {page_num} (Oggetto {img_index+1})</div>
                    </div>
                    '''
                except Exception:
                    # Ignore errors on single image extraction
                    pass
        
        doc.close()
        print(f"  <- Fine elaborazione pagina {page_num}")
        return {
            "page_num": page_num,
            "text_html": translated_page_html,
            "image_html": page_images_html,
        }
    except Exception as e:
        print(f"  !! Errore critico durante l'elaborazione della pagina {page_num}: {e}")
        return {
            "page_num": page_num,
            "text_html": f"<p>Errore nell'elaborazione della pagina {page_num}.</p>",
            "image_html": "",
        }


def translate_pdf_to_html(pdf_path, html_path):
    """
    Translates a PDF, extracts images using PyMuPDF, and saves it as a styled HTML file.
    Uses a thread pool to process pages in parallel.
    """
    html_template = '''
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Traduzione PDF</title>
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
                /* New rule to adapt very tall images to the screen */
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
        <h1>Contenuto Tradotto</h1>
        {all_pages_content}

        <hr style="margin: 60px 0;">
        <h1>Immagini del Documento</h1>
        <div class="all-images-container">
            {all_images_content}
        </div>
    </body>
    </html>
    '''

    try:
        # Open the doc once to get page count
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()

        print(f"Trovate {num_pages} pagine. Avvio l'elaborazione parallela...")

        # Use a partial function to pass the static pdf_path to the worker
        worker = partial(process_page_worker, pdf_path=pdf_path)
        page_indices = range(num_pages)
        
        all_results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # map processes the pages and returns results in order
            all_results = list(executor.map(worker, page_indices))

        print("Elaborazione parallela completata. Assemblo il file HTML...")

        # Although map preserves order, sorting is a good safety measure
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
                <div class="page-number">Pagina {page_num}</div>
            </div>
            '''
            all_images_html_content += page_images_html

        # --- Assemble Final HTML ---
        final_html = html_template.format(
            all_pages_content=all_pages_html_content,
            all_images_content=all_images_html_content
        )

        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(final_html)

        print(f"Traduzione completata! Il file è stato salvato in: {html_path}")

    except FileNotFoundError:
        print(f"Errore: Il file '{pdf_path}' non è stato trovato.")
    except Exception as e:
        print(f"Si è verificato un errore imprevisto: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python translator.py <input.pdf> <output.html>")
    else:
        input_pdf = sys.argv[1]
        output_html = sys.argv[2]
        translate_pdf_to_html(input_pdf, output_html)
