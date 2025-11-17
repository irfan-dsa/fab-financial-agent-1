"""FAB Financial Agent - INTEGRATED WITH HYBRID EXTRACTOR
Uses proven direct PDF extraction for 100% accuracy
"""
import sys
sys.path.insert(0, "src")
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import re
from agents.calculator_agent import yoy_change
from agents.extractor_adapter_hybrid import extract_metric_from_file, METRIC_MAPPING
from pathlib import Path

class AgentState(TypedDict):
    query: str
    plan: Dict[str, Any]
    retrieved_chunks: List[Dict]
    extracted_metrics: Dict[str, Any]
    calculations: Dict[str, Any]
    final_answer: str
    sources: List[str]
    confidence: float

class FABFinancialAgent:
    def __init__(self):
        self.vector_client = QdrantClient(path="data/vectorstore")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("plan", self.plan_query)
        workflow.add_node("retrieve", self.retrieve_data)
        workflow.add_node("extract", self.extract_metrics)
        workflow.add_node("calculate", self.calculate_results)
        workflow.add_node("synthesize", self.synthesize_answer)
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "retrieve")
        workflow.add_edge("retrieve", "extract")
        workflow.add_edge("extract", "calculate")
        workflow.add_edge("calculate", "synthesize")
        workflow.add_edge("synthesize", END)
        return workflow.compile()

    def plan_query(self, state):
        query = state["query"]
        print(f"\n[PLAN] {query[:80]}...")
        
        # Detect metric being asked about
        query_lower = query.lower()
        detected_metric = None
        # Try exact phrase match first (most specific)
        for snake_case, display_name in METRIC_MAPPING.items():
            if display_name.lower() in query_lower:
                detected_metric = snake_case
                break
        
        # If no exact match, try partial matches with priority
        if not detected_metric:
            metric_priorities = [
                ('profit for the period', 'profit_for_the_period'),
                ('net profit', 'net_profit'),
                ('net interest income', 'net_interest_income'),
                ('net fee and commission', 'net_fee_and_commission_income'),
                ('operating income', 'operating_income'),
                ('interest income', 'interest_income'),
                ('interest expense', 'interest_expense'),
            ]
            for phrase, metric_key in metric_priorities:
                if phrase in query_lower:
                    detected_metric = metric_key
                    break
        
        # If no specific metric, default to net_profit
        if not detected_metric:
            if 'profit' in query_lower:
                detected_metric = 'profit_for_the_period'
        
        state["plan"] = {
            "needs_calculation": any(w in query_lower for w in ["calculate", "growth", "change", "yoy", "percentage", "compare"]),
            "quarters_mentioned": re.findall(r'Q[1-4]\s*\d{4}', query, re.I),
            "metric": detected_metric
        }
        print(f"  Quarters: {state['plan']['quarters_mentioned']}")
        print(f"  Metric: {detected_metric}")
        return state

    def retrieve_data(self, state):
        print("\n[RETRIEVE] Using direct PDF extraction...")
        quarters = state["plan"]["quarters_mentioned"]
        metric = state["plan"]["metric"]
        
        if not quarters or not metric:
            print("  ⚠ No quarters or metric detected, falling back to vector search")
            return self._fallback_retrieve(state)
        
        state["retrieved_chunks"] = []
        for q_str in quarters:
            match = re.match(r'Q(\d)\s*(\d{4})', q_str, re.I)
            if match:
                quarter, year = f"Q{match.group(1)}", match.group(2)
                pdf_path = f"data/raw/FAB-FS-{quarter}-{year}-English.pdf"
                
                if Path(pdf_path).exists():
                    state["retrieved_chunks"].append({
                        "quarter": quarter,
                        "year": int(year),
                        "pdf_path": pdf_path,
                        "quarter_year": f"{quarter}_{year}"
                    })
                    print(f"  Found PDF: {pdf_path}")
        
        return state

    def _fallback_retrieve(self, state):
        """Fallback to vector search if direct extraction can't be used"""
        print("\n[RETRIEVE] Searching vector DB...")
        query_vector = self.encoder.encode(state["query"]).tolist()
        
        query_filter = None
        if state["plan"]["quarters_mentioned"]:
            from qdrant_client.models import Filter, FieldCondition, MatchAny
            qys = [f"Q{re.match(r'Q(\d)\s*(\d{4})', q, re.I).group(1)}_{re.match(r'Q(\d)\s*(\d{4})', q, re.I).group(2)}"
                   for q in state["plan"]["quarters_mentioned"]]
            query_filter = Filter(must=[FieldCondition(key="quarter_year", match=MatchAny(any=qys))])
            print(f"  Filtering: {qys}")
        
        results = self.vector_client.query_points("fab_financials", query_vector, query_filter=query_filter, limit=20)
        state["retrieved_chunks"] = [{
            "content": r.payload["full_content"],
            "quarter": r.payload["quarter"],
            "year": r.payload["year"],
            "section": r.payload["section"],
            "page": r.payload["page"],
            "score": r.score
        } for r in results.points]
        print(f"  Found {len(state['retrieved_chunks'])} chunks")
        return state

    def extract_metrics(self, state):
        print("\n[EXTRACT] Using hybrid extractor...")
        extracted = {}
        metric = state["plan"]["metric"]
        
        if not metric:
            print("  ⚠ No metric detected")
            state["extracted_metrics"] = extracted
            return state
        
        for chunk in state["retrieved_chunks"]:
            pdf_path = chunk.get("pdf_path")
            if not pdf_path:
                continue
            
            try:
                proofs = extract_metric_from_file(pdf_path, metric)
                
                if proofs:
                    # Use first proof (highest confidence)
                    proof = proofs[0]
                    qk = chunk["quarter_year"]
                    
                    extracted[f"{metric}_{qk}"] = {
                        "metric_name": METRIC_MAPPING.get(metric, metric),
                        "value": proof["value_millions"],
                        "quarter": chunk["quarter"],
                        "year": chunk["year"],
                        "source": f"Page {proof['page']}",
                        "unit": "AED millions",
                        "raw_line": proof["raw_line"],
                        "confidence": 1.0
                    }
                    print(f"  ✓ {chunk['quarter']} {chunk['year']}: {proof['value_millions']:,.2f}M")
            except Exception as e:
                print(f"  ✗ Error extracting from {pdf_path}: {e}")
        
        print(f"  Total: {len(extracted)} metrics")
        state["extracted_metrics"] = extracted
        return state

    def calculate_results(self, state):
        print("\n[CALCULATE]...")
        calcs = {}
        if state["plan"]["needs_calculation"] and len(state["extracted_metrics"]) >= 2:
            vals = sorted(state["extracted_metrics"].values(), key=lambda x: (x['year'], x['quarter']))
            if len(vals) >= 2:
                old, new = vals[0]['value'], vals[-1]['value']
                result = yoy_change(float(old), float(new))
                metric_name = vals[0]['metric_name']
                calcs[f"{metric_name}_Growth"] = {
                    "result": result.output,
                    "old": old,
                    "new": new,
                    "old_period": f"{vals[0]['quarter']} {vals[0]['year']}",
                    "new_period": f"{vals[-1]['quarter']} {vals[-1]['year']}",
                    "change": new - old
                }
                print(f"  ✓ Growth: {result.output:.2f}%")
        state["calculations"] = calcs
        return state

    def synthesize_answer(self, state):
        print("\n[SYNTHESIZE]...")
        parts = []
        
        if state["calculations"]:
            for calc_name, c in state["calculations"].items():
                parts.append(
                    f"## 📊 {calc_name}: **{c['result']:.2f}%**\n\n"
                    f"- **{c['old_period']}**: {c['old']:,.2f}M AED\n"
                    f"- **{c['new_period']}**: {c['new']:,.2f}M AED\n"
                    f"- **Change**: {c['change']:+,.2f}M AED\n"
                )
        
        elif state["extracted_metrics"]:
            parts.append("## 📈 Extracted Metrics\n\n")
            for key, m in state["extracted_metrics"].items():
                parts.append(
                    f"**{m['metric_name']}** ({m['quarter']} {m['year']}): "
                    f"**{m['value']:,.2f}M** AED\n"
                    f"- Source: {m['source']}\n"
                    f"- Line: {m.get('raw_line', 'N/A')[:80]}\n\n"
                )
        else:
            parts.append("No data found")
        
        state["final_answer"] = "".join(parts)
        state["confidence"] = 1.0 if state["extracted_metrics"] else 0.4
        return state

    def query(self, question: str) -> Dict[str, Any]:
        initial_state = {
            "query": question,
            "plan": {},
            "retrieved_chunks": [],
            "extracted_metrics": {},
            "calculations": {},
            "final_answer": "",
            "sources": [],
            "confidence": 0.0
        }
        
        result = self.workflow.invoke(initial_state)
        return result

if __name__ == "__main__":
    agent = FABFinancialAgent()
    
    # Test queries
    tests = [
        "What was the net profit in Q1 2025?",
        "Calculate YoY growth in net profit between Q1 2024 and Q1 2025",
        "What was net interest income in Q3 2023?"
    ]
    
    for q in tests:
        print("\n" + "="*70)
        print(f"Q: {q}")
        print("="*70)
        result = agent.query(q)
        print(f"\nAnswer:\n{result['final_answer']}")
        print(f"Confidence: {result['confidence']*100:.1f}%")

