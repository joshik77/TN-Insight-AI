import gc
import os
import shutil

import pymupdf
import pytesseract

from PIL import Image


MIN_TEXT_LENGTH = 25

OCR_SCALE = 1.0

MAX_OCR_PAGES = 3

MAX_TEXT_PER_PAGE = 12000


def configure_tesseract():

    custom_path = os.getenv(
        "TESSERACT_CMD"
    )

    if (
        custom_path
        and os.path.exists(custom_path)
    ):

        pytesseract.pytesseract.tesseract_cmd = (
            custom_path
        )

        print(
            "Using Tesseract from environment:",
            custom_path,
            flush=True
        )

        return True


    detected_path = shutil.which(
        "tesseract"
    )

    if detected_path:

        pytesseract.pytesseract.tesseract_cmd = (
            detected_path
        )

        print(
            "Tesseract detected:",
            detected_path,
            flush=True
        )

        return True


    if os.name == "nt":

        windows_paths = [

            r"C:\Program Files\Tesseract-OCR\tesseract.exe",

            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

        ]

        for path in windows_paths:

            if os.path.exists(path):

                pytesseract.pytesseract.tesseract_cmd = (
                    path
                )

                print(
                    "Tesseract detected:",
                    path,
                    flush=True
                )

                return True


    print(
        "WARNING: Tesseract OCR is not installed "
        "or could not be found.",
        flush=True
    )

    return False


TESSERACT_AVAILABLE = (
    configure_tesseract()
)


def clean_text(text):

    if not text:

        return ""

    text = text.strip()

    if (
        len(text)
        > MAX_TEXT_PER_PAGE
    ):

        text = text[
            :MAX_TEXT_PER_PAGE
        ]

    return text


def is_readable_text(text):

    return (
        text is not None
        and len(
            text.strip()
        ) >= MIN_TEXT_LENGTH
    )


def extract_with_pymupdf(
    file_bytes
):

    print(
        "Trying lightweight "
        "PyMuPDF extraction...",
        flush=True
    )

    pages = []

    document = None

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        )

        total_pages = len(
            document
        )

        print(
            "Total PDF pages:",
            total_pages,
            flush=True
        )

        for page_number in range(
            total_pages
        ):

            page = (
                document.load_page(
                    page_number
                )
            )

            try:

                text = clean_text(
                    page.get_text(
                        "text"
                    )
                )

                pages.append(
                    {
                        "page":
                            page_number + 1,

                        "text":
                            text
                    }
                )

            except Exception as error:

                print(
                    "Text extraction failed "
                    f"for page "
                    f"{page_number + 1}:",
                    error,
                    flush=True
                )

                pages.append(
                    {
                        "page":
                            page_number + 1,

                        "text":
                            ""
                    }
                )

            finally:

                del page


            if (
                (page_number + 1)
                % 10
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


def get_available_ocr_language():

    if not TESSERACT_AVAILABLE:

        return None


    try:

        languages = (
            pytesseract.get_languages(
                config=""
            )
        )

        print(
            "Available OCR languages:",
            languages,
            flush=True
        )


        has_english = (
            "eng" in languages
        )

        has_tamil = (
            "tam" in languages
        )


        if (
            has_english
            and has_tamil
        ):

            return "eng+tam"


        if has_english:

            return "eng"


        if has_tamil:

            return "tam"


        return None


    except Exception as error:

        print(
            "Unable to detect OCR "
            "languages:",
            error,
            flush=True
        )

        return "eng"


OCR_LANGUAGE = os.getenv(
    "OCR_LANGUAGE",
    "eng"
).strip()

if OCR_LANGUAGE not in {
    "eng",
    "tam",
    "eng+tam"
}:
    OCR_LANGUAGE = (
        get_available_ocr_language()
        or "eng"
    )

print(
    "Selected OCR language:",
    OCR_LANGUAGE,
    flush=True
)


def ocr_single_page(page):

    if not TESSERACT_AVAILABLE:

        print(
            "OCR skipped because "
            "Tesseract is unavailable.",
            flush=True
        )

        return ""


    if not OCR_LANGUAGE:

        print(
            "OCR skipped because no "
            "supported language data "
            "was found.",
            flush=True
        )

        return ""


    pixmap = None

    image = None


    try:

        print(
            "Rendering page for OCR...",
            flush=True
        )


        matrix = pymupdf.Matrix(
            OCR_SCALE,
            OCR_SCALE
        )


        pixmap = page.get_pixmap(
            matrix=matrix,
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


        print(
            "Running OCR using:",
            OCR_LANGUAGE,
            flush=True
        )


        try:

            text = (
                pytesseract
                .image_to_string(
                    image,
                    lang=OCR_LANGUAGE,
                    config="--oem 3 --psm 3"
                )
            )

        except Exception as error:

            print(
                "Primary OCR failed:",
                error,
                flush=True
            )


            if (
                OCR_LANGUAGE
                != "eng"
            ):

                try:

                    print(
                        "Retrying with "
                        "English OCR...",
                        flush=True
                    )

                    text = (
                        pytesseract
                        .image_to_string(
                            image,
                            lang="eng",
                            config=(
                                "--oem 3 "
                                "--psm 3"
                            )
                        )
                    )

                except Exception as english_error:

                    print(
                        "English OCR "
                        "also failed:",
                        english_error,
                        flush=True
                    )

                    return ""

            else:

                return ""


        text = clean_text(
            text
        )


        print(
            "OCR extracted characters:",
            len(text),
            flush=True
        )


        return text


    except Exception as error:

        print(
            "OCR page processing error:",
            error,
            flush=True
        )

        return ""


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


    if not TESSERACT_AVAILABLE:

        print(
            "Cannot OCR scanned pages "
            "because Tesseract is not "
            "available on this server.",
            flush=True
        )

        return pages


    if (
        len(
            missing_page_numbers
        )
        > MAX_OCR_PAGES
    ):

        print(
            "Large scanned PDF detected. "
            f"OCR will process the first "
            f"{MAX_OCR_PAGES} unreadable "
            "pages to protect server "
            "memory.",
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
                "OCR processing page "
                f"{page_number}...",
                flush=True
            )


            page = (
                document.load_page(
                    page_number - 1
                )
            )


            try:

                text = (
                    ocr_single_page(
                        page
                    )
                )


                if is_readable_text(
                    text
                ):

                    pages[
                        page_number - 1
                    ]["text"] = text


                    print(
                        "OCR successful "
                        "for page "
                        f"{page_number}.",
                        flush=True
                    )

                else:

                    print(
                        "OCR did not find "
                        "enough readable text "
                        "on page "
                        f"{page_number}.",
                        flush=True
                    )


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


def count_readable_pages(
    pages
):

    return sum(

        1

        for page in pages

        if is_readable_text(
            page["text"]
        )

    )


def extract_pdf_text(
    file_bytes
):

    print(
        "Starting PDF extraction...",
        flush=True
    )


    try:

        pages = (
            extract_with_pymupdf(
                file_bytes
            )
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


        if (
            readable_pages
            == len(pages)
        ):

            print(
                "All pages extracted "
                "successfully using "
                "PyMuPDF.",
                flush=True
            )

            return pages


        if readable_pages == 0:

            print(
                "This appears to be a "
                "scanned/image-based PDF. "
                "Starting OCR...",
                flush=True
            )

        else:

            print(
                "Some pages contain "
                "little or no embedded "
                "text. Starting OCR for "
                "those pages...",
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


        if (
            final_readable_pages
            == 0
        ):

            print(
                "No readable text could "
                "be extracted. If this is "
                "a scanned PDF, confirm "
                "that Tesseract OCR is "
                "installed on the server.",
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

def extract_pdf_text_progressive(
    file_bytes,
    on_update=None,
    quick_ocr_pages=1
):
    """
    Progressive extraction for interactive uploads.

    1. Extract embedded text from the whole PDF with PyMuPDF.
    2. Publish that immediately when any readable text exists.
    3. For scanned/unreadable pages, OCR a small quick batch first and publish it.
    4. Continue OCR for the remaining allowed pages and publish after each page.

    Existing extract_pdf_text() remains unchanged for comparison/fallback callers.
    """
    print(
        "Starting progressive PDF extraction...",
        flush=True
    )

    pages = extract_with_pymupdf(
        file_bytes
    )

    if not pages:
        return []

    def publish(stage, completed=False):
        if not on_update:
            return

        snapshot = [
            {
                "page": page["page"],
                "text": page.get("text", "")
            }
            for page in pages
        ]

        try:
            on_update(
                snapshot,
                stage,
                completed
            )
        except Exception as error:
            print(
                "Progressive update callback error:",
                error,
                flush=True
            )

    readable = count_readable_pages(
        pages
    )

    if readable:
        publish(
            "Embedded PDF text is ready",
            readable == len(pages)
        )

    missing_page_numbers = [
        page["page"]
        for page in pages
        if not is_readable_text(
            page.get("text", "")
        )
    ]

    if not missing_page_numbers:
        print(
            "Progressive extraction complete; OCR not required.",
            flush=True
        )
        return pages

    if not TESSERACT_AVAILABLE:
        print(
            "Progressive OCR unavailable because Tesseract is missing.",
            flush=True
        )
        return pages

    # Keep the current server-protection limit. This avoids turning a free
    # Render instance into a long-running full-document OCR worker.
    ocr_targets = missing_page_numbers[
        :MAX_OCR_PAGES
    ]

    quick_count = max(
        1,
        min(
            int(quick_ocr_pages or 1),
            len(ocr_targets)
        )
    )

    document = None

    try:
        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        )

        for index, page_number in enumerate(
            ocr_targets
        ):
            if index == 0:
                stage = (
                    "OCRing first scanned page for quick access..."
                )
            elif index < quick_count:
                stage = (
                    f"OCRing quick page {index + 1}/{quick_count}..."
                )
            else:
                stage = (
                    f"Continuing OCR in background "
                    f"({index + 1}/{len(ocr_targets)})..."
                )

            print(
                stage,
                flush=True
            )

            page = document.load_page(
                page_number - 1
            )

            try:
                text = ocr_single_page(
                    page
                )

                if is_readable_text(
                    text
                ):
                    pages[
                        page_number - 1
                    ]["text"] = text

                    # Publish as soon as the first scanned page is usable,
                    # then after every additional OCR page.
                    publish(
                        (
                            "First scanned page is searchable"
                            if index == 0
                            else stage
                        ),
                        False
                    )
            finally:
                del page
                gc.collect()

        publish(
            "Progressive OCR complete",
            True
        )

        return pages

    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass

        gc.collect()

