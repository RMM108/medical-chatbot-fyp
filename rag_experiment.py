
#RAG Threshold Ablation Study
#Tests the effect of different similarity thresholds on retrieval quantity and quality.


import requests
import json
import csv
from datetime import datetime

SERVER_URL = "http://localhost:8000"
THRESHOLDS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
LIMIT = 10  # Retrieve top 10, then we filter by threshold

# Test queries covering different clinical interview topics 
# These represent the kinds of questions a medical student would/may ask
TEST_QUERIES = [
    # Mood / core symptoms
    {"query": "How have you been feeling lately?",                      "severity": "Moderate"},
    {"query": "Can you describe your mood over the past two weeks?",    "severity": "Moderate"},
    {"query": "Do you still enjoy things you used to like doing?",      "severity": "Mild"},

    # Sleep
    {"query": "How has your sleep been recently?",                      "severity": "Moderately Severe"},
    {"query": "Are you having trouble falling asleep or staying asleep?","severity": "Severe"},

    # Energy / fatigue
    {"query": "How are your energy levels day to day?",                 "severity": "Mild"},
    {"query": "Do you feel tired even when you haven't done much?",     "severity": "Moderate"},

    # Appetite
    {"query": "Has your appetite changed at recently?",             "severity": "Moderate"},

    # Concentration
    {"query": "Are you finding it hard to concentrate or focus on things?",       "severity": "Moderately Severe"},

    # Guilt / worthlessness
    {"query": "Do you ever feel like you've let people down?",          "severity": "Severe"},
    {"query": "Have you been feeling bad about yourself lately?",       "severity": "Moderate"},

    # Suicidal ideation
    {"query": "Have you had any thoughts of harming yourself?",         "severity": "Severe"},
    {"query": "Have you felt like things would be better if you weren't here?", "severity": "Severe"},

    # Social / functioning
    {"query": "How has your social life been affected?",                "severity": "Mild"},
    {"query": "Are you still able to go to work or for daily activities?","severity": "Moderately Severe"},
]


def query_rag(query: str, severity: str, limit: int = LIMIT):
    """Send a query to the RAG server and return all results with scores."""
    try:
        response = requests.post(
            f"{SERVER_URL}/search",
            json={"query": query, "severity": severity, "limit": limit, "chunk_type": "chunk"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Server error {response.status_code} for query: {query[:40]}")
            return []
    except Exception as e:
        print(f"  ⚠ Request failed: {e}")
        return []


def apply_threshold(results, threshold):
    return [r for r in results if r['score'] >= threshold]


def run_experiment():
    print("=" * 60)
    print("RAG THRESHOLD ABLATION STUDY")
    print(f"Server: {SERVER_URL}")
    print(f"Thresholds: {THRESHOLDS}")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print("=" * 60)

    # Check connection
    try:
        r = requests.get(f"{SERVER_URL}/", timeout=5)
        if r.status_code != 200:
            print("Cannot connect to RAG server. Is your SSH tunnel running?")
            return
        print("✓ Connected to RAG server\n")
    except:
        print("Cannot connect to RAG server. Is your SSH tunnel running?")
        print("   Run: ssh -L 8000:localhost:8000 riya@endurance -N")
        return

    # Collect raw results for all queries 
    print("Fetching results for all queries...")
    all_raw_results = []
    for i, q in enumerate(TEST_QUERIES):
        print(f"  [{i+1}/{len(TEST_QUERIES)}] {q['query'][:50]}...")
        results = query_rag(q['query'], q['severity'])
        all_raw_results.append({
            "query": q['query'],
            "severity": q['severity'],
            "results": results
        })

    print(f"\n✓ Raw results collected\n")

    # Analyse each threshold 
    print("=" * 60)
    print("RESULTS BY THRESHOLD")
    print("=" * 60)

    summary_rows = []

    for threshold in THRESHOLDS:
        retrieved_counts = []
        all_scores = []
        zero_result_queries = []

        for item in all_raw_results:
            filtered = apply_threshold(item['results'], threshold)
            count = len(filtered)
            retrieved_counts.append(count)

            scores = [r['score'] for r in filtered]
            all_scores.extend(scores)

            if count == 0:
                zero_result_queries.append(item['query'])

        total_queries = len(TEST_QUERIES)
        avg_retrieved = sum(retrieved_counts) / total_queries
        coverage = (total_queries - len(zero_result_queries)) / total_queries * 100
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        min_score = min(all_scores) if all_scores else 0
        max_score = max(all_scores) if all_scores else 0
        total_retrieved = sum(retrieved_counts)

        print(f"\nThreshold: {threshold}")
        print(f"  Avg results per query : {avg_retrieved:.2f}")
        print(f"  Total results retrieved: {total_retrieved}")
        print(f"  Query coverage        : {coverage:.1f}% ({total_queries - len(zero_result_queries)}/{total_queries} queries returned results)")
        print(f"  Avg similarity score  : {avg_score:.4f}")
        print(f"  Score range           : {min_score:.4f} – {max_score:.4f}")
        if zero_result_queries:
            print(f"  Queries with 0 results ({len(zero_result_queries)}):")
            for q in zero_result_queries:
                print(f"    - {q[:60]}")

        summary_rows.append({
            "threshold": threshold,
            "avg_retrieved": round(avg_retrieved, 2),
            "total_retrieved": total_retrieved,
            "coverage_pct": round(coverage, 1),
            "avg_score": round(avg_score, 4),
            "min_score": round(min_score, 4),
            "max_score": round(max_score, 4),
            "zero_result_queries": len(zero_result_queries)
        })

    # Save CSV summary 
    csv_filename = f"rag_threshold_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\n\n✓ Summary saved to: {csv_filename}")

    # Save detailed JSON 
    json_filename = f"rag_threshold_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    detailed_output = []
    for threshold in THRESHOLDS:
        threshold_data = {"threshold": threshold, "queries": []}
        for item in all_raw_results:
            filtered = apply_threshold(item['results'], threshold)
            threshold_data["queries"].append({
                "query": item['query'],
                "severity": item['severity'],
                "num_retrieved": len(filtered),
                "scores": [round(r['score'], 4) for r in filtered],
                "avg_score": round(sum(r['score'] for r in filtered) / len(filtered), 4) if filtered else 0
            })
        detailed_output.append(threshold_data)

    with open(json_filename, 'w') as f:
        json.dump(detailed_output, f, indent=2)

    print(f"✓ Detailed results saved to: {json_filename}")

    # Print final summary table 
    print("\n\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(f"{'Threshold':<12} {'Avg Retrieved':<16} {'Coverage %':<13} {'Avg Score':<12} {'0-Result Queries'}")
    print("-" * 60)
    for row in summary_rows:
        print(f"{row['threshold']:<12} {row['avg_retrieved']:<16} {row['coverage_pct']:<13} {row['avg_score']:<12} {row['zero_result_queries']}")

    print("\n✓ Experiment complete!")
    print(f"\nFiles saved:")
    print(f"  {csv_filename}  ← use this for your report tables")
    print(f"  {json_filename} ← detailed per-query breakdown")


if __name__ == "__main__":
    run_experiment()