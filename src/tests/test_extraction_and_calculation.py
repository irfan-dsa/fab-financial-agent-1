from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedMetric:
    metric: str
    value: float
    source: str
    page: int
    chunk_id: Optional[str] = None


def extract_metrics_from_chunks(chunks: list) -> list:
    """Extract financial metrics from chunk dictionaries."""
    metrics = []

    for chunk in chunks:
        if chunk.get("chunk_type") == "table_row":
            table_row = chunk.get("table_row", [])
            if len(table_row) >= 2:
                # Normalize metric name to snake_case
                metric_name = table_row[0].lower().replace(" ", "_")

                # Parse value (remove commas, convert to float)
                value_str = str(table_row[1]).replace(",", "")
                try:
                    value = float(value_str)
                except ValueError:
                    continue

                metrics.append(
                    ExtractedMetric(
                        metric=metric_name,
                        value=value,
                        source=chunk.get("file"),
                        page=chunk.get("page"),
                        chunk_id=chunk.get("id"),
                    )
                )

    return metrics
