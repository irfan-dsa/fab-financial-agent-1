"""
Streamlit UI for FAB Financial Agent
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, "src")

from run_agent import FABFinancialAgent
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="FAB Financial Analyst AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "agent" not in st.session_state:
    with st.spinner("Initializing FAB Financial Agent..."):
        st.session_state.agent = FABFinancialAgent()
        st.session_state.history = []

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

# Header
st.markdown('<div class="main-header">🏦 FAB Financial Analyst AI</div>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 About")
    st.info("""
    **FAB Financial Agent** is a multi-agent AI system that analyzes 
    First Abu Dhabi Bank's quarterly financial statements.
    
    **Coverage:**
    - Q2 2023 → Q1 2025
    - 645 document chunks
    - All major financial statements
    """)
    
    st.header("💡 Example Queries")
    example_queries = [
        "What was the net profit in Q1 2025?",
        "Calculate YoY growth in net profit between Q1 2024 and Q1 2025",
        "What are the total assets in Q4 2024?",
        "Compare net profit between Q3 2023 and Q3 2024",
        "What was the Return on Equity trend?",
    ]
    
    for example in example_queries:
        if st.button(example, key=f"example_{example[:20]}"):
            st.session_state.current_query = example
    
    st.header("📈 Statistics")
    st.metric("Total Queries", st.session_state.query_count)
    st.metric("Documents Indexed", "8 quarters")
    st.metric("Total Chunks", "645")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🔍 Ask a Question")
    
    # Query input
    query = st.text_area(
        "Enter your financial analysis query:",
        value=st.session_state.get("current_query", ""),
        height=100,
        placeholder="Example: What was the net profit in Q1 2025?"
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
    
    with col_btn1:
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
    
    with col_btn2:
        clear_btn = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_btn:
        st.session_state.current_query = ""
        st.rerun()

with col2:
    st.header("ℹ️ Query Info")
    if query:
        st.info(f"""
        **Query Length:** {len(query)} characters
        
        **Detected Keywords:**
        {', '.join([w for w in ['profit', 'assets', 'equity', 'growth', 'ratio'] if w in query.lower()]) or 'None'}
        """)

# Process query
if analyze_btn and query:
    st.session_state.query_count += 1
    
    with st.spinner("🤖 Agent is working..."):
        try:
            # Run agent
            result = st.session_state.agent.run(query)
            
            # Add to history
            st.session_state.history.append({
                "query": query,
                "result": result,
                "timestamp": datetime.now()
            })
            
            # Display results
            st.markdown("---")
            st.header("📋 Analysis Results")
            
            # Confidence badge
            confidence = result["confidence"]
            if confidence > 0.75:
                conf_class = "confidence-high"
                conf_emoji = "✅"
            elif confidence > 0.5:
                conf_class = "confidence-medium"
                conf_emoji = "⚠️"
            else:
                conf_class = "confidence-low"
                conf_emoji = "❌"
            
            col_conf1, col_conf2 = st.columns([3, 1])
            with col_conf2:
                st.markdown(f'<div class="{conf_class}">{conf_emoji} Confidence: {confidence:.1%}</div>', 
                           unsafe_allow_html=True)
            
            # Main answer
            st.markdown("### 🎯 Answer")
            st.markdown(result["final_answer"])
            
            # Expandable sections
            with st.expander("📊 Retrieved Data Details", expanded=False):
                st.write(f"**Chunks Retrieved:** {len(result['retrieved_chunks'])}")
                
                if result['retrieved_chunks']:
                    for i, chunk in enumerate(result['retrieved_chunks'][:5], 1):
                        st.markdown(f"""
                        **Chunk {i}:**
                        - Quarter: {chunk['quarter']} {chunk['year']}
                        - Section: {chunk['section']}
                        - Page: {chunk['page']}
                        - Relevance: {chunk['score']:.2%}
                        """)
            
            with st.expander("🔢 Extracted Metrics", expanded=False):
                if result['extracted_metrics']:
                    for metric, data in result['extracted_metrics'].items():
                        st.markdown(f"**{metric}:** {data}")
                else:
                    st.info("No metrics extracted")
            
            with st.expander("🧮 Calculations", expanded=False):
                if result['calculations']:
                    for calc_name, calc_data in result['calculations'].items():
                        st.markdown(f"""
                        **{calc_name}:**
                        - Result: {calc_data['result']:.2f}%
                        - Formula: `{calc_data['formula']}`
                        - Inputs: {calc_data['inputs']}
                        """)
                else:
                    st.info("No calculations performed")
            
            with st.expander("📚 Sources", expanded=False):
                if result['sources']:
                    for source in result['sources']:
                        st.markdown(f"- {source}")
                else:
                    st.info("No sources available")
            
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())

# Query History
if st.session_state.history:
    st.markdown("---")
    st.header("📜 Query History")
    
    for i, item in enumerate(reversed(st.session_state.history[-5:]), 1):
        with st.expander(f"{i}. {item['query'][:60]}... ({item['timestamp'].strftime('%H:%M:%S')})"):
            st.markdown(f"**Query:** {item['query']}")
            st.markdown(f"**Confidence:** {item['result']['confidence']:.1%}")
            st.markdown("**Answer:**")
            st.markdown(item['result']['final_answer'])

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 2rem 0;'>
    <p>FAB Financial Analyst AI | Built with LangGraph, Qdrant, and Streamlit</p>
    <p>Data Coverage: Q2 2023 - Q1 2025</p>
</div>
""", unsafe_allow_html=True)
