# type: ignore
import sys

sys.path.insert(0, "src")
import re

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny
from sentence_transformers import SentenceTransformer


def extract_financial_value(content: str, label: str, column_index: int = 0)  -> str | None:
    """
    Robustly extract a financial value from P&L content.

    Args:
        content: The full text content
        label: The label to search for (e.g., "Profit for the period")
        column_index: Which column to extract (0=first, 1=second, etc.)

    Returns:
        The extracted value as a string, or None if not found
    """
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            # Found the label, now look for the values
            # Skip blank lines and find the first line with numbers
            for j in range(i + 1, min(i + 5, len(lines))):
                potential_value_line = lines[j].strip()

                # Check if this line contains numbers (financial values)
                if re.search(r"\d", potential_value_line):
                    # Split by whitespace and filter out empty strings
                    values = [
                        v.strip() for v in potential_value_line.split() if v.strip()
                    ]

                    # Return the requested column if it exists
                    if column_index < len(values):
                        return values[column_index]

            break

    return None


def query_financial_metric(
    client, encoder, metric_name: str, quarter_year: str, column_index: int = 0
):
    """
    Query for a specific financial metric and extract its value.

    Args:
        client: QdrantClient instance
        encoder: SentenceTransformer instance
        metric_name: Name of the metric (e.g., "Profit for the period")
        quarter_year: Quarter and year (e.g., "Q3_2023")
        column_index: Which column to extract

    Returns:
        Tuple of (value, source_info)
    """
    # Create semantic query
    query_vector = encoder.encode(f"{metric_name} {quarter_year}").tolist()

    # Filter for the specific quarter
    query_filter = Filter(
        must=[
            FieldCondition(key="quarter_year", match=MatchAny(any=[quarter_year])),
            FieldCondition(key="section", match=MatchAny(any=["profit_loss"])),
        ]
    )

    # Search
    results = client.query_points(
        collection_name="fab_financials",
        query=query_vector,
        query_filter=query_filter,
        limit=5,
    )

    # Try to extract from each result
    for result in results.points:
        content = result.payload["full_content"]
        value = extract_financial_value(content, metric_name, column_index)

        if value:
            source_info = {
                "page": result.payload.get("page", "unknown"),
                "score": result.score,
                "chunk_preview": content[:200] + "...",
            }
            return value, source_info

    return None, None


# Example usage
if __name__ == "__main__":
    client = QdrantClient(path="data/vectorstore")
    encoder = SentenceTransformer("all-MiniLM-L6-v2")

    print("ROBUST FINANCIAL METRIC EXTRACTION")
    print("=" * 70)

    # Test different metrics and columns
    test_cases = [
        ("Profit for the period", "Q3_2023", 0, "Current period (9 months)"),
        ("Profit for the period", "Q3_2023", 1, "Prior period (9 months)"),
        ("Profit for the period", "Q3_2023", 2, "Current quarter (3 months)"),
        ("Profit for the period", "Q3_2023", 3, "Prior quarter (3 months)"),
        ("Operating profit", "Q3_2023", 0, "Operating profit - Current period"),
        ("Revenue", "Q3_2023", 0, "Revenue - Current period"),
    ]

    for metric, quarter, col_idx, description in test_cases:
        value, source = query_financial_metric(
            client, encoder, metric, quarter, col_idx
        )

        if value:
            print(f"\n✓ {description}")
            print(f"  Value: {value}")
            print(f"  Source: Page {source['page']}, Score: {source['score']:.4f}")
        else:
            print(f"\n✗ {description}")
            print(f"  Value: NOT FOUND")

    print("\n" + "=" * 70)
    client.close()
