from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.retrieval_service import (
    build_application_query_text,
    embed_text,
    fuse_ranked_chunks_with_rrf,
    score_text_by_keyword_overlap,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline benchmark for keyword vs semantic retrieval."
    )
    parser.add_argument(
        "--eval-file",
        type=Path,
        default=Path("evals/retrieval_eval.sample.json"),
        help="Path to the labeled retrieval eval file.",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=Path("evals/retrieval_embedding_cache.json"),
        help="Path to the local embedding cache JSON file.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of chunks to retrieve for each query.",
    )
    parser.add_argument(
        "--skip-semantic",
        action="store_true",
        help="Run only the keyword baseline and skip embedding-based retrieval.",
    )
    parser.add_argument(
        "--show-per-query",
        action="store_true",
        help="Print per-query rankings and metrics.",
    )
    return parser.parse_args()


def load_eval_file(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        payload = json.load(handle)

    if not isinstance(payload.get("corpus"), list) or not isinstance(payload.get("queries"), list):
        raise ValueError("Eval file must contain 'corpus' and 'queries' lists.")

    return payload


def build_query_text(query: dict[str, Any]) -> str:
    direct_text = str(query.get("query_text", "") or "").strip()
    if direct_text:
        return direct_text

    application = query.get("application")
    if not isinstance(application, dict):
        raise ValueError(
            f"Query '{query.get('id', '<unknown>')}' must define either query_text or application."
        )

    app_namespace = SimpleNamespace(
        role_title=application.get("role_title"),
        company=application.get("company"),
        ai_summary=application.get("ai_summary"),
        required_skills=application.get("required_skills"),
        preferred_skills=application.get("preferred_skills"),
        keywords=application.get("keywords"),
        job_description=application.get("job_description"),
    )
    return build_application_query_text(app_namespace)


def normalize_relevance(query: dict[str, Any]) -> dict[str, int]:
    if isinstance(query.get("relevance"), dict):
        return {
            str(chunk_id): int(score)
            for chunk_id, score in query["relevance"].items()
            if int(score) > 0
        }

    if isinstance(query.get("relevant_ids"), list):
        return {str(chunk_id): 1 for chunk_id in query["relevant_ids"]}

    raise ValueError(
        f"Query '{query.get('id', '<unknown>')}' must define either relevance or relevant_ids."
    )


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding lengths do not match.")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0

    dot_product = sum(a * b for a, b in zip(left, right))
    return dot_product / (left_norm * right_norm)


def load_cache(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}

    with path.open() as handle:
        payload = json.load(handle)

    return {
        str(key): [float(value) for value in embedding]
        for key, embedding in payload.items()
    }


def save_cache(path: Path, cache: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(cache, handle)


def embedding_cache_key(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"text-embedding-3-small:{digest}"


def get_embedding_for_text(
    *,
    text: str,
    cache: dict[str, list[float]],
) -> list[float]:
    key = embedding_cache_key(text)
    if key not in cache:
        cache[key] = embed_text(text)
    return cache[key]


def precision_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    hits = sum(1 for chunk_id in ranked_ids[:k] if relevance.get(chunk_id, 0) > 0)
    return hits / max(k, 1)


def recall_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    relevant_total = sum(1 for score in relevance.values() if score > 0)
    if relevant_total == 0:
        return 0.0

    hits = sum(1 for chunk_id in ranked_ids[:k] if relevance.get(chunk_id, 0) > 0)
    return hits / relevant_total


def reciprocal_rank(ranked_ids: list[str], relevance: dict[str, int]) -> float:
    for index, chunk_id in enumerate(ranked_ids, start=1):
        if relevance.get(chunk_id, 0) > 0:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    def dcg(scores: list[int]) -> float:
        total = 0.0
        for index, score in enumerate(scores, start=1):
            total += (2 ** score - 1) / math.log2(index + 1)
        return total

    observed_scores = [relevance.get(chunk_id, 0) for chunk_id in ranked_ids[:k]]
    ideal_scores = sorted(relevance.values(), reverse=True)[:k]
    ideal = dcg(ideal_scores)
    if ideal == 0:
        return 0.0
    return dcg(observed_scores) / ideal


def average_metric(rows: list[dict[str, float]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(row[key] for row in rows) / len(rows)


def rank_keyword(
    *,
    query_text: str,
    corpus: list[dict[str, Any]],
    top_k: int,
) -> list[str]:
    scored = []

    for item in corpus:
        score = score_text_by_keyword_overlap(query_text, item["text"])
        if score[0] == 0:
            continue
        scored.append((score, item["id"]))

    scored.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1]))
    return [item_id for _, item_id in scored[:top_k]]


def rank_semantic(
    *,
    query_text: str,
    corpus: list[dict[str, Any]],
    cache: dict[str, list[float]],
    top_k: int,
) -> list[str]:
    query_embedding = get_embedding_for_text(text=query_text, cache=cache)
    scored = []

    for item in corpus:
        item_embedding = get_embedding_for_text(text=item["text"], cache=cache)
        similarity = cosine_similarity(query_embedding, item_embedding)
        scored.append((similarity, item["id"]))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item_id for _, item_id in scored[:top_k]]


def rank_hybrid(
    *,
    query_text: str,
    corpus: list[dict[str, Any]],
    cache: dict[str, list[float]],
    top_k: int,
) -> list[str]:
    keyword_ranked_ids = rank_keyword(
        query_text=query_text,
        corpus=corpus,
        top_k=max(top_k, 10),
    )
    semantic_ranked_ids = rank_semantic(
        query_text=query_text,
        corpus=corpus,
        cache=cache,
        top_k=max(top_k, 10),
    )

    corpus_by_id = {item["id"]: item for item in corpus}

    def to_chunks(ranked_ids: list[str]) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(id=item_id, chunk_text=corpus_by_id[item_id]["text"])
            for item_id in ranked_ids
            if item_id in corpus_by_id
        ]

    fused = fuse_ranked_chunks_with_rrf(
        ranked_lists=[to_chunks(semantic_ranked_ids), to_chunks(keyword_ranked_ids)],
        top_k=top_k,
    )
    return [chunk.id for chunk in fused]


def evaluate_method(
    *,
    method_name: str,
    corpus: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    top_k: int,
    cache: dict[str, list[float]] | None = None,
    show_per_query: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, float]] = []
    rankings: dict[str, list[str]] = {}

    for query in queries:
        query_text = build_query_text(query)
        relevance = normalize_relevance(query)

        if method_name == "keyword":
            ranked_ids = rank_keyword(query_text=query_text, corpus=corpus, top_k=top_k)
        elif method_name == "semantic":
            if cache is None:
                raise ValueError("Semantic evaluation requires an embedding cache.")
            ranked_ids = rank_semantic(
                query_text=query_text,
                corpus=corpus,
                cache=cache,
                top_k=top_k,
            )
        elif method_name == "hybrid":
            if cache is None:
                raise ValueError("Hybrid evaluation requires an embedding cache.")
            ranked_ids = rank_hybrid(
                query_text=query_text,
                corpus=corpus,
                cache=cache,
                top_k=top_k,
            )
        else:
            raise ValueError(f"Unknown method: {method_name}")

        metrics = {
            "precision_at_k": precision_at_k(ranked_ids, relevance, top_k),
            "recall_at_k": recall_at_k(ranked_ids, relevance, top_k),
            "mrr": reciprocal_rank(ranked_ids, relevance),
            "ndcg_at_k": ndcg_at_k(ranked_ids, relevance, top_k),
        }
        rows.append(metrics)
        rankings[str(query["id"])] = ranked_ids

        if show_per_query:
            print(f"\n[{method_name}] {query['id']}")
            print(f"  top_{top_k}: {ranked_ids}")
            print(
                "  metrics: "
                f"P@{top_k}={metrics['precision_at_k']:.3f}, "
                f"R@{top_k}={metrics['recall_at_k']:.3f}, "
                f"MRR={metrics['mrr']:.3f}, "
                f"nDCG@{top_k}={metrics['ndcg_at_k']:.3f}"
            )

    return {
        "summary": {
            "precision_at_k": average_metric(rows, "precision_at_k"),
            "recall_at_k": average_metric(rows, "recall_at_k"),
            "mrr": average_metric(rows, "mrr"),
            "ndcg_at_k": average_metric(rows, "ndcg_at_k"),
        },
        "rankings": rankings,
    }


def print_summary(method_name: str, summary: dict[str, float], top_k: int) -> None:
    print(
        f"{method_name:>10}  "
        f"P@{top_k}={summary['precision_at_k']:.3f}  "
        f"R@{top_k}={summary['recall_at_k']:.3f}  "
        f"MRR={summary['mrr']:.3f}  "
        f"nDCG@{top_k}={summary['ndcg_at_k']:.3f}"
    )


def print_head_to_head(
    *,
    baseline_name: str,
    baseline_results: dict[str, Any],
    challenger_name: str,
    challenger_results: dict[str, Any],
    queries: list[dict[str, Any]],
) -> None:
    wins = {challenger_name: 0, baseline_name: 0, "tie": 0}

    for query in queries:
        query_id = str(query["id"])
        relevance = normalize_relevance(query)
        baseline_rank = baseline_results["rankings"][query_id]
        challenger_rank = challenger_results["rankings"][query_id]

        baseline_score = reciprocal_rank(baseline_rank, relevance)
        challenger_score = reciprocal_rank(challenger_rank, relevance)

        if challenger_score > baseline_score:
            wins[challenger_name] += 1
        elif baseline_score > challenger_score:
            wins[baseline_name] += 1
        else:
            wins["tie"] += 1

    print(
        "\nHead-to-head by first relevant hit: "
        f"{challenger_name}={wins[challenger_name]}, "
        f"{baseline_name}={wins[baseline_name]}, ties={wins['tie']}"
    )


def main() -> None:
    args = parse_args()
    payload = load_eval_file(args.eval_file)

    corpus = payload["corpus"]
    queries = payload["queries"]

    print(
        f"Loaded {len(corpus)} corpus chunks and {len(queries)} labeled queries "
        f"from {args.eval_file}"
    )

    keyword_results = evaluate_method(
        method_name="keyword",
        corpus=corpus,
        queries=queries,
        top_k=args.top_k,
        show_per_query=args.show_per_query,
    )

    print("\nAggregate Metrics")
    print_summary("keyword", keyword_results["summary"], args.top_k)

    if args.skip_semantic:
        return

    cache = load_cache(args.cache_file)
    semantic_results = evaluate_method(
        method_name="semantic",
        corpus=corpus,
        queries=queries,
        top_k=args.top_k,
        cache=cache,
        show_per_query=args.show_per_query,
    )
    hybrid_results = evaluate_method(
        method_name="hybrid",
        corpus=corpus,
        queries=queries,
        top_k=args.top_k,
        cache=cache,
        show_per_query=args.show_per_query,
    )
    save_cache(args.cache_file, cache)

    print_summary("semantic", semantic_results["summary"], args.top_k)
    print_summary("hybrid", hybrid_results["summary"], args.top_k)
    print_head_to_head(
        baseline_name="keyword",
        baseline_results=keyword_results,
        challenger_name="semantic",
        challenger_results=semantic_results,
        queries=queries,
    )
    print_head_to_head(
        baseline_name="semantic",
        baseline_results=semantic_results,
        challenger_name="hybrid",
        challenger_results=hybrid_results,
        queries=queries,
    )


if __name__ == "__main__":
    main()
