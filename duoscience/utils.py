# -*- coding: utf-8 -*-
"""
duoscience/utils.py

Utility functions for converting Markdown files to PDF with extended syntax support.
This module provides a function to convert Markdown files to PDF using the `markdown` library
and `pdfkit`, with support for various Markdown extensions such as tables, code highlighting,
admonitions, footnotes, and a table of contents. It also allows for custom CSS styling and
syntax highlighting using Pygments.

Author: Roman Fitzjalen | DuoScience
Date: 8 July 2025
© 2025 DuoScience. All rights reserved.
"""
from __future__ import annotations

import markdown
import pdfkit
import tempfile
import os
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

def convert_md_to_pdf(
    md_file_path: str,
    pdf_file_path: str,
    wkhtmltopdf_path: str,
    css_path: str | None = None,
    pygments_css_path: str | None = None,
    logo_path: str | None = "assets/duoscience-logo.png"
) -> None:
    """
    Converts a Markdown file to PDF with extended syntax support.

    :param md_file_path: Path to the source Markdown file.
    :param pdf_file_path: Path to save the resulting PDF file.
    :param wkhtmltopdf_path: Absolute path to the wkhtmltopdf executable.
    :param css_path: (Optional) Path to a custom CSS file for styling.
    :param pygments_css_path: (Optional) Path to a Pygments CSS file for code highlighting.
    :param logo_path: (Optional) Path to a logo image to embed at the top-left.
    :raises FileNotFoundError: If the Markdown or other asset files do not exist.
    :raises IOError: If there is an issue reading files or writing the PDF.
    :raises Exception: For any other unexpected errors during the conversion.
    :return: None
    """
    try:
        # 1. Read the Markdown file
        md_path = Path(md_file_path)
        if not md_path.exists():
            raise FileNotFoundError(f"Исходный файл не найден: {md_file_path}")
        
        logger.info(f"Reading Markdown file from {md_file_path}")
        with md_path.open('r', encoding='utf-8') as f:
            md_content = f.read()

        # 2. Convert to HTML with extensions
        logger.info("Converting Markdown to HTML with extensions.")
        html_body = markdown.markdown(
            md_content,
            extensions=[
                'tables', 'fenced_code', 'codehilite', 
                'admonition', 'footnotes', 'toc'
            ]
        )

        # 3. Build the complete HTML with embedded styles and logo
        user_css = ""
        if css_path and Path(css_path).exists():
            logger.info(f"Reading custom CSS from {css_path}")
            with open(css_path, 'r', encoding='utf-8') as f:
                user_css = f.read()

        pygments_css = ""
        if pygments_css_path and Path(pygments_css_path).exists():
            logger.info(f"Reading Pygments CSS from {pygments_css_path}")
            with open(pygments_css_path, 'r', encoding='utf-8') as f:
                pygments_css = f.read()
        
        logo_html_element = ""
        if logo_path and Path(logo_path).exists():
            logger.info(f"Embedding logo from: {logo_path}")
            logo_p = Path(logo_path)
            with logo_p.open("rb") as image_file:
                b64_logo = base64.b64encode(image_file.read()).decode('utf-8')
            
            mime_type = f"image/{logo_p.suffix.strip('.')}"
            logo_html_element = f'<img src="data:{mime_type};base64,{b64_logo}" class="logo">'

        html_page = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                /* --- Styles for the logo --- */
                .logo {{
                    max-height: 40px; /* Adjust size as needed */
                    margin-bottom: 20px; /* Space between logo and content */
                }}

                .logo + h1,
                .logo + h2,
                .logo + h3,
                .logo + p {{
                    margin-top: 0;
                }}

                /* --- Basic styles --- */
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 11pt; line-height: 1.6; }}
                @page {{ size: A4; margin: 25mm; }}
                h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 1em; table-layout: fixed; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; word-wrap: break-word; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                code:not(pre > code) {{ background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-size: 0.9em;}}
                blockquote {{ border-left: 4px solid #ddd; padding-left: 1em; color: #666; margin-left: 0; }}
                
                /* --- Custom user styles --- */
                {user_css}
                
                /* --- Pygments code highlighting styles --- */
                {pygments_css}
            </style>
        </head>
        <body>
            {logo_html_element}
            {html_body}
        </body>
        </html>
        """

        # 4. Write HTML to a temporary file and convert to PDF
        logger.info("Configuring pdfkit with wkhtmltopdf path.")
        cfg = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.html') as tmp_html_file:
            tmp_html_file.write(html_page)
            tmp_html_path = tmp_html_file.name
            logger.info(f"HTML content written to temporary file: {tmp_html_path}")

        logger.info(f"Generating PDF and saving to {pdf_file_path}")
        pdfkit.from_file(
            tmp_html_path,
            str(pdf_file_path),
            configuration=cfg,
            options={'encoding': 'UTF-8', 'enable-local-file-access': None}
        )
        
        os.unlink(tmp_html_path)
        logger.info(f"✅ File successfully saved: {pdf_file_path}")

    except FileNotFoundError as e:
        logger.error(f"❌ Error: {e}")
    except IOError as e:
        logger.error(f"❌ I/O Error: {e}. Make sure wkhtmltopdf is installed and the path is correct.")
    except Exception as e:
        logger.exception(f"❌ An unexpected error occurred: {e}")

# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    WKHTMLTOPDF_EXECUTABLE_PATH = r'/usr/local/bin/wkhtmltopdf'

    logger.info("Starting Markdown to PDF conversion example.")
    # For example: assets/duoscience-logo.png
    convert_md_to_pdf(
        md_file_path='tmp.md',
        pdf_file_path='output.pdf',
        wkhtmltopdf_path=WKHTMLTOPDF_EXECUTABLE_PATH,
        css_path='style.css',
        pygments_css_path='pygments.css',
        logo_path='assets/duoscience-logo.png'
    )
    logger.info("Example finished.")