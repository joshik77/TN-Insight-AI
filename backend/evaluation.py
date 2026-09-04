import math
import statistics
import time


def remove_duplicate_pages(results):
    unique_pages = []
    seen_pages = set()

    for result in results:
        page = result["page"]

        if page not in seen_pages:
            unique_pages.append(page)
            seen_pages.add(page)

    return unique_pages


def calculate_recall_at_k(retrieved_pages, relevant_pages, k):
    """True Recall@K = relevant pages retrieved in top K / all relevant pages."""
    if not relevant_pages:
        return 0.0

    top_k_pages = set(retrieved_pages[:k])
    relevant_set = set(relevant_pages)

    return len(top_k_pages & relevant_set) / len(relevant_set)


def calculate_hit_at_k(retrieved_pages, relevant_pages, k):
    if not relevant_pages:
        return 0.0

    top_k_pages = set(retrieved_pages[:k])
    relevant_set = set(relevant_pages)

    return 1.0 if top_k_pages & relevant_set else 0.0


def calculate_reciprocal_rank(retrieved_pages, relevant_pages):
    relevant_set = set(relevant_pages)

    for rank, page in enumerate(retrieved_pages, start=1):
        if page in relevant_set:
            return 1.0 / rank

    return 0.0


def percentile(values, percentile_value):
    if not values:
        return 0.0

    ordered = sorted(values)
    position = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil((percentile_value / 100.0) * len(ordered)) - 1
        )
    )

    return ordered[position]


def evaluate_single_question(
    question,
    relevant_pages,
    chunks,
    index,
    search_function,
    tfidf_weight=0.45,
    bm25_weight=0.55
):
    start = time.perf_counter()

    results = search_function(
        question,
        chunks,
        index,
        top_k=10,
        tfidf_weight=tfidf_weight,
        bm25_weight=bm25_weight
    )

    retrieval_latency_ms = (
        time.perf_counter() - start
    ) * 1000.0

    retrieved_pages = remove_duplicate_pages(results)[:5]

    return {
        "question": question,
        "relevant_pages": relevant_pages,
        "retrieved_pages": retrieved_pages,
        "recall_at_1": calculate_recall_at_k(
            retrieved_pages,
            relevant_pages,
            1
        ),
        "recall_at_3": calculate_recall_at_k(
            retrieved_pages,
            relevant_pages,
            3
        ),
        "recall_at_5": calculate_recall_at_k(
            retrieved_pages,
            relevant_pages,
            5
        ),
        "hit_at_1": calculate_hit_at_k(
            retrieved_pages,
            relevant_pages,
            1
        ),
        "hit_at_3": calculate_hit_at_k(
            retrieved_pages,
            relevant_pages,
            3
        ),
        "hit_at_5": calculate_hit_at_k(
            retrieved_pages,
            relevant_pages,
            5
        ),
        "reciprocal_rank": calculate_reciprocal_rank(
            retrieved_pages,
            relevant_pages
        ),
        "retrieval_latency_ms": round(
            retrieval_latency_ms,
            3
        )
    }


def calculate_dataset_metrics(details):
    if not details:
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

    total = len(details)

    recall_at_1 = sum(
        item["recall_at_1"]
        for item in details
    ) / total

    recall_at_3 = sum(
        item["recall_at_3"]
        for item in details
    ) / total

    recall_at_5 = sum(
        item["recall_at_5"]
        for item in details
    ) / total

    hit_at_1 = sum(
        item["hit_at_1"]
        for item in details
    ) / total

    hit_at_3 = sum(
        item["hit_at_3"]
        for item in details
    ) / total

    hit_at_5 = sum(
        item["hit_at_5"]
        for item in details
    ) / total

    mrr = sum(
        item["reciprocal_rank"]
        for item in details
    ) / total

    latencies = [
        item["retrieval_latency_ms"]
        for item in details
    ]

    return {
        "total_questions": total,
        "recall_at_1": round(recall_at_1, 4),
        "recall_at_3": round(recall_at_3, 4),
        "recall_at_5": round(recall_at_5, 4),
        "hit_at_1": round(hit_at_1, 4),
        "hit_at_3": round(hit_at_3, 4),
        "hit_at_5": round(hit_at_5, 4),
        "mrr": round(mrr, 4),
        "average_retrieval_latency_ms": round(
            statistics.mean(latencies),
            3
        ),
        "median_retrieval_latency_ms": round(
            statistics.median(latencies),
            3
        ),
        "p95_retrieval_latency_ms": round(
            percentile(latencies, 95),
            3
        ),
        "details": details
    }


def evaluate_dataset(
    evaluation_questions,
    chunks,
    index,
    search_function,
    tfidf_weight=0.45,
    bm25_weight=0.55
):
    if not evaluation_questions:
        return calculate_dataset_metrics([])

    details = []

    for item in evaluation_questions:
        result = evaluate_single_question(
            item["question"],
            item["relevant_pages"],
            chunks,
            index,
            search_function,
            tfidf_weight,
            bm25_weight
        )

        details.append(result)

    return calculate_dataset_metrics(details)


def compact_method_result(result):
    return {
        "recall_at_1": result["recall_at_1"],
        "recall_at_3": result["recall_at_3"],
        "recall_at_5": result["recall_at_5"],
        "hit_at_1": result["hit_at_1"],
        "hit_at_3": result["hit_at_3"],
        "hit_at_5": result["hit_at_5"],
        "mrr": result["mrr"],
        "average_retrieval_latency_ms": result[
            "average_retrieval_latency_ms"
        ],
        "median_retrieval_latency_ms": result[
            "median_retrieval_latency_ms"
        ],
        "p95_retrieval_latency_ms": result[
            "p95_retrieval_latency_ms"
        ]
    }


def compare_retrieval_methods(
    evaluation_questions,
    chunks,
    index,
    search_function
):
    tfidf_results = evaluate_dataset(
        evaluation_questions,
        chunks,
        index,
        search_function,
        tfidf_weight=1.0,
        bm25_weight=0.0
    )

    bm25_results = evaluate_dataset(
        evaluation_questions,
        chunks,
        index,
        search_function,
        tfidf_weight=0.0,
        bm25_weight=1.0
    )

    hybrid_results = evaluate_dataset(
        evaluation_questions,
        chunks,
        index,
        search_function,
        tfidf_weight=0.45,
        bm25_weight=0.55
    )

    return {
        "tfidf": compact_method_result(tfidf_results),
        "bm25": compact_method_result(bm25_results),
        "hybrid": compact_method_result(hybrid_results)
    }
