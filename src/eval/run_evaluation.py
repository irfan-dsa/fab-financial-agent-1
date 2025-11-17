# src/eval/run_evaluation.py
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys
sys.path.insert(0, "src")

# Import your agents (adjust imports based on your structure)
from agents.orchestrator import FABOrchestrator  # Your main agent
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


class EvaluationMetrics:
    """Calculate all required evaluation metrics"""
    
    def __init__(self):
        self.results = {
            "accuracy": [],
            "retrieval_quality": [],
            "citation_quality": [],
            "response_times": [],
            "costs": []
        }
    
    def calculate_accuracy(self, predicted_value: float, ground_truth_value: float, tolerance: float = 0.01) -> Dict:
        """
        Calculate accuracy for financial figures
        Args:
            tolerance: Acceptable relative error (default 1%)
        """
        if ground_truth_value == 0:
            is_exact_match = predicted_value == 0
            relative_error = abs(predicted_value)
        else:
            is_exact_match = abs(predicted_value - ground_truth_value) < 1e-6
            relative_error = abs((predicted_value - ground_truth_value) / ground_truth_value)
        
        is_within_tolerance = relative_error <= tolerance
        
        return {
            "exact_match": is_exact_match,
            "within_tolerance": is_within_tolerance,
            "relative_error": relative_error,
            "absolute_error": abs(predicted_value - ground_truth_value)
        }
    
    def evaluate_retrieval(self, retrieved_docs: List[Dict], relevant_periods: List[str]) -> Dict:
        """
        Calculate retrieval precision and recall
        """
        retrieved_periods = set([doc.get("quarter_year") for doc in retrieved_docs if doc.get("quarter_year")])
        relevant_periods_set = set(relevant_periods)
        
        true_positives = len(retrieved_periods & relevant_periods_set)
        false_positives = len(retrieved_periods - relevant_periods_set)
        false_negatives = len(relevant_periods_set - retrieved_periods)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "retrieved_count": len(retrieved_docs),
            "relevant_count": len(relevant_periods)
        }
    
    def evaluate_citations(self, response: str, metadata: Dict) -> Dict:
        """
        Evaluate citation quality
        Returns % of answers with proper sources, page numbers, etc.
        """
        has_source = "source" in metadata or "file" in metadata
        has_page = "page" in metadata
        has_period = "period" in metadata or "quarter" in metadata
        
        # Check if response mentions source explicitly
        mentions_source = any(keyword in response.lower() for keyword in 
                             ["source:", "from", "according to", "page", "quarter", "q1", "q2", "q3", "q4"])
        
        citation_score = sum([has_source, has_page, has_period, mentions_source]) / 4.0
        
        return {
            "has_source": has_source,
            "has_page": has_page,
            "has_period": has_period,
            "mentions_source": mentions_source,
            "citation_score": citation_score
        }
    
    def calculate_cost(self, tokens_used: Dict, model: str = "gpt-4o-mini") -> float:
        """
        Estimate API cost based on token usage
        Pricing as of 2024 (update as needed)
        """
        pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},  # per 1K tokens
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        }
        
        if model not in pricing:
            return 0.0
        
        input_cost = (tokens_used.get("input", 0) / 1000) * pricing[model]["input"]
        output_cost = (tokens_used.get("output", 0) / 1000) * pricing[model]["output"]
        
        return input_cost + output_cost


class EvaluationRunner:
    """Run comprehensive evaluation on test queries"""
    
    def __init__(self, orchestrator, test_queries_path: str):
        self.orchestrator = orchestrator
        self.metrics = EvaluationMetrics()
        
        # Load test queries
        with open(test_queries_path, 'r') as f:
            data = json.load(f)
            self.queries = data["queries"]
            self.metadata = data["metadata"]
        
        self.results = []
    
    def run_single_query(self, query_data: Dict) -> Dict:
        """Execute a single test query and collect metrics"""
        print(f"\n{'='*70}")
        print(f"Query {query_data['id']}: {query_data['category']}")
        print(f"Q: {query_data['query']}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # Run the query through your orchestrator
            response = self.orchestrator.run(query_data['query'])
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Extract response components
            answer = response.get("answer", "")
            metadata = response.get("metadata", {})
            retrieved_docs = response.get("retrieved_docs", [])
            tokens_used = response.get("tokens", {"input": 0, "output": 0})
            
            # Calculate metrics based on category
            result = {
                "query_id": query_data["id"],
                "category": query_data["category"],
                "query": query_data["query"],
                "answer": answer,
                "response_time": response_time,
                "success": True,
                "error": None
            }
            
            # Category-specific evaluation
            if query_data["category"] == "simple_factual":
                result.update(self._evaluate_factual(query_data, answer, metadata))
            
            elif query_data["category"] == "calculation":
                result.update(self._evaluate_calculation(query_data, answer, metadata))
            
            elif query_data["category"] == "multi_hop":
                result.update(self._evaluate_multihop(query_data, answer, retrieved_docs))
            
            elif query_data["category"] == "temporal":
                result.update(self._evaluate_temporal(query_data, answer, metadata))
            
            elif query_data["category"] == "out_of_scope":
                result.update(self._evaluate_out_of_scope(query_data, answer))
            
            # Universal metrics
            result["citation_metrics"] = self.metrics.evaluate_citations(answer, metadata)
            result["cost"] = self.metrics.calculate_cost(tokens_used)
            
            print(f"✅ Response time: {response_time:.2f}s")
            print(f"💰 Estimated cost: ${result['cost']:.6f}")
            
        except Exception as e:
            result = {
                "query_id": query_data["id"],
                "category": query_data["category"],
                "query": query_data["query"],
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
            print(f"❌ Error: {e}")
        
        self.results.append(result)
        return result
    
    def _evaluate_factual(self, query_data: Dict, answer: str, metadata: Dict) -> Dict:
        """Evaluate simple factual query"""
        gt = query_data["ground_truth"]
        
        # Try to extract numeric value from answer
        import re
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', answer.replace(',', ''))
        
        if numbers and gt.get("expected_value"):
            predicted_value = float(numbers[0])
            accuracy = self.metrics.calculate_accuracy(predicted_value, gt["expected_value"])
            
            return {
                "accuracy": accuracy,
                "predicted_value": predicted_value,
                "ground_truth_value": gt["expected_value"],
                "has_source": gt.get("source_required", False) and "source" in metadata
            }
        
        return {"accuracy": None, "extraction_failed": True}
    
    def _evaluate_calculation(self, query_data: Dict, answer: str, metadata: Dict) -> Dict:
        """Evaluate calculation query"""
        gt = query_data["ground_truth"]
        
        import re
        numbers = re.findall(r'-?\d+(?:\.\d+)?', answer)
        
        if numbers and gt.get("expected_value"):
            predicted_value = float(numbers[0])
            tolerance = gt.get("tolerance", 0.01)
            accuracy = self.metrics.calculate_accuracy(predicted_value, gt["expected_value"], tolerance)
            
            return {
                "accuracy": accuracy,
                "predicted_value": predicted_value,
                "ground_truth_value": gt["expected_value"],
                "calculation_shown": "=" in answer or "calculate" in answer.lower(),
                "tool_used": metadata.get("tool_used") == "calculator"
            }
        
        return {"accuracy": None, "extraction_failed": True}
    
    def _evaluate_multihop(self, query_data: Dict, answer: str, retrieved_docs: List) -> Dict:
        """Evaluate multi-hop reasoning"""
        gt = query_data["ground_truth"]
        
        # Check if multiple periods were retrieved
        periods_retrieved = set([doc.get("quarter_year") for doc in retrieved_docs if doc.get("quarter_year")])
        expected_periods = gt.get("periods", [])
        
        retrieval_metrics = self.metrics.evaluate_retrieval(retrieved_docs, expected_periods)
        
        # Check if all required metrics mentioned
        metrics_needed = gt.get("metrics_needed", [])
        metrics_mentioned = sum(1 for metric in metrics_needed if metric.replace("_", " ") in answer.lower())
        metric_coverage = metrics_mentioned / len(metrics_needed) if metrics_needed else 0
        
        return {
            "retrieval_metrics": retrieval_metrics,
            "metric_coverage": metric_coverage,
            "periods_covered": len(periods_retrieved),
            "expected_periods": len(expected_periods),
            "reasoning_depth": len(answer.split(". "))  # Rough proxy for reasoning depth
        }
    
    def _evaluate_temporal(self, query_data: Dict, answer: str, metadata: Dict) -> Dict:
        """Evaluate temporal comparison"""
        gt = query_data["ground_truth"]
        periods = gt.get("periods", [])
        
        # Check how many periods are mentioned in answer
        periods_mentioned = sum(1 for period in periods if period.replace("_", " ") in answer)
        
        return {
            "periods_mentioned": periods_mentioned,
            "expected_periods": len(periods),
            "coverage_rate": periods_mentioned / len(periods) if periods else 0,
            "trend_identified": any(word in answer.lower() for word in ["increase", "decrease", "trend", "growth", "decline"])
        }
    
    def _evaluate_out_of_scope(self, query_data: Dict, answer: str) -> Dict:
        """Evaluate out-of-scope handling"""
        gt = query_data["ground_truth"]
        expected_behavior = gt["expected_behavior"]
        
        # Check if system properly refused or asked for clarification
        refusal_indicators = ["cannot", "unable", "don't have", "not available", "clarify", "specify"]
        refused = any(indicator in answer.lower() for indicator in refusal_indicators)
        
        return {
            "properly_handled": refused,
            "expected_behavior": expected_behavior,
            "refusal_detected": refused
        }
    
    def run_all_queries(self):
        """Execute all test queries"""
        print(f"\n{'#'*70}")
        print(f"# STARTING COMPREHENSIVE EVALUATION")
        print(f"# Total queries: {len(self.queries)}")
        print(f"# Categories: {list(self.metadata['categories'].keys())}")
        print(f"{'#'*70}\n")
        
        for query_data in self.queries:
            self.run_single_query(query_data)
            time.sleep(0.5)  # Rate limiting
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive evaluation report"""
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(self.results),
                "successful_queries": sum(1 for r in self.results if r.get("success")),
                "failed_queries": sum(1 for r in self.results if not r.get("success"))
            },
            "performance_metrics": self._calculate_aggregate_metrics(),
            "category_breakdown": self._breakdown_by_category(),
            "failure_analysis": self._analyze_failures(),
            "detailed_results": self.results
        }
        
        # Save report
        output_path = Path("src/eval/reports/evaluation_report.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'#'*70}")
        print(f"# EVALUATION COMPLETE")
        print(f"# Report saved to: {output_path}")
        print(f"{'#'*70}\n")
        
        self._print_summary(report)
        
        return report
    
    def _calculate_aggregate_metrics(self) -> Dict:
        """Calculate overall performance metrics"""
        successful_results = [r for r in self.results if r.get("success")]
        
        # Accuracy (for factual and calculation queries)
        accuracy_results = [r for r in successful_results 
                          if r.get("accuracy") and r["accuracy"].get("within_tolerance")]
        accuracy_rate = len(accuracy_results) / len([r for r in successful_results 
                                                      if r.get("category") in ["simple_factual", "calculation"]]) if any(r.get("category") in ["simple_factual", "calculation"] for r in successful_results) else 0
        
        # Citation quality
        citation_scores = [r["citation_metrics"]["citation_score"] 
                          for r in successful_results if r.get("citation_metrics")]
        avg_citation_score = sum(citation_scores) / len(citation_scores) if citation_scores else 0
        
        # Response times
        response_times = [r["response_time"] for r in successful_results]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Costs
        costs = [r.get("cost", 0) for r in successful_results]
        total_cost = sum(costs)
        avg_cost_per_query = total_cost / len(costs) if costs else 0
        
        return {
            "accuracy_rate": accuracy_rate,
            "avg_citation_score": avg_citation_score,
            "avg_response_time": avg_response_time,
            "total_cost": total_cost,
            "avg_cost_per_query": avg_cost_per_query,
            "success_rate": len(successful_results) / len(self.results) if self.results else 0
        }
    
    def _breakdown_by_category(self) -> Dict:
        """Break down performance by query category"""
        breakdown = {}
        
        for category in ["simple_factual", "calculation", "multi_hop", "temporal", "out_of_scope"]:
            category_results = [r for r in self.results if r.get("category") == category]
            
            if category_results:
                successful = [r for r in category_results if r.get("success")]
                
                breakdown[category] = {
                    "total": len(category_results),
                    "successful": len(successful),
                    "success_rate": len(successful) / len(category_results),
                    "avg_response_time": sum(r["response_time"] for r in successful) / len(successful) if successful else 0
                }
        
        return breakdown
    
    def _analyze_failures(self) -> List[Dict]:
        """Analyze failed queries"""
        failures = [r for r in self.results if not r.get("success")]
        
        return [{
            "query_id": f["query_id"],
            "query": f["query"],
            "category": f["category"],
            "error": f.get("error", "Unknown error")
        } for f in failures]
    
    def _print_summary(self, report: Dict):
        """Print human-readable summary"""
        metrics = report["performance_metrics"]
        
        print("\n" + "="*70)
        print("EVALUATION SUMMARY")
        print("="*70)
        print(f"\n📊 Overall Performance:")
        print(f"  Success Rate: {metrics['success_rate']*100:.1f}%")
        print(f"  Accuracy Rate: {metrics['accuracy_rate']*100:.1f}%")
        print(f"  Avg Citation Score: {metrics['avg_citation_score']*100:.1f}%")
        print(f"\n⏱️  Performance:")
        print(f"  Avg Response Time: {metrics['avg_response_time']:.2f}s")
        print(f"\n💰 Cost Analysis:")
        print(f"  Total Cost: ${metrics['total_cost']:.4f}")
        print(f"  Avg Cost/Query: ${metrics['avg_cost_per_query']:.6f}")
        
        print(f"\n📁 Category Breakdown:")
        for cat, data in report["category_breakdown"].items():
            print(f"  {cat}: {data['successful']}/{data['total']} ({data['success_rate']*100:.1f}%)")
        
        if report["failure_analysis"]:
            print(f"\n❌ Failures: {len(report['failure_analysis'])}")
            for failure in report["failure_analysis"][:3]:
                print(f"  - Query {failure['query_id']}: {failure['error'][:50]}...")


# Main execution
if __name__ == "__main__":
    # Initialize your orchestrator
    client = QdrantClient(path="data/vectorstore")
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    orchestrator = FABOrchestrator(client, encoder)  # Your main agent system
    
    # Run evaluation
    runner = EvaluationRunner(
        orchestrator=orchestrator,
        test_queries_path="data/ground_truth/test_queries.json"
    )
    
    report = runner.run_all_queries()