from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
import numpy as np


vectorizer = None
document_matrix = None
bm25 = None
tokenized_corpus = None


def chunk_pages(pages, chunk_size=1000, overlap=100):
    chunks = []

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "page": page["page"]
                })

            start += chunk_size - overlap

    return chunks


def tokenize_text(text):
    return (
        text.lower()
        .replace("\n", " ")
        .split()
    )


def build_faiss_index(chunks):
    global vectorizer
    global document_matrix
    global bm25
    global tokenized_corpus

    if not chunks:
        return None

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print(
        f"Creating hybrid index for {len(texts)} chunks..."
    )

    vectorizer = TfidfVectorizer(
        max_features=15000,
        ngram_range=(1, 2)
    )

    document_matrix = vectorizer.fit_transform(
        texts
    )

    tokenized_corpus = [
        tokenize_text(text)
        for text in texts
    ]

    bm25 = BM25Okapi(
        tokenized_corpus
    )

    print(
        "TF-IDF + BM25 hybrid indexing completed."
    )

    return True


def normalize_scores(scores):
    scores = np.array(
        scores,
        dtype=np.float32
    )

    if len(scores) == 0:
        return scores

    min_score = scores.min()
    max_score = scores.max()

    if max_score - min_score < 1e-8:
        return np.zeros_like(scores)

    return (
        scores - min_score
    ) / (
        max_score - min_score
    )


def search_chunks(
    question,
    chunks,
    index,
    top_k=5,
    tfidf_weight=0.45,
    bm25_weight=0.55
):
    global vectorizer
    global document_matrix
    global bm25

    if (
        vectorizer is None
        or document_matrix is None
        or bm25 is None
    ):
        return []

    query_vector = vectorizer.transform(
        [question]
    )

    tfidf_scores = cosine_similarity(
        query_vector,
        document_matrix
    )[0]

    tokenized_query = tokenize_text(
        question
    )

    bm25_scores = bm25.get_scores(
        tokenized_query
    )

    tfidf_normalized = normalize_scores(
        tfidf_scores
    )

    bm25_normalized = normalize_scores(
        bm25_scores
    )

    hybrid_scores = (
        tfidf_weight * tfidf_normalized
        +
        bm25_weight * bm25_normalized
    )

    top_k = min(
        top_k,
        len(chunks)
    )

    top_indices = np.argsort(
        hybrid_scores
    )[::-1][:top_k]

    results = []

    for idx in top_indices:
        chunk = chunks[idx]

        results.append({
            "text": chunk["text"],
            "page": chunk["page"],
            "score": float(
                hybrid_scores[idx]
            ),
            "tfidf_score": float(
                tfidf_normalized[idx]
            ),
            "bm25_score": float(
                bm25_normalized[idx]
            )
        })

    return results