def remove_duplicate_pages(
    results
):
    unique_pages = []
    seen_pages = set()

    for result in results:
        page = result["page"]

        if page not in seen_pages:
            unique_pages.append(
                page
            )

            seen_pages.add(
                page
            )

    return unique_pages


def calculate_recall_at_k(
    retrieved_pages,
    relevant_pages,
    k
):
    if not relevant_pages:
        return 0.0

    top_k_pages = (
        retrieved_pages[:k]
    )

    found = any(
        page in relevant_pages
        for page in top_k_pages
    )

    return (
        1.0
        if found
        else 0.0
    )


def calculate_reciprocal_rank(
    retrieved_pages,
    relevant_pages
):
    for rank, page in enumerate(
        retrieved_pages,
        start=1
    ):
        if page in relevant_pages:

            return (
                1.0 / rank
            )

    return 0.0


def evaluate_single_question(
    question,
    relevant_pages,
    chunks,
    index,
    search_function,
    tfidf_weight=0.45,
    bm25_weight=0.55
):
    results = search_function(
        question,
        chunks,
        index,
        top_k=10,
        tfidf_weight=tfidf_weight,
        bm25_weight=bm25_weight
    )

    retrieved_pages = (
        remove_duplicate_pages(
            results
        )
    )

    retrieved_pages = (
        retrieved_pages[:5]
    )

    return {
        "question":
            question,

        "relevant_pages":
            relevant_pages,

        "retrieved_pages":
            retrieved_pages,

        "recall_at_1":
            calculate_recall_at_k(
                retrieved_pages,
                relevant_pages,
                1
            ),

        "recall_at_3":
            calculate_recall_at_k(
                retrieved_pages,
                relevant_pages,
                3
            ),

        "recall_at_5":
            calculate_recall_at_k(
                retrieved_pages,
                relevant_pages,
                5
            ),

        "reciprocal_rank":
            calculate_reciprocal_rank(
                retrieved_pages,
                relevant_pages
            )
    }


def calculate_dataset_metrics(
    details
):
    if not details:

        return {
            "total_questions": 0,
            "recall_at_1": 0,
            "recall_at_3": 0,
            "recall_at_5": 0,
            "mrr": 0,
            "details": []
        }

    total = len(
        details
    )

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

    mrr = sum(
        item[
            "reciprocal_rank"
        ]
        for item in details
    ) / total

    return {
        "total_questions":
            total,

        "recall_at_1":
            round(
                recall_at_1,
                4
            ),

        "recall_at_3":
            round(
                recall_at_3,
                4
            ),

        "recall_at_5":
            round(
                recall_at_5,
                4
            ),

        "mrr":
            round(
                mrr,
                4
            ),

        "details":
            details
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

        return {
            "total_questions": 0,
            "recall_at_1": 0,
            "recall_at_3": 0,
            "recall_at_5": 0,
            "mrr": 0,
            "details": []
        }

    details = []

    for item in (
        evaluation_questions
    ):

        result = (
            evaluate_single_question(
                item["question"],
                item["relevant_pages"],
                chunks,
                index,
                search_function,
                tfidf_weight,
                bm25_weight
            )
        )

        details.append(
            result
        )

    return (
        calculate_dataset_metrics(
            details
        )
    )


def compare_retrieval_methods(
    evaluation_questions,
    chunks,
    index,
    search_function
):
    tfidf_results = (
        evaluate_dataset(
            evaluation_questions,
            chunks,
            index,
            search_function,
            tfidf_weight=1.0,
            bm25_weight=0.0
        )
    )

    bm25_results = (
        evaluate_dataset(
            evaluation_questions,
            chunks,
            index,
            search_function,
            tfidf_weight=0.0,
            bm25_weight=1.0
        )
    )

    hybrid_results = (
        evaluate_dataset(
            evaluation_questions,
            chunks,
            index,
            search_function,
            tfidf_weight=0.45,
            bm25_weight=0.55
        )
    )

    return {
        "tfidf": {
            "recall_at_1":
                tfidf_results[
                    "recall_at_1"
                ],

            "recall_at_3":
                tfidf_results[
                    "recall_at_3"
                ],

            "recall_at_5":
                tfidf_results[
                    "recall_at_5"
                ],

            "mrr":
                tfidf_results[
                    "mrr"
                ]
        },

        "bm25": {
            "recall_at_1":
                bm25_results[
                    "recall_at_1"
                ],

            "recall_at_3":
                bm25_results[
                    "recall_at_3"
                ],

            "recall_at_5":
                bm25_results[
                    "recall_at_5"
                ],

            "mrr":
                bm25_results[
                    "mrr"
                ]
        },

        "hybrid": {
            "recall_at_1":
                hybrid_results[
                    "recall_at_1"
                ],

            "recall_at_3":
                hybrid_results[
                    "recall_at_3"
                ],

            "recall_at_5":
                hybrid_results[
                    "recall_at_5"
                ],

            "mrr":
                hybrid_results[
                    "mrr"
                ]
        }
    }