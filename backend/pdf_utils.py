import io

import pymupdf
import pdfplumber
import pytesseract

from PIL import Image


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


MIN_TEXT_LENGTH = 25
OCR_SCALE = 1.2


def clean_text(text):

    if not text:
        return ""

    return text.strip()


def is_readable_text(text):

    return (
        text is not None
        and len(text.strip()) >= MIN_TEXT_LENGTH
    )


def extract_with_pymupdf(file_bytes):

    print(
        "Trying PyMuPDF extraction..."
    )

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        text = clean_text(
            page.get_text("text")
        )

        pages.append({
            "page": page_number,
            "text": text
        })

    document.close()

    return pages


def extract_with_pdfplumber(file_bytes):

    print(
        "Trying pdfplumber extraction..."
    )

    pages = []

    pdf_stream = io.BytesIO(
        file_bytes
    )

    with pdfplumber.open(
        pdf_stream
    ) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            text = clean_text(
                page.extract_text()
            )

            pages.append({
                "page": page_number,
                "text": text
            })

    return pages


def ocr_single_page(page):

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(
            OCR_SCALE,
            OCR_SCALE
        ),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [
            pixmap.width,
            pixmap.height
        ],
        pixmap.samples
    )

    try:

        text = pytesseract.image_to_string(
            image,
            lang="eng+tam",
            config="--psm 6"
        )

    except Exception:

        print(
            "Tamil OCR unavailable. Falling back to English OCR."
        )

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 6"
        )

    return clean_text(
        text
    )


def extract_with_ocr(
    file_bytes,
    existing_pages=None
):

    print(
        "Starting OCR extraction..."
    )

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        existing_text = ""

        if (
            existing_pages
            and page_number <= len(existing_pages)
        ):

            existing_text = (
                existing_pages[
                    page_number - 1
                ]
                .get(
                    "text",
                    ""
                )
            )

        if is_readable_text(
            existing_text
        ):

            print(
                f"Page {page_number}: text already available, skipping OCR."
            )

            pages.append({
                "page": page_number,
                "text": existing_text
            })

            continue

        print(
            f"OCR processing page {page_number}..."
        )

        text = ocr_single_page(
            page
        )

        pages.append({
            "page": page_number,
            "text": text
        })

    document.close()

    return pages


def count_readable_pages(pages):

    return sum(
        1
        for page in pages
        if is_readable_text(
            page["text"]
        )
    )


def merge_page_results(
    primary_pages,
    fallback_pages
):

    merged_pages = []

    max_pages = max(
        len(primary_pages),
        len(fallback_pages)
    )

    for index in range(
        max_pages
    ):

        primary_text = ""

        fallback_text = ""


        if index < len(
            primary_pages
        ):

            primary_text = (
                primary_pages[index]
                .get(
                    "text",
                    ""
                )
            )


        if index < len(
            fallback_pages
        ):

            fallback_text = (
                fallback_pages[index]
                .get(
                    "text",
                    ""
                )
            )


        if is_readable_text(
            primary_text
        ):

            final_text = primary_text

        else:

            final_text = fallback_text


        merged_pages.append({
            "page": index + 1,
            "text": final_text
        })


    return merged_pages


def extract_pdf_text(file_bytes):

    pymupdf_pages = extract_with_pymupdf(
        file_bytes
    )

    pymupdf_readable = count_readable_pages(
        pymupdf_pages
    )

    print(
        "PyMuPDF readable pages:",
        pymupdf_readable
    )


    if (
        pymupdf_readable
        == len(pymupdf_pages)
        and pymupdf_readable > 0
    ):

        print(
            "All pages extracted successfully using PyMuPDF."
        )

        return pymupdf_pages


    pdfplumber_pages = extract_with_pdfplumber(
        file_bytes
    )

    pdfplumber_readable = count_readable_pages(
        pdfplumber_pages
    )

    print(
        "pdfplumber readable pages:",
        pdfplumber_readable
    )


    merged_pages = merge_page_results(
        pymupdf_pages,
        pdfplumber_pages
    )


    merged_readable = count_readable_pages(
        merged_pages
    )

    print(
        "Readable pages after normal extraction:",
        merged_readable
    )


    if (
        merged_readable
        == len(merged_pages)
        and merged_readable > 0
    ):

        print(
            "All pages extracted without OCR."
        )

        return merged_pages


    print(
        "Some pages still require OCR."
    )


    final_pages = extract_with_ocr(
        file_bytes,
        existing_pages=merged_pages
    )


    final_readable = count_readable_pages(
        final_pages
    )

    print(
        "Final readable pages:",
        final_readable,
        "/",
        len(final_pages)
    )


    return final_pages