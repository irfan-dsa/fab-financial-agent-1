# src/eval/create_test_queries.py
import json
from pathlib import Path

def create_test_queries():
    """
    Generate 25 test queries covering all required categories:
    - Simple factual (5 queries)
    - Multi-hop reasoning (5 queries)
    - Calculation-heavy (5 queries)
    - Temporal comparison (5 queries)
    - Out-of-scope (5 queries)
    """
    
    queries = [
        # SIMPLE FACTUAL QUERIES (Single document)
        {
            "id": 1,
            "category": "simple_factual",
            "query": "What was FAB's net profit for Q3 2023?",
            "ground_truth": {
                "metric": "net_profit",
                "period": "Q3_2023",
                "expected_value": 3456000000,
                "expected_unit": "AED",
                "source_required": True,
                "page_reference": True
            },
            "difficulty": "easy",
            "expected_steps": 1
        },
        {
            "id": 2,
            "category": "simple_factual",
            "query": "What is the total shareholders' equity in Q1 2024?",
            "ground_truth": {
                "metric": "shareholders_equity",
                "period": "Q1_2024",
                "expected_value": 89000000000,
                "expected_unit": "AED",
                "source_required": True
            },
            "difficulty": "easy",
            "expected_steps": 1
        },
        {
            "id": 3,
            "category": "simple_factual",
            "query": "What was FAB's total revenue in Q2 2024?",
            "ground_truth": {
                "metric": "revenue",
                "period": "Q2_2024",
                "expected_value": 8900000000,
                "expected_unit": "AED",
                "source_required": True
            },
            "difficulty": "easy",
            "expected_steps": 1
        },
        {
            "id": 4,
            "category": "simple_factual",
            "query": "What are the total customer deposits for Q1 2025?",
            "ground_truth": {
                "metric": "customer_deposits",
                "period": "Q1_2025",
                "expected_value": 456000000000,
                "expected_unit": "AED",
                "source_required": True
            },
            "difficulty": "easy",
            "expected_steps": 1
        },
        {
            "id": 5,
            "category": "simple_factual",
            "query": "What was the operating profit in Q2 2023?",
            "ground_truth": {
                "metric": "operating_profit",
                "period": "Q2_2023",
                "expected_value": 7800000000,
                "expected_unit": "AED",
                "source_required": True
            },
            "difficulty": "easy",
            "expected_steps": 1
        },
        
        # CALCULATION-HEAVY QUERIES
        {
            "id": 6,
            "category": "calculation",
            "query": "Calculate FAB's Return on Equity (ROE) for Q3 2023",
            "ground_truth": {
                "calculation": "ROE = (Net Profit / Shareholders Equity) * 100",
                "inputs": {
                    "net_profit": 3456000000,
                    "shareholders_equity": 87000000000
                },
                "expected_value": 3.97,
                "expected_unit": "%",
                "tolerance": 0.1,
                "tool_required": "calculator"
            },
            "difficulty": "medium",
            "expected_steps": 3
        },
        {
            "id": 7,
            "category": "calculation",
            "query": "What is the loan-to-deposit ratio for Q1 2024?",
            "ground_truth": {
                "calculation": "LDR = Total Loans / Customer Deposits",
                "inputs": {
                    "total_loans": 389000000000,
                    "customer_deposits": 445000000000
                },
                "expected_value": 0.874,
                "expected_unit": "ratio",
                "tolerance": 0.01,
                "tool_required": "calculator"
            },
            "difficulty": "medium",
            "expected_steps": 3
        },
        {
            "id": 8,
            "category": "calculation",
            "query": "Calculate the year-over-year percentage change in net profit between Q2 2023 and Q2 2024",
            "ground_truth": {
                "calculation": "YoY = ((Q2_2024 - Q2_2023) / Q2_2023) * 100",
                "inputs": {
                    "q2_2023_net_profit": 3200000000,
                    "q2_2024_net_profit": 3700000000
                },
                "expected_value": 15.625,
                "expected_unit": "%",
                "tolerance": 0.5,
                "tool_required": "calculator"
            },
            "difficulty": "medium",
            "expected_steps": 4
        },
        {
            "id": 9,
            "category": "calculation",
            "query": "What is FAB's Return on Assets (ROA) for Q1 2025?",
            "ground_truth": {
                "calculation": "ROA = (Net Profit / Total Assets) * 100",
                "inputs": {
                    "net_profit": 4100000000,
                    "total_assets": 1123000000000
                },
                "expected_value": 0.365,
                "expected_unit": "%",
                "tolerance": 0.05,
                "tool_required": "calculator"
            },
            "difficulty": "medium",
            "expected_steps": 3
        },
        {
            "id": 10,
            "category": "calculation",
            "query": "Calculate the cost-to-income ratio for Q3 2023",
            "ground_truth": {
                "calculation": "C/I = (Operating Expenses / Revenue) * 100",
                "inputs": {
                    "operating_expenses": 2500000000,
                    "revenue": 8500000000
                },
                "expected_value": 29.41,
                "expected_unit": "%",
                "tolerance": 0.5,
                "tool_required": "calculator"
            },
            "difficulty": "medium",
            "expected_steps": 3
        },
        
        # MULTI-HOP REASONING QUERIES
        {
            "id": 11,
            "category": "multi_hop",
            "query": "Compare FAB's profitability between Q3 2023 and Q1 2024 by analyzing both net profit and ROE. Which quarter performed better?",
            "ground_truth": {
                "requires_multiple_documents": True,
                "metrics_needed": ["net_profit", "roe", "shareholders_equity"],
                "periods": ["Q3_2023", "Q1_2024"],
                "expected_analysis": "comparison with justification",
                "reasoning_steps": [
                    "Extract net profit Q3 2023",
                    "Extract net profit Q1 2024",
                    "Calculate or extract ROE for both",
                    "Compare metrics",
                    "Provide conclusion"
                ]
            },
            "difficulty": "hard",
            "expected_steps": 5
        },
        {
            "id": 12,
            "category": "multi_hop",
            "query": "How has FAB's lending capacity evolved from Q2 2023 to Q1 2025? Consider both total loans and loan-to-deposit ratio.",
            "ground_truth": {
                "requires_multiple_documents": True,
                "metrics_needed": ["total_loans", "customer_deposits", "loan_to_deposit_ratio"],
                "periods": ["Q2_2023", "Q1_2025"],
                "expected_analysis": "trend analysis with numerical support",
                "reasoning_steps": [
                    "Extract loans Q2 2023",
                    "Extract deposits Q2 2023",
                    "Extract loans Q1 2025",
                    "Extract deposits Q1 2025",
                    "Calculate LDR for both periods",
                    "Analyze trend"
                ]
            },
            "difficulty": "hard",
            "expected_steps": 6
        },
        {
            "id": 13,
            "category": "multi_hop",
            "query": "What is the relationship between FAB's revenue growth and operating profit margin across Q2 2023, Q2 2024, and Q1 2025?",
            "ground_truth": {
                "requires_multiple_documents": True,
                "metrics_needed": ["revenue", "operating_profit", "operating_expenses"],
                "periods": ["Q2_2023", "Q2_2024", "Q1_2025"],
                "expected_analysis": "correlation analysis",
                "reasoning_steps": [
                    "Extract revenue for all 3 periods",
                    "Extract operating profit for all 3 periods",
                    "Calculate profit margins",
                    "Analyze correlation",
                    "Provide insights"
                ]
            },
            "difficulty": "hard",
            "expected_steps": 7
        },
        {
            "id": 14,
            "category": "multi_hop",
            "query": "Analyze FAB's capital efficiency by comparing ROE and ROA trends from Q3 2023 to Q1 2024",
            "ground_truth": {
                "requires_multiple_documents": True,
                "metrics_needed": ["net_profit", "shareholders_equity", "total_assets"],
                "periods": ["Q3_2023", "Q1_2024"],
                "expected_analysis": "efficiency analysis with ratios",
                "reasoning_steps": [
                    "Calculate ROE Q3 2023",
                    "Calculate ROA Q3 2023",
                    "Calculate ROE Q1 2024",
                    "Calculate ROA Q1 2024",
                    "Compare trends",
                    "Interpret capital efficiency"
                ]
            },
            "difficulty": "hard",
            "expected_steps": 6
        },
        {
            "id": 15,
            "category": "multi_hop",
            "query": "Has FAB's operational efficiency improved between Q2 2023 and Q2 2024? Consider revenue, operating expenses, and profitability.",
            "ground_truth": {
                "requires_multiple_documents": True,
                "metrics_needed": ["revenue", "operating_expenses", "operating_profit", "net_profit"],
                "periods": ["Q2_2023", "Q2_2024"],
                "expected_analysis": "efficiency improvement assessment",
                "reasoning_steps": [
                    "Extract all metrics Q2 2023",
                    "Extract all metrics Q2 2024",
                    "Calculate efficiency ratios",
                    "Compare year-over-year",
                    "Conclude improvement/decline"
                ]
            },
            "difficulty": "hard",
            "expected_steps": 6
        },
        
        # TEMPORAL COMPARISON QUERIES
        {
            "id": 16,
            "category": "temporal",
            "query": "Show the trend in net profit across all available quarters from Q2 2023 to Q1 2025",
            "ground_truth": {
                "periods": ["Q2_2023", "Q3_2023", "Q1_2024", "Q2_2024", "Q1_2025"],
                "metric": "net_profit",
                "expected_output": "chronological trend with values",
                "visualization_recommended": True
            },
            "difficulty": "medium",
            "expected_steps": 5
        },
        {
            "id": 17,
            "category": "temporal",
            "query": "Compare ROE performance across Q3 2023, Q1 2024, and Q1 2025. Which quarter had the best return?",
            "ground_truth": {
                "periods": ["Q3_2023", "Q1_2024", "Q1_2025"],
                "metric": "roe",
                "calculation_required": True,
                "expected_output": "ranking with values"
            },
            "difficulty": "medium",
            "expected_steps": 4
        },
        {
            "id": 18,
            "category": "temporal",
            "query": "How has customer deposit growth changed from Q2 2023 to Q1 2025?",
            "ground_truth": {
                "periods": ["Q2_2023", "Q1_2025"],
                "metric": "customer_deposits",
                "calculation": "absolute and percentage change",
                "expected_output": "growth rate and absolute change"
            },
            "difficulty": "medium",
            "expected_steps": 4
        },
        {
            "id": 19,
            "category": "temporal",
            "query": "Track the quarterly progression of operating profit from Q2 2023 to Q2 2024",
            "ground_truth": {
                "periods": ["Q2_2023", "Q3_2023", "Q1_2024", "Q2_2024"],
                "metric": "operating_profit",
                "expected_output": "quarter-by-quarter comparison"
            },
            "difficulty": "medium",
            "expected_steps": 4
        },
        {
            "id": 20,
            "category": "temporal",
            "query": "What is the average quarterly net profit for 2023 and 2024 separately?",
            "ground_truth": {
                "periods_2023": ["Q2_2023", "Q3_2023"],
                "periods_2024": ["Q1_2024", "Q2_2024"],
                "metric": "net_profit",
                "calculation": "average by year",
                "expected_output": "two averages with comparison"
            },
            "difficulty": "medium",
            "expected_steps": 5
        },
        
        # OUT-OF-SCOPE QUERIES (Should refuse/clarify)
        {
            "id": 21,
            "category": "out_of_scope",
            "query": "What will FAB's net profit be in Q3 2025?",
            "ground_truth": {
                "expected_behavior": "refuse_future_prediction",
                "reason": "Future prediction not possible with historical data",
                "suggested_response": "Cannot predict future quarters. Can analyze historical trends."
            },
            "difficulty": "n/a",
            "expected_steps": 1
        },
        {
            "id": 22,
            "category": "out_of_scope",
            "query": "Compare FAB's performance with Emirates NBD",
            "ground_truth": {
                "expected_behavior": "refuse_external_comparison",
                "reason": "No data available for other banks",
                "suggested_response": "Only FAB data available. Cannot compare with other banks."
            },
            "difficulty": "n/a",
            "expected_steps": 1
        },
        {
            "id": 23,
            "category": "out_of_scope",
            "query": "What is the CEO's opinion on cryptocurrency investments?",
            "ground_truth": {
                "expected_behavior": "refuse_opinion_speculation",
                "reason": "Opinion/subjective content not in financial statements",
                "suggested_response": "Financial statements don't contain CEO opinions on this topic."
            },
            "difficulty": "n/a",
            "expected_steps": 1
        },
        {
            "id": 24,
            "category": "out_of_scope",
            "query": "Should I invest in FAB stock?",
            "ground_truth": {
                "expected_behavior": "refuse_investment_advice",
                "reason": "Cannot provide investment advice",
                "suggested_response": "Cannot provide investment advice. Can only present financial data."
            },
            "difficulty": "n/a",
            "expected_steps": 1
        },
        {
            "id": 25,
            "category": "out_of_scope",
            "query": "What is FAB's net profit?",
            "ground_truth": {
                "expected_behavior": "ask_clarification",
                "reason": "Missing time period specification",
                "suggested_response": "Please specify which quarter/year (e.g., Q3 2023, Q1 2024)"
            },
            "difficulty": "n/a",
            "expected_steps": 1
        }
    ]
    
    # Save to file
    output_path = Path("data/ground_truth/test_queries.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "metadata": {
                "total_queries": len(queries),
                "categories": {
                    "simple_factual": 5,
                    "calculation": 5,
                    "multi_hop": 5,
                    "temporal": 5,
                    "out_of_scope": 5
                },
                "difficulty_distribution": {
                    "easy": 5,
                    "medium": 10,
                    "hard": 5,
                    "n/a": 5
                }
            },
            "queries": queries
        }, f, indent=2)
    
    print(f"✅ Created {len(queries)} test queries")
    print(f"📁 Saved to: {output_path}")
    print(f"\nCategory breakdown:")
    for cat in ["simple_factual", "calculation", "multi_hop", "temporal", "out_of_scope"]:
        count = len([q for q in queries if q["category"] == cat])
        print(f"  - {cat}: {count}")
    
    return queries

if __name__ == "__main__":
    create_test_queries()