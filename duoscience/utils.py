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

import os
import re
import markdown
import pdfkit
import tempfile
import logging
import base64
from pathlib import Path
from urllib.parse import unquote
from bs4 import BeautifulSoup, NavigableString

URL_RE = re.compile(r'(https?://[^\s<>"\]]+)', re.IGNORECASE)
LIST_ITEM_RE = re.compile(r'^\s*(?:[-+*]|\d+\.)\s+')
LIST_BULLET_RE = re.compile(r'^(\s+)((?:[-+*]|\d+\.)\s+)')

# --- Regex for long amino acid sequences (see soft_wrap_unbreakables) ---
# Includes standard amino acids + commonly encountered special symbols B, Z, X, O, U, *
AA_RE = re.compile(r'(?<![A-Za-z])([ACDEFGHIKLMNPQRSTVWYBXZOU\*]{30,})(?![A-Za-z])')

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
            raise FileNotFoundError(f"Source file not found: {md_file_path}")
        
        logger.info(f"Reading Markdown file from {md_file_path}")
        with md_path.open('r', encoding='utf-8') as f:
            md_content = f.read()

        md_content = ensure_blank_line_before_lists(md_content)
        md_content = normalize_list_indentation(md_content)

        # 2. Convert to HTML with extensions
        logger.info("Converting Markdown to HTML with extensions.")
        html_body = markdown.markdown(
            md_content,
            extensions=[
                'tables', 'fenced_code', 'codehilite', 
                'admonition', 'footnotes', 'toc', 'sane_lists'
            ]
        )
        # Make links explicit to prevent wkhtmltopdf from "re-encoding" them
        html_body = linkify_preserving_percents(html_body)
        # HACK for wkhtmltopdf: remove existing %XX so it can re-encode them itself
        html_body = url_decode_anchor_hrefs(html_body)

        # --- Soft wraps for "unbreakable" sequences (AA, long words, etc.) ---
        # Insert U+200B every N characters in code/paragraps/table cells, so even old wkhtmltopdf can correctly wrap lines.
        html_body = soft_wrap_unbreakables(html_body, chunk=10)

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

            /* --- Wrapping long lines inside code/preformatted text blocks --- */
            /* Enable wrapping and add compatible fallbacks for older wkhtmltopdf engines */
            pre,
            .codehilite pre,
            .highlight pre {{
                white-space: pre-wrap !important;     /* preserves formatting but allows wrapping */
                overflow-wrap: anywhere !important;   /* modern option */
                word-wrap: break-word !important;     /* older alias */
                word-break: break-all;                /* hard fallback for very old engines */
            }}
            pre code {{
                white-space: inherit !important;      /* inherit behavior from pre */
            }}
            /* Ensure wrapping outside code blocks (tables/lists/paragraphs) as well */
            td, th, p, li {{
                word-wrap: break-word;
                overflow-wrap: anywhere;
            }}

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
            # NOTE: single braces — pass a dict, not a set. None/'' are typical for boolean flags in pdfkit.
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

def linkify_preserving_percents(html: str) -> str:
    """
    Replaces "bare" URLs in HTML with <a href="...">...</a>, preserving % 
    and not touching existing <a> tags or the content of <code>/<pre>/<script>/<style>.
    """
    soup = BeautifulSoup(html, "html.parser")
    skip_parents = {"a", "code", "pre", "script", "style"}

    for node in list(soup.descendants):
        if isinstance(node, NavigableString):
            parent = node.parent
            if not parent or parent.name in skip_parents:
                continue

            text = str(node)
            parts = []
            last = 0
            changed = False

            for m in URL_RE.finditer(text):
                url = m.group(1)
                parts.append(text[last:m.start()])
                a = soup.new_tag("a")
                a["href"] = url
                a.string = url
                parts.append(a)
                last = m.end()
                changed = True

            if changed:
                parts.append(text[last:])
                node.replace_with(*parts)

    return str(soup)

def url_decode_anchor_hrefs(html: str) -> str:
    """
    Decodes the href attribute of all <a> tags once, so that wkhtmltopdf can re-encode them later
    (avoiding %25 issues). Does not modify the link text, only the href attribute.
    """
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        old = a["href"]
        new = unquote(old)  # IMPORTANT: use unquote, NOT unquote_plus
        if new != old:
            a["href"] = new
    return str(soup)

def _insert_zwsp_every(s: str, n: int) -> str:
    """
    Inserts a zero-width space (U+200B) every n characters in the string s.
    This is invisible in rendering but allows the engine to break the line.
    """
    return "\u200b".join(s[i:i+n] for i in range(0, len(s), n))

def soft_wrap_unbreakables(html: str, chunk: int = 10) -> str:
    """
    Inserts soft breaks into long AA sequences within elements
    code/pre/p/li/td/th. Links <a> and their content are not modified.
    
    The length threshold is defined by AA_RE (>=30). The chunk parameter controls the step for inserting U+200B.
    """
    soup = BeautifulSoup(html, "html.parser")
    targets = soup.select("code, pre, p, li, td, th")
    for node in targets:
        # Skip links and nodes inside links to avoid breaking URLs
        if node.name == "a" or node.find_parent("a"):
            continue
        # Iterate over text nodes
        for t in list(node.strings):
            txt = str(t)
            if AA_RE.search(txt):
                new_txt = AA_RE.sub(lambda m: _insert_zwsp_every(m.group(1), chunk), txt)
                if new_txt != txt:
                    t.replace_with(new_txt)
    return str(soup)

def ensure_blank_line_before_lists(md_text: str) -> str:
    """
    Inserts a blank line ONLY before the start of a list if it follows regular text.
    Does not modify fenced code blocks ```/~~~ and does not add blank lines before nested list items.
    """
    lines = md_text.splitlines()
    out = []
    in_fence = False
    fence_re = re.compile(r'^\s*(```|~~~)')  # start/end of fenced code block

    def is_list_line(s: str) -> bool:
        return bool(LIST_ITEM_RE.match(s))

    for line in lines:
        # toggle fenced code blocks
        if fence_re.match(line):
            in_fence = not in_fence
            out.append(line)
            continue

        if not in_fence and is_list_line(line):
            # Find the previous non-empty line
            j = len(out) - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            prev_nonempty = out[j] if j >= 0 else ""

            # if the previous line is NOT a list item and not empty => insert a blank line
            # (i.e., the list starts after regular text or a heading)
            if prev_nonempty and not is_list_line(prev_nonempty):
                out.append("")
        out.append(line)

    return "\n".join(out)

def normalize_list_indentation(md_text: str) -> str:
    """
    Rounds leading spaces of list items to the nearest greater multiple of 4.
    Works only outside fenced code blocks (``` / ~~~). Does not modify text lines.
    """
    lines = md_text.splitlines()
    out = []
    in_fence = False
    fence_re = re.compile(r'^\s*(```|~~~)')

    for line in lines:
        if fence_re.match(line):
            in_fence = not in_fence
            out.append(line)
            continue

        if not in_fence:
            m = LIST_BULLET_RE.match(line)
            if m:
                indent, marker = m.groups()
                n = len(indent)
                # округляем вверх до кратного 4
                new_n = ((n + 3) // 4) * 4
                if new_n != n:
                    line = " " * new_n + line[n:]

        out.append(line)

    return "\n".join(out)

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

    # --- Additional example matching your local run ---
    logger.info("Starting Markdown to PDF conversion (local/markdown.md).")
    convert_md_to_pdf(
        md_file_path="local/markdown.md",
        pdf_file_path="local/markdown.pdf",
        wkhtmltopdf_path=WKHTMLTOPDF_EXECUTABLE_PATH
    )
    logger.info("Second example finished.")
