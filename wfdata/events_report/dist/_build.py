#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

disclaimer_text = f"""
&copy; 2025 Facility for Rare Isotope Beams, Michigan State University.
All Rights Reserved."""
# Last Updated: <span style='font-family:monospace'>{datetime.now().isoformat()}</span>"""


def build_page(input_file: str, output_file: str, title="MPS Fault Events",
               footer=disclaimer_text):
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            body_content = infile.read()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
              <style>
                header {{
                    position: fixed;
                    top: 0;
                    width: 100%;
                    background: white;
                    padding: 10px;
                    text-align: center;
                }}
                body {{
                    margin-top: 60px; /* Prevent content from being hidden under fixed header */
                }}
            </style>
        </head>
        <body>
            <header>
                <h1 style="text-align:center;font-family:monospace;">{title}</h1>
                <hr/>
            </header>
            {body_content}
            <footer>
                <p style="text-align:center;">{footer}</p>
            </footer>
        </body>
        </html>
        """

        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write(html_content)

        print(f"HTML page generated successfully: {output_file}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Example usage
    build_page("mps_faults.html", "output.html")

