import os
import json
import re
import base64
import hashlib
import hmac
import secrets
import time
import gc
import threading
import uuid
from pathlib import Path

import requests
import numpy as np
import fitz

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Header
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import Response, FileResponse

from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pdf_utils import (
    extract_pdf_text,
    extract_pdf_text_progressive
)

from rag import (
    chunk_pages,
    build_faiss_index,
    search_chunks
)

from database import (
    Base,
    engine,
    get_db,
    ensure_schema
)

from library import Document, User

from evaluation import (
    evaluate_dataset,
    compare_retrieval_methods
)


load_dotenv()


Base.metadata.create_all(
    bind=engine
)

ensure_schema()


# Persistent processed-text cache.
# This survives Render restarts because the text is stored in PostgreSQL.
with engine.begin() as connection:
    connection.execute(
        sql_text(
            """
            CREATE TABLE IF NOT EXISTS processed_pdf_cache (
                id BIGSERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                total_pages INTEGER NOT NULL DEFAULT 0,
                pages_with_text INTEGER NOT NULL DEFAULT 0,
                uncached_processing_ms DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, content_hash)
            )
            """
        )
    )

    connection.execute(
        sql_text(
            """
            ALTER TABLE processed_pdf_cache
            ADD COLUMN IF NOT EXISTS uncached_processing_ms DOUBLE PRECISION
            """
        )
    )

    connection.execute(
        sql_text(
            """
            CREATE TABLE IF NOT EXISTS app_usage_metrics (
                user_id INTEGER PRIMARY KEY,
                qa_queries BIGINT NOT NULL DEFAULT 0,
                english_queries BIGINT NOT NULL DEFAULT 0,
                tamil_queries BIGINT NOT NULL DEFAULT 0,
                first_query_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_query_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


app = FastAPI(
    title="TN Insight AI API",
    description="Backend API for TN Insight AI",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


PDF_STORAGE_DIR = Path(
    "saved_pdfs"
)

PDF_STORAGE_DIR.mkdir(
    exist_ok=True
)


EVALUATION_DATASET_PATH = Path(
    "evaluation_dataset.json"
)


AUTH_SECRET_KEY = os.getenv(
    "AUTH_SECRET_KEY",
    "tn-insight-ai-development-secret-change-me"
)

AUTH_TOKEN_TTL_SECONDS = int(
    os.getenv(
        "AUTH_TOKEN_TTL_SECONDS",
        "86400"
    )
)

PBKDF2_ITERATIONS = 260000


runtime_states = {}
processing_jobs = {}

# Cache extracted PDF pages by SHA-256 to avoid repeated OCR.
pdf_extraction_cache = {}
MAX_PDF_CACHE_ITEMS = 12


def create_empty_runtime_state():

    return {
        "current_chunks": [],
        "current_index": None,
        "current_filename": None,
        "current_pages": [],
        "current_pdf_bytes": None,
        "current_library_document_id": None,
        "processing_job_id": None,
        "processing_complete": True,
        "comparison_pdf_a_bytes": None,
        "comparison_pdf_b_bytes": None,
        "comparison_filename_a": None,
        "comparison_filename_b": None
    }


def get_runtime_state(
    user_id
):

    if user_id not in runtime_states:

        runtime_states[
            user_id
        ] = create_empty_runtime_state()

    return runtime_states[
        user_id
    ]


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LibraryComparisonRequest(BaseModel):
    document_a_id: int
    document_b_id: int
    language: str = "English"


class QuestionRequest(BaseModel):
    question: str
    language: str = "English"


class SaveDocumentRequest(BaseModel):
    title: str
    department: str = "Unknown"
    document_type: str = "Government Document"
    year: str = "Unknown"


class EvaluationItem(BaseModel):
    question: str
    relevant_pages: list[int]


class EvaluationRequest(BaseModel):
    questions: list[EvaluationItem]


def normalize_email(
    email
):

    return (
        str(email)
        .strip()
        .lower()
    )


def validate_email(
    email
):

    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email
        )
    )


def hash_password(
    password
):

    salt = secrets.token_bytes(
        16
    )

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(
            "utf-8"
        ),
        salt,
        PBKDF2_ITERATIONS
    )

    return (
        f"pbkdf2_sha256$"
        f"{PBKDF2_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode('utf-8')}$"
        f"{base64.urlsafe_b64encode(password_hash).decode('utf-8')}"
    )


def verify_password(
    password,
    stored_hash
):

    try:

        algorithm, iterations, salt_text, hash_text = (
            stored_hash.split(
                "$",
                3
            )
        )

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.urlsafe_b64decode(
            salt_text.encode(
                "utf-8"
            )
        )

        expected_hash = (
            base64.urlsafe_b64decode(
                hash_text.encode(
                    "utf-8"
                )
            )
        )

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(
                "utf-8"
            ),
            salt,
            int(iterations)
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except Exception:

        return False


def base64url_encode(
    value
):

    return (
        base64
        .urlsafe_b64encode(
            value
        )
        .rstrip(
            b"="
        )
        .decode(
            "utf-8"
        )
    )


def base64url_decode(
    value
):

    padding = "=" * (
        (-len(value)) % 4
    )

    return base64.urlsafe_b64decode(
        (
            value
            + padding
        ).encode(
            "utf-8"
        )
    )


def create_access_token(
    user
):

    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    now = int(
        time.time()
    )

    payload = {
        "sub": str(
            user.id
        ),
        "email":
            user.email,
        "name":
            user.name,
        "iat":
            now,
        "exp":
            now
            + AUTH_TOKEN_TTL_SECONDS
    }

    header_part = (
        base64url_encode(
            json.dumps(
                header,
                separators=(
                    ",",
                    ":"
                )
            ).encode(
                "utf-8"
            )
        )
    )

    payload_part = (
        base64url_encode(
            json.dumps(
                payload,
                separators=(
                    ",",
                    ":"
                )
            ).encode(
                "utf-8"
            )
        )
    )

    signing_input = (
        f"{header_part}.{payload_part}"
    )

    signature = hmac.new(
        AUTH_SECRET_KEY.encode(
            "utf-8"
        ),
        signing_input.encode(
            "utf-8"
        ),
        hashlib.sha256
    ).digest()

    signature_part = (
        base64url_encode(
            signature
        )
    )

    return (
        f"{signing_input}."
        f"{signature_part}"
    )


def decode_access_token(
    token
):

    try:

        parts = token.split(
            "."
        )

        if len(parts) != 3:
            return None

        header_part, payload_part, signature_part = (
            parts
        )

        signing_input = (
            f"{header_part}.{payload_part}"
        )

        expected_signature = hmac.new(
            AUTH_SECRET_KEY.encode(
                "utf-8"
            ),
            signing_input.encode(
                "utf-8"
            ),
            hashlib.sha256
        ).digest()

        provided_signature = (
            base64url_decode(
                signature_part
            )
        )

        if not hmac.compare_digest(
            expected_signature,
            provided_signature
        ):
            return None

        payload = json.loads(
            base64url_decode(
                payload_part
            ).decode(
                "utf-8"
            )
        )

        if int(
            payload.get(
                "exp",
                0
            )
        ) < int(
            time.time()
        ):
            return None

        return payload

    except Exception:

        return None


def get_current_user(
    authorization:
        str | None = Header(
            default=None
        ),
    db: Session = Depends(
        get_db
    )
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail=
                "Authentication required"
        )

    parts = authorization.split(
        " ",
        1
    )

    if (
        len(parts) != 2
        or parts[0].lower()
        != "bearer"
    ):

        raise HTTPException(
            status_code=401,
            detail=
                "Invalid authorization header"
        )

    payload = decode_access_token(
        parts[1].strip()
    )

    if not payload:

        print(
            "AUTH ERROR: Invalid or expired token"
        )

        raise HTTPException(
            status_code=401,
            detail=
                "Invalid or expired token"
        )

    try:

        user_id = int(
            payload.get(
                "sub"
            )
        )

    except Exception:

        raise HTTPException(
            status_code=401,
            detail=
                "Invalid token"
        )

    user = (
        db
        .query(
            User
        )
        .filter(
            User.id
            == user_id
        )
        .first()
    )

    if not user:

        print(
            "AUTH ERROR: User account not found",
            user_id
        )

        raise HTTPException(
            status_code=401,
            detail=
                "User account not found"
        )

    return user



def get_authenticated_user_id(
    authorization:
        str | None = Header(
            default=None
        )
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    parts = authorization.split(" ", 1)

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )

    payload = decode_access_token(
        parts[1].strip()
    )

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    try:
        return int(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def document_belongs_to_user(
    document,
    user
):

    return (
        document is not None
        and document.user_id
        == user.id
    )


def get_library_pdf_path(
    document_id
):

    return (
        PDF_STORAGE_DIR
        / f"document_{document_id}.pdf"
    )


def save_library_pdf(
    document_id,
    pdf_bytes
):

    if not pdf_bytes:
        return False

    path = get_library_pdf_path(
        document_id
    )

    with open(
        path,
        "wb"
    ) as file:
        file.write(
            pdf_bytes
        )

    return True


def parse_saved_pages(
    extracted_text
):

    if not extracted_text:
        return []


    pattern = re.compile(
        r"(?:^|\n\n)PAGE\s+(\d+)\n",
        re.IGNORECASE
    )


    matches = list(
        pattern.finditer(
            extracted_text
        )
    )


    if not matches:

        return [
            {
                "page": 1,
                "text":
                    extracted_text.strip()
            }
        ]


    pages = []


    for index, match in enumerate(
        matches
    ):

        page_number = int(
            match.group(1)
        )

        start = match.end()

        if index + 1 < len(
            matches
        ):
            end = (
                matches[index + 1]
                .start()
            )
        else:
            end = len(
                extracted_text
            )


        text = (
            extracted_text[
                start:end
            ]
            .strip()
        )


        if text:

            pages.append({
                "page":
                    page_number,
                "text":
                    text
            })


    return pages


def load_evaluation_dataset():

    if not EVALUATION_DATASET_PATH.exists():

        return {
            "success": False,
            "message":
                "evaluation_dataset.json was not found in the backend folder",
            "mode": None,
            "documents": [],
            "questions": []
        }

    try:

        with open(
            EVALUATION_DATASET_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            list
        ):

            return {
                "success": False,
                "message":
                    "evaluation_dataset.json must contain a JSON array",
                "mode": None,
                "documents": [],
                "questions": []
            }

        if not data:

            return {
                "success": False,
                "message":
                    "evaluation_dataset.json is empty",
                "mode": None,
                "documents": [],
                "questions": []
            }

        is_multi_document = any(
            isinstance(item, dict)
            and "document" in item
            and "questions" in item
            for item in data
        )

        if is_multi_document:

            documents = []

            for group in data:

                if not isinstance(
                    group,
                    dict
                ):
                    continue

                document_name = str(
                    group.get(
                        "document",
                        ""
                    )
                ).strip()

                raw_questions = (
                    group.get(
                        "questions",
                        []
                    )
                )

                if (
                    not document_name
                    or not isinstance(
                        raw_questions,
                        list
                    )
                ):
                    continue

                questions = []

                for item in raw_questions:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue

                    question = str(
                        item.get(
                            "question",
                            ""
                        )
                    ).strip()

                    relevant_pages = (
                        item.get(
                            "relevant_pages",
                            []
                        )
                    )

                    if not isinstance(
                        relevant_pages,
                        list
                    ):
                        continue

                    valid_pages = sorted(
                        set(
                            page
                            for page in relevant_pages
                            if (
                                isinstance(
                                    page,
                                    int
                                )
                                and page >= 1
                            )
                        )
                    )

                    if (
                        question
                        and valid_pages
                    ):

                        questions.append({
                            "question":
                                question,
                            "relevant_pages":
                                valid_pages
                        })

                if questions:

                    documents.append({
                        "document":
                            document_name,
                        "questions":
                            questions
                    })

            if not documents:

                return {
                    "success": False,
                    "message":
                        "No valid document groups were found in evaluation_dataset.json",
                    "mode":
                        "multi_document",
                    "documents": [],
                    "questions": []
                }

            return {
                "success": True,
                "message":
                    "Multi-document evaluation dataset loaded successfully",
                "mode":
                    "multi_document",
                "documents":
                    documents,
                "questions": []
            }

        questions = []

        for item in data:

            if not isinstance(
                item,
                dict
            ):
                continue

            question = str(
                item.get(
                    "question",
                    ""
                )
            ).strip()

            relevant_pages = (
                item.get(
                    "relevant_pages",
                    []
                )
            )

            if not isinstance(
                relevant_pages,
                list
            ):
                continue

            valid_pages = sorted(
                set(
                    page
                    for page in relevant_pages
                    if (
                        isinstance(
                            page,
                            int
                        )
                        and page >= 1
                    )
                )
            )

            if (
                question
                and valid_pages
            ):

                questions.append({
                    "question":
                        question,
                    "relevant_pages":
                        valid_pages
                })

        if not questions:

            return {
                "success": False,
                "message":
                    "No valid evaluation questions were found in evaluation_dataset.json",
                "mode":
                    "single_document",
                "documents": [],
                "questions": []
            }

        return {
            "success": True,
            "message":
                "Single-document evaluation dataset loaded successfully",
            "mode":
                "single_document",
            "documents": [],
            "questions":
                questions
        }

    except json.JSONDecodeError as error:

        return {
            "success": False,
            "message":
                f"Invalid JSON in evaluation_dataset.json: {error}",
            "mode": None,
            "documents": [],
            "questions": []
        }

    except Exception as error:

        return {
            "success": False,
            "message":
                str(error),
            "mode": None,
            "documents": [],
            "questions": []
        }


def combine_evaluation_results(
    per_document_results
):

    all_details = []

    for item in per_document_results:
        document_name = item["document"]
        evaluation = item["evaluation"]

        for detail in evaluation.get(
            "details",
            []
        ):
            all_details.append({
                "document": document_name,
                **detail
            })

    if not all_details:
        return {
            "total_questions": 0,
            "recall_at_1": 0,
            "recall_at_3": 0,
            "recall_at_5": 0,
            "hit_at_1": 0,
            "hit_at_3": 0,
            "hit_at_5": 0,
            "mrr": 0,
            "average_retrieval_latency_ms": 0,
            "median_retrieval_latency_ms": 0,
            "p95_retrieval_latency_ms": 0,
            "details": []
        }

    total = len(all_details)

    def average_metric(name):
        return round(
            sum(
                float(item.get(name, 0) or 0)
                for item in all_details
            ) / total,
            4
        )

    latencies = sorted(
        float(item.get("retrieval_latency_ms", 0) or 0)
        for item in all_details
    )

    median_latency = 0.0
    if latencies:
        middle = len(latencies) // 2
        if len(latencies) % 2 == 0:
            median_latency = (
                latencies[middle - 1]
                + latencies[middle]
            ) / 2
        else:
            median_latency = latencies[middle]

    p95_latency = 0.0
    if latencies:
        p95_index = max(
            0,
            min(
                len(latencies) - 1,
                int(np.ceil(0.95 * len(latencies))) - 1
            )
        )
        p95_latency = latencies[p95_index]

    return {
        "total_questions": total,
        "recall_at_1": average_metric("recall_at_1"),
        "recall_at_3": average_metric("recall_at_3"),
        "recall_at_5": average_metric("recall_at_5"),
        "hit_at_1": average_metric("hit_at_1"),
        "hit_at_3": average_metric("hit_at_3"),
        "hit_at_5": average_metric("hit_at_5"),
        "mrr": average_metric("reciprocal_rank"),
        "average_retrieval_latency_ms": round(
            sum(latencies) / len(latencies),
            3
        ) if latencies else 0,
        "median_retrieval_latency_ms": round(
            median_latency,
            3
        ),
        "p95_retrieval_latency_ms": round(
            p95_latency,
            3
        ),
        "details": all_details
    }

def combine_retriever_comparisons(
    per_document_results
):

    methods = [
        "tfidf",
        "bm25",
        "hybrid"
    ]

    combined = {}

    total_questions = sum(
        item["evaluation"]
        .get(
            "total_questions",
            0
        )
        for item in per_document_results
    )

    if total_questions <= 0:

        return {
            method: {
                "recall_at_1": 0,
                "recall_at_3": 0,
                "recall_at_5": 0,
                "mrr": 0
            }
            for method in methods
        }

    for method in methods:

        combined[
            method
        ] = {}

        for metric in [
            "recall_at_1",
            "recall_at_3",
            "recall_at_5",
            "hit_at_1",
            "hit_at_3",
            "hit_at_5",
            "mrr",
            "average_retrieval_latency_ms",
            "median_retrieval_latency_ms",
            "p95_retrieval_latency_ms"
        ]:

            weighted_total = 0.0

            for item in (
                per_document_results
            ):

                question_count = (
                    item["evaluation"]
                    .get(
                        "total_questions",
                        0
                    )
                )

                value = (
                    item[
                        "retriever_comparison"
                    ]
                    .get(
                        method,
                        {}
                    )
                    .get(
                        metric,
                        0
                    )
                )

                weighted_total += (
                    value
                    * question_count
                )

            combined[
                method
            ][
                metric
            ] = round(
                weighted_total
                / total_questions,
                4
            )

    return combined


@app.post("/auth/register")
def register_user(
    request: RegisterRequest,
    db: Session = Depends(
        get_db
    )
):

    name = request.name.strip()

    email = normalize_email(
        request.email
    )

    password = request.password

    if len(name) < 2:

        return {
            "success": False,
            "message":
                "Name must contain at least 2 characters"
        }

    if not validate_email(
        email
    ):

        return {
            "success": False,
            "message":
                "Please enter a valid email address"
        }

    if len(password) < 8:

        return {
            "success": False,
            "message":
                "Password must contain at least 8 characters"
        }

    existing_user = (
        db
        .query(
            User
        )
        .filter(
            User.email
            == email
        )
        .first()
    )

    if existing_user:

        return {
            "success": False,
            "message":
                "An account with this email already exists"
        }

    try:

        user = User(
            name=name,
            email=email,
            password_hash=
                hash_password(
                    password
                )
        )

        db.add(
            user
        )

        db.commit()

        db.refresh(
            user
        )

        token = create_access_token(
            user
        )

        return {
            "success": True,
            "message":
                "Account created successfully",
            "access_token":
                token,
            "token_type":
                "bearer",
            "user": {
                "id":
                    user.id,
                "name":
                    user.name,
                "email":
                    user.email
            }
        }

    except Exception as error:

        db.rollback()

        print(
            "REGISTER ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                "Unable to create account"
        }


@app.post("/auth/login")
def login_user(
    request: LoginRequest,
    db: Session = Depends(
        get_db
    )
):

    email = normalize_email(
        request.email
    )

    user = (
        db
        .query(
            User
        )
        .filter(
            User.email
            == email
        )
        .first()
    )

    if (
        not user
        or not verify_password(
            request.password,
            user.password_hash
        )
    ):

        return {
            "success": False,
            "message":
                "Invalid email or password"
        }

    token = create_access_token(
        user
    )

    return {
        "success": True,
        "message":
            "Login successful",
        "access_token":
            token,
        "token_type":
            "bearer",
        "user": {
            "id":
                user.id,
            "name":
                user.name,
            "email":
                user.email
        }
    }


@app.get("/auth/me")
def auth_me(
    current_user:
        User = Depends(
            get_current_user
        )
):

    return {
        "success": True,
        "user": {
            "id":
                current_user.id,
            "name":
                current_user.name,
            "email":
                current_user.email
        }
    }


@app.post("/auth/logout")
def logout_user(
    current_user:
        User = Depends(
            get_current_user
        )
):

    runtime_states.pop(
        current_user.id,
        None
    )

    return {
        "success": True,
        "message":
            "Logged out successfully"
    }


@app.get("/")
def home():

    return {
        "success": True,
        "message":
            "TN Insight AI backend is running"
    }


@app.get("/health")
def health():

    return {
        "success": True,
        "status": "ok"
    }


@app.get("/project-metrics")
def project_metrics(
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):
    try:
        registered_users = db.query(User).count()
        total_saved_documents = db.query(Document).count()

        with engine.connect() as connection:
            usage = connection.execute(
                sql_text(
                    """
                    SELECT
                        COALESCE(SUM(qa_queries), 0) AS qa_queries,
                        COALESCE(SUM(english_queries), 0) AS english_queries,
                        COALESCE(SUM(tamil_queries), 0) AS tamil_queries,
                        COUNT(*) FILTER (WHERE qa_queries > 0) AS active_qa_users
                    FROM app_usage_metrics
                    """
                )
            ).mappings().first()

            cache_stats = connection.execute(
                sql_text(
                    """
                    SELECT
                        COUNT(*) AS cached_documents,
                        COALESCE(SUM(total_pages), 0) AS cached_total_pages,
                        COALESCE(AVG(uncached_processing_ms), 0) AS avg_uncached_processing_ms
                    FROM processed_pdf_cache
                    """
                )
            ).mappings().first()

        return {
            "success": True,
            "note": (
                "Usage counters start from the deployment that introduced "
                "app_usage_metrics; they do not reconstruct historical queries."
            ),
            "registered_users": registered_users,
            "active_qa_users_tracked": int(
                usage["active_qa_users"] or 0
            ),
            "qa_queries_tracked": int(
                usage["qa_queries"] or 0
            ),
            "english_queries_tracked": int(
                usage["english_queries"] or 0
            ),
            "tamil_queries_tracked": int(
                usage["tamil_queries"] or 0
            ),
            "total_saved_documents": total_saved_documents,
            "cached_documents": int(
                cache_stats["cached_documents"] or 0
            ),
            "cached_total_pages": int(
                cache_stats["cached_total_pages"] or 0
            ),
            "average_uncached_processing_ms": round(
                float(
                    cache_stats["avg_uncached_processing_ms"]
                    or 0
                ),
                2
            )
        }

    except Exception as error:
        return {
            "success": False,
            "message": str(error)
        }


@app.get("/evaluation")
def evaluation_status(
    current_user:
        User = Depends(
            get_current_user
        )
):

    return {
        "success": True,
        "message":
            "Evaluation endpoint is ready",
        "requires_loaded_document":
            True,
        "metrics": [
            "Recall@1",
            "Recall@3",
            "Recall@5",
            "MRR"
        ],
        "run_endpoint":
            "POST /evaluation"
    }

@app.post("/evaluation")
def run_evaluation(
    request: EvaluationRequest,
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    current_chunks = (
        state["current_chunks"]
    )

    if not current_chunks:

        return {
            "success": False,
            "message":
                "Please upload, process, or load a document before running evaluation"
        }

    if not request.questions:

        return {
            "success": False,
            "message":
                "Please provide at least one evaluation question"
        }

    try:

        current_index = (
            build_faiss_index(
                current_chunks
            )
        )

        evaluation_questions = []

        for item in request.questions:

            question = (
                item.question.strip()
            )

            relevant_pages = sorted(
                set(
                    page
                    for page
                    in item.relevant_pages
                    if page >= 1
                )
            )

            if (
                not question
                or not relevant_pages
            ):
                continue

            evaluation_questions.append({
                "question":
                    question,
                "relevant_pages":
                    relevant_pages
            })

        if not evaluation_questions:

            return {
                "success": False,
                "message":
                    "No valid evaluation questions were provided"
            }

        result = evaluate_dataset(
            evaluation_questions,
            current_chunks,
            current_index,
            search_chunks
        )

        comparison = (
            compare_retrieval_methods(
                evaluation_questions,
                current_chunks,
                current_index,
                search_chunks
            )
        )

        state[
            "current_index"
        ] = build_faiss_index(
            current_chunks
        )

        return {
            "success": True,
            "document":
                state[
                    "current_filename"
                ],
            "retrieval_method":
                "TF-IDF + BM25 Hybrid Search",
            "evaluation":
                result,
            "retriever_comparison":
                comparison
        }

    except Exception as error:

        print(
            "EVALUATION ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

@app.get("/evaluation/dataset")
def get_evaluation_dataset(
    current_user:
        User = Depends(
            get_current_user
        )
):

    dataset = (
        load_evaluation_dataset()
    )

    if not dataset["success"]:

        return {
            "success": False,
            "message":
                dataset["message"]
        }

    if (
        dataset["mode"]
        == "multi_document"
    ):

        total_questions = sum(
            len(
                item["questions"]
            )
            for item
            in dataset["documents"]
        )

        return {
            "success": True,
            "mode":
                "multi_document",
            "total_documents":
                len(
                    dataset["documents"]
                ),
            "total_questions":
                total_questions,
            "documents": [
                {
                    "document":
                        item["document"],
                    "question_count":
                        len(
                            item["questions"]
                        )
                }
                for item
                in dataset["documents"]
            ]
        }

    return {
        "success": True,
        "mode":
            "single_document",
        "total_documents":
            1,
        "total_questions":
            len(
                dataset["questions"]
            ),
        "questions":
            dataset["questions"]
    }

@app.post("/evaluation/run-dataset")
def run_evaluation_dataset(
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    dataset = (
        load_evaluation_dataset()
    )

    if not dataset["success"]:

        return {
            "success": False,
            "message":
                dataset["message"]
        }

    state = get_runtime_state(
        current_user.id
    )

    original_chunks = list(
        state["current_chunks"]
    )

    if (
        dataset["mode"]
        == "single_document"
    ):

        if not original_chunks:

            return {
                "success": False,
                "message":
                    "Please upload, process, or load a document before running the single-document dataset evaluation"
            }

        try:

            current_index = (
                build_faiss_index(
                    original_chunks
                )
            )

            evaluation_questions = (
                dataset["questions"]
            )

            result = evaluate_dataset(
                evaluation_questions,
                original_chunks,
                current_index,
                search_chunks
            )

            comparison = (
                compare_retrieval_methods(
                    evaluation_questions,
                    original_chunks,
                    current_index,
                    search_chunks
                )
            )

            state[
                "current_index"
            ] = build_faiss_index(
                original_chunks
            )

            return {
                "success": True,
                "mode":
                    "single_document",
                "document":
                    state[
                        "current_filename"
                    ],
                "dataset_file":
                    "evaluation_dataset.json",
                "total_documents":
                    1,
                "total_questions":
                    len(
                        evaluation_questions
                    ),
                "retrieval_method":
                    "TF-IDF + BM25 Hybrid Search",
                "evaluation":
                    result,
                "retriever_comparison":
                    comparison,
                "per_document": [
                    {
                        "document":
                            state[
                                "current_filename"
                            ],
                        "evaluation":
                            result,
                        "retriever_comparison":
                            comparison
                    }
                ],
                "missing_documents":
                    []
            }

        except Exception as error:

            print(
                "DATASET EVALUATION ERROR:",
                error
            )

            return {
                "success": False,
                "message":
                    str(error)
            }

    per_document_results = []
    missing_documents = []

    try:

        for group in (
            dataset["documents"]
        ):

            document_name = (
                group["document"]
            )

            evaluation_questions = (
                group["questions"]
            )

            user_document = (
                db
                .query(
                    Document
                )
                .filter(
                    Document.filename
                    == document_name,
                    Document.user_id
                    == current_user.id
                )
                .first()
            )

            shared_benchmark = (
                db
                .query(
                    Document
                )
                .filter(
                    Document.filename
                    == document_name,
                    Document.user_id
                    .is_(None)
                )
                .first()
            )

            document = (
                user_document
                or shared_benchmark
            )

            if not document:

                missing_documents.append({
                    "document":
                        document_name,
                    "reason":
                        "Benchmark document is not available"
                })

                continue

            saved_text = (
                document.extracted_text
                or ""
            ).strip()

            if not saved_text:

                missing_documents.append({
                    "document":
                        document_name,
                    "reason":
                        "Saved document contains no extracted text"
                })

                continue

            pages = parse_saved_pages(
                saved_text
            )

            pages = [
                page
                for page in pages
                if page["text"].strip()
            ]

            if not pages:

                missing_documents.append({
                    "document":
                        document_name,
                    "reason":
                        "No readable pages could be reconstructed from the saved document"
                })

                continue

            benchmark_chunks = (
                chunk_pages(
                    pages
                )
            )

            if not benchmark_chunks:

                missing_documents.append({
                    "document":
                        document_name,
                    "reason":
                        "No chunks could be created"
                })

                continue

            benchmark_index = (
                build_faiss_index(
                    benchmark_chunks
                )
            )

            if benchmark_index is None:

                missing_documents.append({
                    "document":
                        document_name,
                    "reason":
                        "Retriever index could not be created"
                })

                continue

            evaluation_result = (
                evaluate_dataset(
                    evaluation_questions,
                    benchmark_chunks,
                    benchmark_index,
                    search_chunks
                )
            )

            comparison_result = (
                compare_retrieval_methods(
                    evaluation_questions,
                    benchmark_chunks,
                    benchmark_index,
                    search_chunks
                )
            )

            per_document_results.append({
                "document":
                    document_name,
                "document_id":
                    document.id,
                "total_pages":
                    document.total_pages,
                "total_chunks":
                    len(benchmark_chunks),
                "evaluation":
                    evaluation_result,
                "retriever_comparison":
                    comparison_result
            })

        if not per_document_results:

            return {
                "success": False,
                "message":
                    "None of the benchmark documents could be evaluated.",
                "missing_documents":
                    missing_documents
            }

        overall_evaluation = (
            combine_evaluation_results(
                per_document_results
            )
        )

        overall_comparison = (
            combine_retriever_comparisons(
                per_document_results
            )
        )

        return {
            "success": True,
            "mode":
                "multi_document",
            "dataset_file":
                "evaluation_dataset.json",
            "retrieval_method":
                "TF-IDF + BM25 Hybrid Search",
            "total_documents_in_dataset":
                len(
                    dataset["documents"]
                ),
            "documents_evaluated":
                len(
                    per_document_results
                ),
            "total_pages_evaluated":
                sum(
                    int(item.get("total_pages") or 0)
                    for item in per_document_results
                ),
            "total_chunks_evaluated":
                sum(
                    int(item.get("total_chunks") or 0)
                    for item in per_document_results
                ),
            "total_questions":
                overall_evaluation[
                    "total_questions"
                ],
            "evaluation":
                overall_evaluation,
            "retriever_comparison":
                overall_comparison,
            "per_document":
                per_document_results,
            "missing_documents":
                missing_documents
        }

    except Exception as error:

        print(
            "MULTI-DOCUMENT DATASET EVALUATION ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

    finally:

        if original_chunks:

            state[
                "current_index"
            ] = build_faiss_index(
                original_chunks
            )

        else:

            state[
                "current_index"
            ] = None

@app.get("/current-pdf")
def get_current_pdf(
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    current_pdf_bytes = (
        state["current_pdf_bytes"]
    )

    if not current_pdf_bytes:

        raise HTTPException(
            status_code=404,
            detail=
                "Current PDF is not available"
        )

    filename = (
        state["current_filename"]
        or "document.pdf"
    )

    return Response(
        content=
            current_pdf_bytes,
        media_type=
            "application/pdf",
        headers={
            "Content-Disposition":
                f'inline; filename="{filename}"'
        }
    )

@app.get(
    "/library/{document_id}/pdf"
)
def get_library_pdf(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    document = (
        db
        .query(
            Document
        )
        .filter(
            Document.id
            == document_id,
            Document.user_id
            == current_user.id
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=404,
            detail=
                "Document not found"
        )

    path = get_library_pdf_path(
        document_id
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "The original PDF was not stored for this document. "
                "Please re-upload and save it."
            )
        )

    return FileResponse(
        path=str(
            path
        ),
        media_type=
            "application/pdf",
        filename=
            document.filename,
        content_disposition_type=
            "inline"
    )

@app.get("/comparison/a/pdf")
def get_comparison_pdf_a(
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    pdf_bytes = (
        state[
            "comparison_pdf_a_bytes"
        ]
    )

    filename = (
        state[
            "comparison_filename_a"
        ]
    )

    if not pdf_bytes:

        raise HTTPException(
            status_code=404,
            detail=
                "Comparison Document A is unavailable"
        )

    return Response(
        content=
            pdf_bytes,
        media_type=
            "application/pdf",
        headers={
            "Content-Disposition":
                f'inline; filename="{filename or "document-a.pdf"}"'
        }
    )

@app.get("/comparison/b/pdf")
def get_comparison_pdf_b(
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    pdf_bytes = (
        state[
            "comparison_pdf_b_bytes"
        ]
    )

    filename = (
        state[
            "comparison_filename_b"
        ]
    )

    if not pdf_bytes:

        raise HTTPException(
            status_code=404,
            detail=
                "Comparison Document B is unavailable"
        )

    return Response(
        content=
            pdf_bytes,
        media_type=
            "application/pdf",
        headers={
            "Content-Disposition":
                f'inline; filename="{filename or "document-b.pdf"}"'
        }
    )

@app.get("/library")
def get_library(
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    try:

        documents = (
            db
            .query(
                Document
            )
            .filter(
                Document.user_id
                == current_user.id
            )
            .order_by(
                Document.id.desc()
            )
            .all()
        )

        return {
            "success": True,
            "documents": [
                {
                    "id":
                        document.id,
                    "filename":
                        document.filename,
                    "title":
                        document.title,
                    "department":
                        document.department,
                    "document_type":
                        document.document_type,
                    "year":
                        document.year,
                    "total_pages":
                        document.total_pages,
                    "pdf_available":
                        get_library_pdf_path(
                            document.id
                        ).exists()
                }
                for document
                in documents
            ]
        }

    except Exception as error:

        print(
            "LIBRARY ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

@app.get("/library/{document_id}")
def get_library_document(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    try:

        document = (
            db
            .query(
                Document
            )
            .filter(
                Document.id
                == document_id,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        if not document:

            return {
                "success": False,
                "message":
                    "Document not found"
            }

        return {
            "success": True,
            "document": {
                "id":
                    document.id,
                "filename":
                    document.filename,
                "title":
                    document.title,
                "department":
                    document.department,
                "document_type":
                    document.document_type,
                "year":
                    document.year,
                "total_pages":
                    document.total_pages,
                "extracted_text":
                    document.extracted_text,
                "pdf_available":
                    get_library_pdf_path(
                        document.id
                    ).exists()
            }
        }

    except Exception as error:

        print(
            "LIBRARY DOCUMENT ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

@app.post("/save-current-document")
def save_current_document(
    request: SaveDocumentRequest,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    current_chunks = (
        state["current_chunks"]
    )

    current_filename = (
        state["current_filename"]
    )

    current_pages = (
        state["current_pages"]
    )

    current_pdf_bytes = (
        state["current_pdf_bytes"]
    )

    if (
        not current_chunks
        or not current_filename
    ):

        return {
            "success": False,
            "message":
                "Please upload and process a document first"
        }

    try:

        if current_pages:

            full_text = "\n\n".join(
                f"PAGE {page['page']}\n{page['text']}"
                for page in current_pages
                if page["text"].strip()
            )

            total_pages = len(
                current_pages
            )

        else:

            full_text = "\n\n".join(
                chunk["text"]
                for chunk
                in current_chunks
            )

            total_pages = len(
                set(
                    chunk["page"]
                    for chunk
                    in current_chunks
                )
            )

        existing_document = (
            db
            .query(
                Document
            )
            .filter(
                Document.filename
                == current_filename,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        if existing_document:

            path = get_library_pdf_path(
                existing_document.id
            )

            if (
                current_pdf_bytes
                and not path.exists()
            ):

                save_library_pdf(
                    existing_document.id,
                    current_pdf_bytes
                )

                state[
                    "current_library_document_id"
                ] = existing_document.id

                return {
                    "success": True,
                    "message":
                        "Document already existed. Original PDF has now been attached.",
                    "document": {
                        "id":
                            existing_document.id,
                        "filename":
                            existing_document.filename,
                        "title":
                            existing_document.title,
                        "department":
                            existing_document.department,
                        "document_type":
                            existing_document.document_type,
                        "year":
                            existing_document.year,
                        "total_pages":
                            existing_document.total_pages,
                        "pdf_available":
                            True
                    }
                }

            return {
                "success": False,
                "message":
                    "This document is already saved in your library"
            }

        document = Document(
            user_id=
                current_user.id,
            filename=
                current_filename,
            title=
                request.title.strip()
                or current_filename,
            department=
                request.department.strip()
                or "Unknown",
            document_type=
                request.document_type.strip()
                or "Government Document",
            year=
                request.year.strip()
                or "Unknown",
            total_pages=
                total_pages,
            extracted_text=
                full_text
        )

        db.add(
            document
        )

        db.commit()

        db.refresh(
            document
        )

        pdf_saved = (
            save_library_pdf(
                document.id,
                current_pdf_bytes
            )
        )

        state[
            "current_library_document_id"
        ] = document.id

        return {
            "success": True,
            "message":
                "Document saved to your private library successfully",
            "document": {
                "id":
                    document.id,
                "filename":
                    document.filename,
                "title":
                    document.title,
                "department":
                    document.department,
                "document_type":
                    document.document_type,
                "year":
                    document.year,
                "total_pages":
                    document.total_pages,
                "pdf_available":
                    pdf_saved
            }
        }

    except Exception as error:

        db.rollback()

        print(
            "SAVE LIBRARY ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

@app.post(
    "/load-library-document/{document_id}"
)
def load_library_document(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    try:

        document = (
            db
            .query(
                Document
            )
            .filter(
                Document.id
                == document_id,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        if not document:

            return {
                "success": False,
                "message":
                    "Document not found"
            }

        text_value = (
            document.extracted_text
            or ""
        ).strip()

        if not text_value:

            return {
                "success": False,
                "message":
                    "Saved document contains no readable text"
            }

        current_pages = (
            parse_saved_pages(
                text_value
            )
        )

        current_chunks = (
            chunk_pages(
                current_pages
            )
        )

        current_index = (
            build_faiss_index(
                current_chunks
            )
        )

        state[
            "current_pages"
        ] = current_pages

        state[
            "current_chunks"
        ] = current_chunks

        state[
            "current_index"
        ] = current_index

        state[
            "current_filename"
        ] = document.filename

        state[
            "current_library_document_id"
        ] = document.id

        pdf_path = get_library_pdf_path(
            document.id
        )

        if pdf_path.exists():

            with open(
                pdf_path,
                "rb"
            ) as file:

                state[
                    "current_pdf_bytes"
                ] = file.read()

        else:

            state[
                "current_pdf_bytes"
            ] = None

        return {
            "success": True,
            "message":
                "Document loaded from your private library",
            "document": {
                "id":
                    document.id,
                "filename":
                    document.filename,
                "title":
                    document.title,
                "department":
                    document.department,
                "document_type":
                    document.document_type,
                "year":
                    document.year,
                "total_pages":
                    document.total_pages,
                "total_chunks":
                    len(
                        current_chunks
                    ),
                "pdf_available":
                    pdf_path.exists()
            }
        }

    except Exception as error:

        print(
            "LOAD LIBRARY ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

@app.delete("/library/{document_id}")
def delete_library_document(
    document_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):

    try:

        document = (
            db
            .query(
                Document
            )
            .filter(
                Document.id
                == document_id,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        if not document:

            return {
                "success": False,
                "message":
                    "Document not found"
            }

        pdf_path = get_library_pdf_path(
            document_id
        )

        if pdf_path.exists():

            try:

                pdf_path.unlink()

            except Exception as error:

                print(
                    "PDF DELETE WARNING:",
                    error
                )

        db.delete(
            document
        )

        db.commit()

        state = get_runtime_state(
            current_user.id
        )

        if (
            state[
                "current_library_document_id"
            ]
            == document_id
        ):

            runtime_states[
                current_user.id
            ] = create_empty_runtime_state()

        return {
            "success": True,
            "message":
                "Document removed from your private library"
        }

    except Exception as error:

        db.rollback()

        print(
            "DELETE LIBRARY ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }


def pages_to_persistent_text(
    pages
):
    return "\n\n".join(
        f"PAGE {page['page']}\n{page['text']}"
        for page in pages
        if (
            page.get("text", "")
            or ""
        ).strip()
    )


def load_persistent_pdf_cache(
    user_id,
    content_hash
):
    try:
        with engine.connect() as connection:
            row = connection.execute(
                sql_text(
                    """
                    SELECT
                        filename,
                        extracted_text,
                        total_pages,
                        pages_with_text,
                        uncached_processing_ms
                    FROM processed_pdf_cache
                    WHERE user_id = :user_id
                      AND content_hash = :content_hash
                    LIMIT 1
                    """
                ),
                {
                    "user_id": user_id,
                    "content_hash": content_hash
                }
            ).mappings().first()

        if not row:
            return None

        pages = parse_saved_pages(
            row["extracted_text"]
        )

        pages = [
            {
                "page": page.get("page"),
                "text": (
                    page.get("text", "")
                    or ""
                ).strip()
            }
            for page in pages
            if (
                page.get("text", "")
                or ""
            ).strip()
        ]

        if not pages:
            return None

        return {
            "filename": row["filename"],
            "pages": pages,
            "total_pages":
                row["total_pages"]
                or len(pages),
            "pages_with_text":
                row["pages_with_text"]
                or len(pages),
            "uncached_processing_ms":
                row["uncached_processing_ms"]
        }

    except Exception as error:
        print(
            "PERSISTENT CACHE READ ERROR:",
            error,
            flush=True
        )
        return None

def save_persistent_pdf_cache(
    user_id,
    content_hash,
    filename,
    pages,
    total_pages,
    uncached_processing_ms=None
):
    full_text = pages_to_persistent_text(
        pages
    )

    if not full_text.strip():
        return

    try:
        with engine.begin() as connection:
            connection.execute(
                sql_text(
                    """
                    INSERT INTO processed_pdf_cache (
                        user_id,
                        content_hash,
                        filename,
                        extracted_text,
                        total_pages,
                        pages_with_text,
                        uncached_processing_ms
                    )
                    VALUES (
                        :user_id,
                        :content_hash,
                        :filename,
                        :extracted_text,
                        :total_pages,
                        :pages_with_text,
                        :uncached_processing_ms
                    )
                    ON CONFLICT (user_id, content_hash)
                    DO UPDATE SET
                        filename = EXCLUDED.filename,
                        extracted_text = EXCLUDED.extracted_text,
                        total_pages = EXCLUDED.total_pages,
                        pages_with_text = EXCLUDED.pages_with_text,
                        uncached_processing_ms = COALESCE(
                            EXCLUDED.uncached_processing_ms,
                            processed_pdf_cache.uncached_processing_ms
                        )
                    """
                ),
                {
                    "user_id": user_id,
                    "content_hash": content_hash,
                    "filename": filename,
                    "extracted_text": full_text,
                    "total_pages": total_pages,
                    "pages_with_text": len(pages),
                    "uncached_processing_ms":
                        uncached_processing_ms
                }
            )

        print(
            "Persistent PDF cache SAVED",
            flush=True
        )

    except Exception as error:
        print(
            "PERSISTENT CACHE SAVE ERROR:",
            error,
            flush=True
        )


def record_qa_query(
    user_id,
    language
):
    normalized_language = (
        language or "English"
    ).strip().lower()

    english_increment = (
        1 if normalized_language == "english" else 0
    )
    tamil_increment = (
        1 if normalized_language == "tamil" else 0
    )

    try:
        with engine.begin() as connection:
            connection.execute(
                sql_text(
                    """
                    INSERT INTO app_usage_metrics (
                        user_id,
                        qa_queries,
                        english_queries,
                        tamil_queries,
                        first_query_at,
                        last_query_at
                    )
                    VALUES (
                        :user_id,
                        1,
                        :english_increment,
                        :tamil_increment,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        qa_queries = app_usage_metrics.qa_queries + 1,
                        english_queries = app_usage_metrics.english_queries + :english_increment,
                        tamil_queries = app_usage_metrics.tamil_queries + :tamil_increment,
                        last_query_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "user_id": user_id,
                    "english_increment": english_increment,
                    "tamil_increment": tamil_increment
                }
            )
    except Exception as error:
        print(
            "USAGE METRICS ERROR:",
            error,
            flush=True
        )

def activate_processed_pages(
    user_id,
    filename,
    file_bytes,
    extracted_pages,
    total_pages
):
    current_chunks = chunk_pages(
        extracted_pages
    )

    current_index = build_faiss_index(
        current_chunks
    )

    state = get_runtime_state(
        user_id
    )

    state["current_pdf_bytes"] = (
        file_bytes
    )
    state[
        "current_library_document_id"
    ] = None
    state["current_pages"] = (
        extracted_pages
    )
    state["current_chunks"] = (
        current_chunks
    )
    state["current_index"] = (
        current_index
    )
    state["current_filename"] = (
        filename
    )

    total_characters = sum(
        len(page["text"])
        for page in extracted_pages
    )

    preview = (
        extracted_pages[0]["text"][:1200]
    )

    return {
        "success": True,
        "message":
            "PDF processed and indexed successfully",
        "filename":
            filename,
        "total_pages":
            total_pages,
        "pages_with_text":
            len(extracted_pages),
        "total_characters":
            total_characters,
        "total_chunks":
            len(current_chunks),
        "retrieval_method":
            "TF-IDF + BM25 Hybrid Search",
        "preview":
            preview,
        "pdf_available":
            True
    }


def process_pdf_job(
    job_id,
    user_id,
    filename,
    file_bytes,
    content_hash
):
    job_start = time.perf_counter()
    job = processing_jobs[job_id]
    state = get_runtime_state(
        user_id
    )

    state["processing_job_id"] = job_id
    state["processing_complete"] = False
    state["current_pdf_bytes"] = file_bytes
    state["current_filename"] = filename
    state["current_library_document_id"] = None

    try:
        cached = load_persistent_pdf_cache(
            user_id,
            content_hash
        )

        if cached:
            job["status"] = "processing"
            job["message"] = (
                "Previously processed document found. Loading instantly..."
            )

            job["result"] = activate_processed_pages(
                user_id,
                filename,
                file_bytes,
                cached["pages"],
                cached["total_pages"]
            )

            cached_processing_ms = (
                time.perf_counter() - job_start
            ) * 1000.0

            job["result"]["cache_hit"] = True
            job["result"]["processing_complete"] = True
            job["result"]["ready_for_questions"] = True
            job["result"]["processing_time_ms"] = round(
                cached_processing_ms,
                2
            )

            historical_uncached_ms = (
                cached.get("uncached_processing_ms")
            )

            if (
                historical_uncached_ms
                and historical_uncached_ms > 0
            ):
                improvement = (
                    (historical_uncached_ms - cached_processing_ms)
                    / historical_uncached_ms
                ) * 100.0

                job["result"]["previous_uncached_processing_ms"] = round(
                    historical_uncached_ms,
                    2
                )
                job["result"]["cache_speedup_x"] = round(
                    historical_uncached_ms
                    / max(cached_processing_ms, 0.001),
                    2
                )
                job["result"]["cache_time_reduction_percent"] = round(
                    max(0.0, improvement),
                    2
                )

            state["processing_complete"] = True

            job["status"] = "completed"
            job["message"] = (
                "Document ready — OCR was skipped"
            )

            print(
                "PERSISTENT PDF CACHE HIT: OCR skipped",
                flush=True
            )
            return

        job["status"] = "processing"
        job["message"] = (
            "New document detected. Extracting text..."
        )
        job["ready_for_questions"] = False
        job["partial_result"] = None

        latest_pages = []

        def progressive_update(
            pages,
            stage,
            completed
        ):
            nonlocal latest_pages

            extracted_pages = [
                page
                for page in pages
                if (
                    page.get("text", "")
                    or ""
                ).strip()
            ]

            if not extracted_pages:
                job["message"] = stage
                return

            latest_pages = extracted_pages

            # Rebuild only a small current-document index. MAX_OCR_PAGES is
            # already tiny, so this is much cheaper than waiting for OCR.
            partial_result = activate_processed_pages(
                user_id,
                filename,
                file_bytes,
                extracted_pages,
                len(pages)
            )

            partial_result["cache_hit"] = False
            partial_result[
                "processing_complete"
            ] = bool(completed)
            partial_result[
                "ready_for_questions"
            ] = True

            job["partial_result"] = partial_result
            job["ready_for_questions"] = True
            job["message"] = stage

            print(
                "PROGRESSIVE READY:",
                stage,
                "| searchable pages:",
                len(extracted_pages),
                flush=True
            )

        pages = extract_pdf_text_progressive(
            file_bytes,
            on_update=progressive_update,
            quick_ocr_pages=1
        )

        extracted_pages = [
            page
            for page in pages
            if (
                page.get("text", "")
                or ""
            ).strip()
        ]

        if not extracted_pages:
            job["status"] = "failed"
            job["message"] = (
                "No readable text found in this PDF"
            )
            state["processing_complete"] = True
            return

        job["message"] = (
            "Finishing document search index..."
        )

        result = activate_processed_pages(
            user_id,
            filename,
            file_bytes,
            extracted_pages,
            len(pages)
        )

        uncached_processing_ms = (
            time.perf_counter() - job_start
        ) * 1000.0

        save_persistent_pdf_cache(
            user_id,
            content_hash,
            filename,
            extracted_pages,
            len(pages),
            uncached_processing_ms=uncached_processing_ms
        )

        result["cache_hit"] = False
        result["processing_time_ms"] = round(
            uncached_processing_ms,
            2
        )
        result["processing_complete"] = True
        result["ready_for_questions"] = True

        job["result"] = result
        job["partial_result"] = result
        job["ready_for_questions"] = True
        job["status"] = "completed"
        job["message"] = (
            "Document processed successfully"
        )

        state["processing_complete"] = True

    except Exception as error:
        print(
            "BACKGROUND PDF ERROR:",
            error,
            flush=True
        )

        job["status"] = "failed"
        job["message"] = str(error)
        state["processing_complete"] = True

    finally:
        gc.collect()


@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user:
        User = Depends(
            get_current_user
        )
):

    if (
        file.content_type
        != "application/pdf"
    ):
        return {
            "success": False,
            "message":
                "Please upload a PDF file"
        }

    try:
        file_bytes = await file.read()

        if not file_bytes:
            return {
                "success": False,
                "message":
                    "The uploaded PDF is empty"
            }

        content_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        job_id = uuid.uuid4().hex

        processing_jobs[job_id] = {
            "user_id":
                current_user.id,
            "status":
                "queued",
            "message":
                "PDF uploaded. Processing is starting...",
            "result":
                None,
            "partial_result":
                None,
            "ready_for_questions":
                False
        }

        worker = threading.Thread(
            target=process_pdf_job,
            args=(
                job_id,
                current_user.id,
                file.filename,
                file_bytes,
                content_hash
            ),
            daemon=True
        )

        worker.start()

        return {
            "success": True,
            "processing": True,
            "job_id": job_id,
            "message":
                "PDF uploaded. Processing continues in the background."
        }

    except Exception as error:
        print(
            "PDF UPLOAD ERROR:",
            error,
            flush=True
        )

        return {
            "success": False,
            "message": str(error)
        }


@app.get("/upload-status/{job_id}")
def upload_status(
    job_id: str,
    current_user:
        User = Depends(
            get_current_user
        )
):
    job = processing_jobs.get(
        job_id
    )

    if (
        not job
        or job.get("user_id")
        != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Processing job not found"
        )

    response = {
        "success": True,
        "status": job["status"],
        "message": job["message"],
        "ready_for_questions":
            bool(
                job.get(
                    "ready_for_questions",
                    False
                )
            ),
        "processing_complete":
            job["status"] == "completed"
    }

    partial_result = job.get(
        "partial_result"
    )

    if partial_result:
        response[
            "partial_result"
        ] = partial_result

    if job["status"] == "completed":
        response["result"] = job["result"]

        # Keep completed jobs briefly in memory rather than popping here.
        # The frontend can poll more than once without receiving a false 404.
        job["completed_at"] = job.get(
            "completed_at",
            time.time()
        )

    elif job["status"] == "failed":
        response["success"] = False

    return response


def create_language_instruction(
    language
):

    if language.lower() == "tamil":

        return {
            "instruction": """
You MUST answer in clear and simple Tamil.

Use natural Tamil that an ordinary citizen can understand.

Avoid unnecessary English words whenever possible.

Preserve Government Order numbers, dates, department names,
amounts and official technical terms accurately.
""",

            "unavailable": (
                "இந்த கேள்விக்கு பதிலளிக்க தேவையான "
                "போதுமான தகவல் பதிவேற்றப்பட்ட "
                "ஆவணத்தில் இல்லை."
            )
        }


    return {
        "instruction": """
You MUST answer in clear and simple English.
""",

        "unavailable": (
            "The uploaded document does not provide enough "
            "information to answer this question."
        )
    }


def call_openrouter(
    prompt,
    max_tokens=1200
):

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )


    if not api_key:

        return {
            "success": False,
            "message":
                "OPENROUTER_API_KEY is missing"
        }


    headers = {
        "Authorization":
            f"Bearer {api_key}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "http://localhost:5173",

        "X-OpenRouter-Title":
            "TN Insight AI"
    }


    payload = {
        "model":
            "openrouter/free",

        "messages": [
            {
                "role":
                    "system",

                "content":
                    "You are a grounded government document intelligence assistant."
            },
            {
                "role":
                    "user",

                "content":
                    prompt
            }
        ],

        "temperature":
            0.1,

        "max_tokens":
            max_tokens
    }


    try:

        for attempt in range(2):

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90
            )


            try:
                data = response.json()

            except Exception:

                print(
                    "OPENROUTER NON-JSON RESPONSE:",
                    response.text
                )

                continue


            if not response.ok:

                print(
                    "OPENROUTER ERROR:",
                    data
                )


                message = (
                    data
                    .get(
                        "error",
                        {}
                    )
                    .get(
                        "message",
                        "AI service failed"
                    )
                )


                return {
                    "success": False,
                    "message":
                        message
                }


            choices = data.get(
                "choices",
                []
            )


            if not choices:

                print(
                    "No AI choices returned. Retrying..."
                )

                continue


            message = (
                choices[0]
                .get(
                    "message",
                    {}
                )
            )


            answer = message.get(
                "content"
            )


            if isinstance(
                answer,
                list
            ):

                text_parts = []

                for part in answer:

                    if isinstance(
                        part,
                        dict
                    ):

                        text = part.get(
                            "text"
                        )

                        if text:
                            text_parts.append(
                                text
                            )


                answer = "\n".join(
                    text_parts
                )


            if answer:

                answer = (
                    answer.strip()
                )


            if answer:

                return {
                    "success": True,
                    "answer":
                        answer
                }


            print(
                f"Empty AI response attempt {attempt + 1}. Retrying..."
            )


        return {
            "success": False,

            "message":
                "The free AI model returned an empty response. Please try again."
        }


    except requests.exceptions.Timeout:

        return {
            "success": False,

            "message":
                "AI request timed out. Please try again."
        }


    except Exception as error:

        print(
            "AI ERROR:",
            error
        )


        return {
            "success": False,
            "message": str(error)
        }


def generate_ai_answer(
    question,
    results,
    language,
    filename
):

    context_parts = []


    for item in results:

        context_parts.append(
            f"""
PAGE {item['page']}

{item['text']}
"""
        )


    context = "\n\n".join(
        context_parts
    )


    language_data = (
        create_language_instruction(
            language
        )
    )


    prompt = f"""
You are TN Insight AI.

You help citizens, students, researchers and public policy users
understand Tamil Nadu Government documents.

You must answer ONLY using the retrieved document context.

OUTPUT LANGUAGE:

{language_data["instruction"]}

STRICT RULES:

1. Use ONLY information supported by the retrieved document context.

2. Do NOT invent facts.

3. Do NOT use outside knowledge.

4. If the answer cannot be found, reply:

"{language_data["unavailable"]}"

5. Mention relevant page numbers.

6. Keep the answer easy to understand.

7. Use bullet points when useful.

8. Preserve important dates, numbers, Government Order numbers,
department names and eligibility conditions accurately.

9. Do not claim that TN Insight AI is an official Government service.

10. Do not provide unsupported legal, financial or policy conclusions.

11. When extracting eligibility, deadlines or required documents,
clearly separate each item.

12. Cite pages using formats such as:

[Page 3]

or

[Pages 3, 5]


DOCUMENT:

{filename}


RETRIEVED DOCUMENT CONTEXT:

{context}


USER QUESTION:

{question}
"""


    return call_openrouter(
        prompt,
        max_tokens=1000
    )


@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    current_user:
        User = Depends(
            get_current_user
        )
):

    state = get_runtime_state(
        current_user.id
    )

    question = (
        request.question.strip()
    )

    language = (
        request.language.strip()
        if request.language
        else "English"
    )

    if not question:

        return {
            "success": False,
            "message":
                "Question is required"
        }

    current_chunks = (
        state["current_chunks"]
    )

    if not current_chunks:

        return {
            "success": False,
            "message":
                "Please upload and process a PDF first"
        }

    try:

        current_index = (
            build_faiss_index(
                current_chunks
            )
        )

        state[
            "current_index"
        ] = current_index

        results = search_chunks(
            question,
            current_chunks,
            current_index,
            top_k=5
        )

        if not results:

            return {
                "success": False,
                "message":
                    "No relevant information was found"
            }

        ai_result = (
            generate_ai_answer(
                question,
                results,
                language,
                state[
                    "current_filename"
                ]
            )
        )

        if not ai_result["success"]:

            return {
                "success": False,
                "message":
                    ai_result["message"]
            }

        record_qa_query(
            current_user.id,
            language
        )

        sources = []
        seen_pages = set()

        for item in results:

            if (
                item["page"]
                not in seen_pages
            ):

                sources.append({
                    "page":
                        item["page"],
                    "score":
                        item["score"],
                    "tfidf_score":
                        item.get(
                            "tfidf_score",
                            0
                        ),
                    "bm25_score":
                        item.get(
                            "bm25_score",
                            0
                        )
                })

                seen_pages.add(
                    item["page"]
                )

        return {
            "success": True,
            "question":
                question,
            "language":
                language,
            "document":
                state[
                    "current_filename"
                ],
            "answer":
                ai_result[
                    "answer"
                ],
            "retrieval_method":
                "TF-IDF + BM25 Hybrid Search",
            "sources":
                sources,
            "results":
                results
        }

    except Exception as error:

        print(
            "ASK ERROR:",
            error
        )

        return {
            "success": False,
            "message":
                str(error)
        }

def get_cached_pdf_pages(
    file_bytes,
    extractor,
    cache_namespace="default"
):
    """
    Reuse extracted text for the same PDF during the lifetime of this
    Render process. The cache is intentionally small to limit memory use.
    """
    pdf_hash = hashlib.sha256(file_bytes).hexdigest()
    cache_key = f"{cache_namespace}:{pdf_hash}"

    cached = pdf_extraction_cache.get(cache_key)
    if cached is not None:
        print(
            f"PDF extraction cache HIT: {cache_namespace}",
            flush=True
        )
        return [
            {
                "page": item["page"],
                "text": item["text"]
            }
            for item in cached
        ]

    print(
        f"PDF extraction cache MISS: {cache_namespace}",
        flush=True
    )

    pages = extractor(file_bytes)

    if pages:
        safe_pages = [
            {
                "page": item.get("page"),
                "text": item.get("text", "")
            }
            for item in pages
            if item.get("text", "").strip()
        ]

        if len(pdf_extraction_cache) >= MAX_PDF_CACHE_ITEMS:
            oldest_key = next(iter(pdf_extraction_cache))
            pdf_extraction_cache.pop(oldest_key, None)

        pdf_extraction_cache[cache_key] = safe_pages
        return [
            {
                "page": item["page"],
                "text": item["text"]
            }
            for item in safe_pages
        ]

    return []


def extract_pdf_text_for_comparison(
    file_bytes,
    max_pages=40,
    max_chars_per_page=8000
):

    pages = []
    pdf_document = None

    try:

        pdf_document = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )

        total_pages = min(
            len(pdf_document),
            max_pages
        )

        for page_index in range(
            total_pages
        ):

            page = pdf_document.load_page(
                page_index
            )

            text_value = (
                page.get_text(
                    "text"
                )
                or ""
            ).strip()

            if not text_value:
                continue

            if len(text_value) > max_chars_per_page:
                text_value = text_value[
                    :max_chars_per_page
                ]

            pages.append({
                "page":
                    page_index + 1,
                "text":
                    text_value
            })

            del page

        return pages

    except Exception as error:

        print(
            "LIGHTWEIGHT PDF EXTRACTION ERROR:",
            error,
            flush=True
        )

        return []

    finally:

        if pdf_document is not None:

            try:
                pdf_document.close()
            except Exception:
                pass

        gc.collect()


def prepare_comparison_document(
    file_bytes,
    filename
):

    pages = get_cached_pdf_pages(
        file_bytes,
        extract_pdf_text_for_comparison,
        cache_namespace="comparison-text"
    )

    # Scanned/image-only PDFs have no embedded text.
    # Fall back to the existing OCR pipeline from pdf_utils.py.
    if not pages:
        print(
            "Comparison PDF has no embedded text. Falling back to OCR...",
            flush=True
        )
        pages = extract_pdf_text(
            file_bytes
        )

    extracted_pages = []

    for page in pages:

        text_value = (
            page.get(
                "text",
                ""
            )
            or ""
        ).strip()

        if not text_value:
            continue

        if len(text_value) > 12000:
            text_value = text_value[:12000]

        extracted_pages.append({
            "page":
                page.get(
                    "page"
                ),
            "text":
                text_value
        })

    del pages
    gc.collect()

    if not extracted_pages:
        return None

    chunks = chunk_pages(
        extracted_pages
    )

    if len(chunks) > 160:
        chunks = chunks[:160]

    total_pages = len(
        extracted_pages
    )

    del extracted_pages
    gc.collect()

    return {
        "filename":
            filename,
        "total_pages":
            total_pages,
        "chunks":
            chunks
    }

def select_comparison_chunks(
    chunks,
    top_k=10
):

    if not chunks:
        return []


    texts = [
        item["text"]
        for item in chunks
    ]


    comparison_query = """
purpose policy eligibility beneficiary beneficiaries
conditions criteria amount fee financial assistance
deadline date dates time period application
required documents certificates forms proof
department authority institution students employees citizens
amendment change revision revised removed added new provision
government order scheme rules regulations
"""


    try:

        vectorizer = TfidfVectorizer(
            max_features=2500,
            ngram_range=(1, 1),
            dtype=np.float32
        )


        matrix = (
            vectorizer.fit_transform(
                texts + [
                    comparison_query
                ]
            )
        )


        query_vector = (
            matrix[-1]
        )

        document_vectors = (
            matrix[:-1]
        )


        scores = cosine_similarity(
            query_vector,
            document_vectors
        )[0]


        top_k = min(
            top_k,
            len(chunks)
        )


        indices = (
            scores
            .argsort()[::-1][:top_k]
        )


        selected = []


        for idx in indices:

            item = chunks[idx]


            selected.append({
                "page":
                    item["page"],

                "text":
                    item["text"],

                "score":
                    float(
                        scores[idx]
                    )
            })


        return selected


    except Exception as error:

        print(
            "COMPARISON RETRIEVAL ERROR:",
            error
        )

        return chunks[:top_k]


def create_comparison_context(
    results,
    label
):

    parts = []


    for item in results:

        parts.append(
            f"""
{label} - PAGE {item['page']}

{item['text']}
"""
        )


    return "\n\n".join(
        parts
    )


def remove_reasoning_leakage(
    answer
):

    if not answer:
        return answer

    cleaned = answer.strip()

    leak_markers = [
        "Here's a thinking process:",
        "Here is a thinking process:",
        "Thinking process:",
        "Analyze User Request:",
        "Let me think",
        "I need to",
        "We need to",
        "I should",
        "Re-read rule",
        "Let me re-read",
        "The best approach is",
        "I think I should"
    ]

    lowered = cleaned.lower()

    for marker in leak_markers:

        marker_lower = marker.lower()

        if marker_lower in lowered:

            # If the model later starts a likely final-answer section,
            # keep only that part.
            final_markers = [
                "ஒட்டுமொத்த நோக்கம்",
                "இறுதி சுருக்கம்",
                "ஆவணம் A",
                "Document A",
                "Overall Purpose",
                "Final Summary"
            ]

            found_positions = []

            for final_marker in final_markers:

                position = cleaned.find(
                    final_marker
                )

                if position != -1:
                    found_positions.append(
                        position
                    )

            if found_positions:

                cleaned = cleaned[
                    min(found_positions):
                ].strip()

            else:
                return ""

            break

    return cleaned


def rewrite_comparison_to_tamil(
    comparison_text
):

    if not comparison_text:
        return {
            "success": False,
            "message":
                "Comparison text is empty"
        }

    prompt = f"""
You are a Tamil language editor for TN Insight AI.

Your only task is to rewrite the comparison below into clear, simple Tamil.

STRICT OUTPUT RULES:

1. Return ONLY the final Tamil comparison.
2. Do NOT show analysis, reasoning, planning, thinking process, hidden steps, or instructions.
3. Do NOT say phrases such as:
   - "Here's a thinking process"
   - "Analyze User Request"
   - "Let me think"
   - "I need to"
4. Translate all headings and explanations into Tamil.
5. Keep official Government Order numbers, dates, amounts, road names,
   project names, department names, abbreviations and technical identifiers
   unchanged where translation could reduce accuracy.
6. Preserve every page citation exactly in meaning.
7. Do not add new facts.
8. Do not remove supported facts.
9. Do not treat Document A as "old" and Document B as "new"
   unless the source comparison explicitly proves that relationship.
10. If the documents are unrelated projects, present them simply as
    "ஆவணம் A" and "ஆவணம் B" and explain that they are separate projects.
11. Use concise headings such as:
    - ஒட்டுமொத்த நோக்கம்
    - முக்கிய ஒற்றுமைகள்
    - முக்கிய வேறுபாடுகள்
    - நிதி / தொகை
    - தேதி / நிர்வாக அனுமதி
    - துறை / அதிகார அமைப்பு
    - இறுதி சுருக்கம்
12. Before returning, verify that explanatory prose is in Tamil.

COMPARISON TO REWRITE:

{comparison_text}
"""

    return call_openrouter(
        prompt,
        max_tokens=1800
    )



def prepare_saved_library_document(
    document
):
    """
    Build comparison chunks directly from text already stored in Neon.
    This path performs NO PDF extraction and NO OCR.
    """
    if (
        document is None
        or not document.extracted_text
        or not document.extracted_text.strip()
    ):
        return None

    pages = parse_saved_pages(
        document.extracted_text
    )

    pages = [
        {
            "page": page.get("page"),
            "text": (
                page.get("text", "")
                or ""
            ).strip()
        }
        for page in pages
        if (
            page.get("text", "")
            or ""
        ).strip()
    ]

    if not pages:
        return None

    chunks = chunk_pages(
        pages
    )

    if len(chunks) > 160:
        chunks = chunks[:160]

    return {
        "filename":
            document.filename,
        "total_pages":
            document.total_pages
            or len(pages),
        "chunks":
            chunks
    }


def generate_fast_comparison(
    document_a,
    document_b,
    language
):
    results_a = select_comparison_chunks(
        document_a["chunks"],
        top_k=6
    )

    results_b = select_comparison_chunks(
        document_b["chunks"],
        top_k=6
    )

    context_a = create_comparison_context(
        results_a,
        "DOCUMENT A"
    )

    context_b = create_comparison_context(
        results_b,
        "DOCUMENT B"
    )

    language_data = create_language_instruction(
        language
    )

    prompt = f"""
You are TN Insight AI.

Compare two Tamil Nadu Government documents using ONLY the supplied context.

OUTPUT LANGUAGE:
{language_data["instruction"]}

STRICT RULES:
1. Return ONLY the final comparison.
2. Do not reveal reasoning or chain-of-thought.
3. Do not invent facts or use outside knowledge.
4. Preserve Government Order numbers, dates, amounts, department names,
   road names, locations and technical identifiers accurately.
5. Clearly distinguish Document A from Document B.
6. Include relevant page citations from BOTH documents.
7. Do not describe A as old and B as new unless the context proves that
   they are versions of the same policy/order/project.
8. If they are unrelated, say that they are separate documents/projects.
9. Keep the answer concise so the comparison returns quickly.
10. Do not claim TN Insight AI is an official Government service.

If Tamil is selected, write the complete explanation in clear Tamil.
Keep official names, GO numbers, dates, amounts, abbreviations and necessary
technical identifiers unchanged where translation could reduce accuracy.

DOCUMENT A:
{document_a["filename"]}

DOCUMENT A CONTEXT:
{context_a}

DOCUMENT B:
{document_b["filename"]}

DOCUMENT B CONTEXT:
{context_b}
"""

    ai_result = call_openrouter(
        prompt,
        max_tokens=1200
    )

    if not ai_result["success"]:
        return {
            "success": False,
            "message":
                ai_result["message"]
        }

    comparison_answer = remove_reasoning_leakage(
        ai_result["answer"]
    )

    if not comparison_answer:
        comparison_answer = (
            ai_result["answer"]
            or ""
        ).strip()

    if not comparison_answer:
        return {
            "success": False,
            "message":
                "Comparison generation failed. Please try again."
        }

    sources_a = []
    seen_a = set()

    for item in results_a:
        page = item.get("page")
        if page not in seen_a:
            sources_a.append({
                "page": page
            })
            seen_a.add(page)

    sources_b = []
    seen_b = set()

    for item in results_b:
        page = item.get("page")
        if page not in seen_b:
            sources_b.append({
                "page": page
            })
            seen_b.add(page)

    return {
        "success": True,
        "message":
            "Saved documents compared successfully",
        "fast_mode": True,
        "document_a": {
            "filename":
                document_a["filename"],
            "total_pages":
                document_a["total_pages"]
        },
        "document_b": {
            "filename":
                document_b["filename"],
            "total_pages":
                document_b["total_pages"]
        },
        "language":
            language,
        "comparison":
            comparison_answer,
        "sources_a":
            sources_a,
        "sources_b":
            sources_b,
        "evidence_a":
            results_a,
        "evidence_b":
            results_b
    }


@app.post("/compare-library-documents")
def compare_library_documents(
    request: LibraryComparisonRequest,
    db: Session = Depends(
        get_db
    ),
    current_user:
        User = Depends(
            get_current_user
        )
):
    """
    Super-fast comparison path for documents that have already been
    processed and saved. OCR is never run here.
    """
    if (
        request.document_a_id
        == request.document_b_id
    ):
        return {
            "success": False,
            "message":
                "Please select two different saved documents"
        }

    try:
        saved_a = (
            db.query(Document)
            .filter(
                Document.id
                == request.document_a_id,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        saved_b = (
            db.query(Document)
            .filter(
                Document.id
                == request.document_b_id,
                Document.user_id
                == current_user.id
            )
            .first()
        )

        if not saved_a:
            return {
                "success": False,
                "message":
                    "Saved Document A was not found"
            }

        if not saved_b:
            return {
                "success": False,
                "message":
                    "Saved Document B was not found"
            }

        document_a = (
            prepare_saved_library_document(
                saved_a
            )
        )

        document_b = (
            prepare_saved_library_document(
                saved_b
            )
        )

        if document_a is None:
            return {
                "success": False,
                "message":
                    "Saved Document A has no processed text. Process and save it again."
            }

        if document_b is None:
            return {
                "success": False,
                "message":
                    "Saved Document B has no processed text. Process and save it again."
            }

        # Preserve clickable comparison citations when the saved PDF
        # is still available on this Render instance.
        state = get_runtime_state(
            current_user.id
        )

        path_a = get_library_pdf_path(
            saved_a.id
        )
        path_b = get_library_pdf_path(
            saved_b.id
        )

        state[
            "comparison_pdf_a_bytes"
        ] = (
            path_a.read_bytes()
            if path_a.exists()
            else None
        )

        state[
            "comparison_pdf_b_bytes"
        ] = (
            path_b.read_bytes()
            if path_b.exists()
            else None
        )

        state[
            "comparison_filename_a"
        ] = saved_a.filename

        state[
            "comparison_filename_b"
        ] = saved_b.filename

        print(
            "FAST LIBRARY COMPARISON: using stored extracted text; OCR skipped",
            flush=True
        )

        return generate_fast_comparison(
            document_a,
            document_b,
            request.language
        )

    except Exception as error:
        print(
            "FAST LIBRARY COMPARISON ERROR:",
            error,
            flush=True
        )

        return {
            "success": False,
            "message":
                str(error)
        }


@app.post("/compare-documents")
async def compare_documents(

    file_a:
        UploadFile = File(...),

    file_b:
        UploadFile = File(...),

    language:
        str = Form("English")

):

    print(
        "### NEW COMPARE ENDPOINT HIT ###",
        flush=True
    )

    if (
        file_a.content_type
        != "application/pdf"
        or
        file_b.content_type
        != "application/pdf"
    ):

        return {
            "success": False,
            "message":
                "Please upload two PDF files"
        }

    document_a = None
    document_b = None
    results_a = []
    results_b = []
    context_a = ""
    context_b = ""

    try:

        bytes_a = await file_a.read()

        if len(bytes_a) > 20 * 1024 * 1024:

            return {
                "success": False,
                "message":
                    "Document A is too large. Please use a PDF smaller than 20 MB."
            }

        document_a = (
            prepare_comparison_document(
                bytes_a,
                file_a.filename
            )
        )

        del bytes_a
        gc.collect()

        if document_a is None:

            return {
                "success": False,
                "message":
                    "Document A contains no readable text"
            }

        bytes_b = await file_b.read()

        if len(bytes_b) > 20 * 1024 * 1024:

            return {
                "success": False,
                "message":
                    "Document B is too large. Please use a PDF smaller than 20 MB."
            }

        document_b = (
            prepare_comparison_document(
                bytes_b,
                file_b.filename
            )
        )

        del bytes_b
        gc.collect()

        if document_b is None:

            return {
                "success": False,
                "message":
                    "Document B contains no readable text"
            }

        results_a = (
            select_comparison_chunks(
                document_a["chunks"],
                top_k=6
            )
        )

        results_b = (
            select_comparison_chunks(
                document_b["chunks"],
                top_k=6
            )
        )

        context_a = (
            create_comparison_context(
                results_a,
                "DOCUMENT A"
            )
        )

        context_b = (
            create_comparison_context(
                results_b,
                "DOCUMENT B"
            )
        )

        language_data = (
            create_language_instruction(
                language
            )
        )

        prompt = f"""
You are TN Insight AI.

Compare two Tamil Nadu Government documents using ONLY the supplied context.

OUTPUT LANGUAGE:

{language_data["instruction"]}

ABSOLUTE OUTPUT RULE:

Return ONLY the final comparison answer.

Do NOT reveal analysis, reasoning, planning, scratch work, chain-of-thought,
or phrases such as "Here's a thinking process", "Analyze User Request",
"Let me think", "I need to", or "I should".

DOCUMENT RELATIONSHIP RULE:

First determine from the provided context whether Document A and Document B
are clearly related versions of the same policy/order/project.

- If the documents are clearly an original order and an amendment/revision,
  you may describe supported changes.
- If they are different projects, different schemes, or unrelated orders,
  do NOT describe Document A as "old" and Document B as "new".
- For unrelated documents, compare them side-by-side as Document A and Document B.
- Never imply that one replaces the other unless the documents explicitly say so.

CONTENT RULES:

1. Do NOT invent facts.
2. Compare only information explicitly present in the retrieved context.
3. Preserve Government Order numbers, dates, amounts, department names,
   road names, locations and technical terms accurately.
4. Clearly state which fact belongs to Document A and which belongs to Document B.
5. Include relevant page citations from BOTH documents.
6. If a category cannot be meaningfully compared, say so briefly.
7. Do not claim TN Insight AI is an official Tamil Nadu Government service.

IF THE SELECTED LANGUAGE IS TAMIL:

- Write the entire explanation in clear, natural Tamil.
- Write all headings in Tamil.
- Keep only official names, GO numbers, dates, amounts, abbreviations,
  road identifiers and necessary technical terms in English.
- Do not output English explanatory paragraphs.
- If the documents are unrelated, explicitly say:
  "இந்த இரண்டு ஆவணங்களும் வெவ்வேறு திட்டங்களைப் பற்றியவை; எனவே இது பழையது-புதியது என்ற மாற்ற ஒப்பீடு அல்ல."

Suggested Tamil structure when applicable:

- ஒட்டுமொத்த நோக்கம்
- ஆவணம் A
- ஆவணம் B
- முக்கிய ஒற்றுமைகள்
- முக்கிய வேறுபாடுகள்
- நிதி / தொகை
- தேதி / நிர்வாக அனுமதி
- துறை / அதிகார அமைப்பு
- இறுதி சுருக்கம்

IF THE SELECTED LANGUAGE IS ENGLISH:

Use concise English headings and the same relationship-aware comparison logic.

DOCUMENT A NAME:

{document_a["filename"]}

DOCUMENT A CONTEXT:

{context_a}

DOCUMENT B NAME:

{document_b["filename"]}

DOCUMENT B CONTEXT:

{context_b}
"""

        ai_result = call_openrouter(
            prompt,
            max_tokens=1800
        )

        if not ai_result["success"]:

            return {
                "success": False,
                "message":
                    ai_result["message"]
            }

        comparison_answer = (
            remove_reasoning_leakage(
                ai_result["answer"]
            )
        )

        if (
            language.strip()
            .lower()
            == "tamil"
        ):

            tamil_result = (
                rewrite_comparison_to_tamil(
                    comparison_answer
                    or ai_result[
                        "answer"
                    ]
                )
            )

            if tamil_result["success"]:

                comparison_answer = (
                    remove_reasoning_leakage(
                        tamil_result[
                            "answer"
                        ]
                    )
                )

            if not comparison_answer:

                return {
                    "success": False,
                    "message":
                        "Tamil comparison generation failed. Please try again."
                }

        else:

            if not comparison_answer:

                comparison_answer = (
                    ai_result[
                        "answer"
                    ]
                )

        sources_a = []
        seen_a = set()

        for item in results_a:

            if (
                item["page"]
                not in seen_a
            ):

                sources_a.append({
                    "page":
                        item["page"]
                })

                seen_a.add(
                    item["page"]
                )

        sources_b = []
        seen_b = set()

        for item in results_b:

            if (
                item["page"]
                not in seen_b
            ):

                sources_b.append({
                    "page":
                        item["page"]
                })

                seen_b.add(
                    item["page"]
                )

        response_data = {
            "success": True,
            "message":
                "Documents compared successfully",
            "document_a": {
                "filename":
                    document_a[
                        "filename"
                    ],
                "total_pages":
                    document_a[
                        "total_pages"
                    ]
            },
            "document_b": {
                "filename":
                    document_b[
                        "filename"
                    ],
                "total_pages":
                    document_b[
                        "total_pages"
                    ]
            },
            "language":
                language,
            "comparison":
                comparison_answer,
            "sources_a":
                sources_a,
            "sources_b":
                sources_b,
            "evidence_a":
                results_a,
            "evidence_b":
                results_b
        }

        print(
            "### COMPARE COMPLETED SUCCESSFULLY ###",
            flush=True
        )

        return response_data

    except Exception as error:

        print(
            "COMPARISON ERROR:",
            error,
            flush=True
        )

        return {
            "success": False,
            "message":
                str(error)
        }

    finally:

        context_a = ""
        context_b = ""

        gc.collect()

