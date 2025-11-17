"""Supervisor Agent - Orchestrates the workflow."""
from typing import Any, Dict, List


class SupervisorAgent:
    """Master coordinator for financial analysis."""

    def __init__(self, llm):
        self.llm = llm

    def plan_workflow(self, query: str) -> Dict[str, Any]:
        """Create execution plan for query."""
        # Simplified planning
        plan = {
            "query": query,
            "needs_retrieval": True,
            "needs_calculation": "calculate" in query.lower()
            or "growth" in query.lower(),
            "needs_temporal": any(
                q in query.lower() for q in ["Q1", "Q2", "Q3", "Q4", "quarter", "year"]
            ),
        }
        return plan

    def synthesize_answer(self, state: Dict[str, Any]) -> str:
        """Combine results into final answer."""
        retrieved_data = state.get("retrieved_data", [])
        calculations = state.get("calculations", {})

        # Simple synthesis
        answer_parts = []

        if retrieved_data:
            answer_parts.append("Based on the financial statements:")
            for data in retrieved_data[:3]:
                answer_parts.append(f"- {data}")

        if calculations:
            answer_parts.append("\nCalculations:")
            for calc_name, result in calculations.items():
                answer_parts.append(f"- {calc_name}: {result}")

        return "\n".join(answer_parts)
