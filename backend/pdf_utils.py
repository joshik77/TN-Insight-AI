import gc

import pymupdf
import pytesseract

from PIL import Image


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


MIN_TEXT_LENGTH = 25

OCR_SCALE = 1.0

MAX_OCR_PAGES = 10

MAX_TEXT_PER_PAGE = 12000


def clean_text(text):

    if not text:
        return ""

    text = text.strip()

    if len(text) > MAX_TEXT_PER_PAGE:
        text = text[:MAX_TEXT_PER_PAGE]

    return text


def is_readable_text(text):

    return (
        text is not None
        and len(text.strip()) >= MIN_TEXT_LENGTH
    )


def extract_with_pymupdf(file_bytes):

    print(
        "Trying lightweight PyMuPDF extraction...",
        flush=True
    )

    pages = []

    document = None

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        )

        total_pages = len(document)

        print(
            "Total PDF pages:",
            total_pages,
            flush=True
        )

        for page_number in range(
            total_pages
        ):

            page = document.load_page(
                page_number
            )

            try:

                text = clean_text(
                    page.get_text(
                        "text"
                    )
                )

                pages.append({
                    "page":
                        page_number + 1,
                    "text":
                        text
                })

            finally:

                del page

            if (
                (page_number + 1) % 10
                == 0
            ):

                gc.collect()

        return pages

    finally:

        if document is not None:

            try:
                document.close()

            except Exception:
                pass

        gc.collect()


def ocr_single_page(page):

    pixmap = None
    image = None

    try:

        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                OCR_SCALE,
                OCR_SCALE
            ),
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            (
                pixmap.width,
                pixmap.height
            ),
            pixmap.samples
        )

        try:

            text = (
                pytesseract
                .image_to_string(
                    image,
                    lang="eng+tam",
                    config="--psm 6"
                )
            )

        except Exception as error:

            print(
                "Tamil OCR unavailable. "
                "Trying English OCR:",
                error,
                flush=True
            )

            try:

                text = (
                    pytesseract
                    .image_to_string(
                        image,
                        lang="eng",
                        config="--psm 6"
                    )
                )

            except Exception as error:

                print(
                    "OCR unavailable:",
                    error,
                    flush=True
                )

                return ""

        return clean_text(
            text
        )

    finally:

        if image is not None:

            try:
                image.close()

            except Exception:
                pass

        if pixmap is not None:
            del pixmap

        gc.collect()


def extract_missing_pages_with_ocr(
    file_bytes,
    pages
):

    missing_page_numbers = [
        page["page"]
        for page in pages
        if not is_readable_text(
            page["text"]
        )
    ]

    if not missing_page_numbers:

        print(
            "No OCR required.",
            flush=True
        )

        return pages

    print(
        "Pages requiring OCR:",
        missing_page_numbers,
        flush=True
    )

    if (
        len(missing_page_numbers)
        > MAX_OCR_PAGES
    ):

        print(
            "Too many pages require OCR. "
            f"Only the first {MAX_OCR_PAGES} "
            "pages will be OCR processed "
            "to protect server memory.",
            flush=True
        )

        missing_page_numbers = (
            missing_page_numbers[
                :MAX_OCR_PAGES
            ]
        )

    document = None

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        )

        for page_number in (
            missing_page_numbers
        ):

            print(
                f"OCR processing page "
                f"{page_number}...",
                flush=True
            )

            page = document.load_page(
                page_number - 1
            )

            try:

                text = ocr_single_page(
                    page
                )

                if text:

                    pages[
                        page_number - 1
                    ]["text"] = text

            finally:

                del page

            gc.collect()

        return pages

    finally:

        if document is not None:

            try:
                document.close()

            except Exception:
                pass

        gc.collect()


def count_readable_pages(pages):

    return sum(
        1
        for page in pages
        if is_readable_text(
            page["text"]
        )
    )


def extract_pdf_text(file_bytes):

    print(
        "Starting PDF extraction...",
        flush=True
    )

    try:

        pages = extract_with_pymupdf(
            file_bytes
        )

        if not pages:

            print(
                "PDF contains no pages.",
                flush=True
            )

            return []

        readable_pages = (
            count_readable_pages(
                pages
            )
        )

        print(
            "PyMuPDF readable pages:",
            readable_pages,
            "/",
            len(pages),
            flush=True
        )

        if readable_pages == len(
            pages
        ):

            print(
                "All pages extracted "
                "successfully using PyMuPDF.",
                flush=True
            )

            return pages

        print(
            "Some pages contain little "
            "or no embedded text.",
            flush=True
        )

        pages = (
            extract_missing_pages_with_ocr(
                file_bytes,
                pages
            )
        )

        final_readable_pages = (
            count_readable_pages(
                pages
            )
        )

        print(
            "Final readable pages:",
            final_readable_pages,
            "/",
            len(pages),
            flush=True
        )

        return pages

    except Exception as error:

        print(
            "PDF EXTRACTION ERROR:",
            error,
            flush=True
        )

        return []

    finally:

        gc.collect()