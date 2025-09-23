"""
Document Parser Dashboard Launcher

A unified launcher that provides access to both W-2 and Paystub parsing dashboards
with a clean tabbed interface for easy navigation between different document types.
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Page configuration
st.set_page_config(
    page_title="Document Parser Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .dashboard-card {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 0.5rem;
        border: 2px solid #dee2e6;
        margin: 1rem 0;
        text-align: center;
        transition: all 0.3s ease;
    }
    .dashboard-card:hover {
        border-color: #1f77b4;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .feature-list {
        text-align: left;
        margin: 1rem 0;
    }
    .feature-list li {
        margin: 0.5rem 0;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-ready {
        background-color: #28a745;
    }
    .status-warning {
        background-color: #ffc107;
    }
    .status-error {
        background-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

def check_dependencies():
    """Check if required dependencies are available"""
    issues = []
    
    # Check OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        issues.append("OpenAI API key not found")
    
    # Check if dashboard files exist
    w2_dashboard_path = os.path.join(current_dir, "w2", "w2_interactive_dashboard.py")
    paystub_dashboard_path = os.path.join(current_dir, "paystub", "paystub_interactive_dashboard.py")
    
    if not os.path.exists(w2_dashboard_path):
        issues.append("W-2 dashboard not found")
    
    if not os.path.exists(paystub_dashboard_path):
        issues.append("Paystub dashboard not found")
    
    return issues

def get_dashboard_status():
    """Get status of each dashboard"""
    issues = check_dependencies()
    
    status = {
        "w2": "ready" if not any("W-2" in issue for issue in issues) else "error",
        "paystub": "ready" if not any("Paystub" in issue for issue in issues) else "error",
        "api": "ready" if not any("API" in issue for issue in issues) else "error"
    }
    
    return status, issues

def display_welcome():
    """Display welcome section"""
    st.markdown('<h1 class="main-header">Document Parser Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload and parse W-2 and Paystub documents with AI-powered analysis</p>', unsafe_allow_html=True)
    
    # Check system status
    status, issues = get_dashboard_status()
    
    if issues:
        st.error("⚠️ **System Issues Detected:**")
        for issue in issues:
            st.write(f"• {issue}")
        st.markdown("---")
    else:
        st.success("✅ **System Ready** - All components are available")
        st.markdown("---")

def display_dashboard_cards():
    """Display dashboard selection cards"""
    status, issues = get_dashboard_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 📊 W-2 Parser Dashboard")
        
        # Status indicator
        if status["w2"] == "ready":
            st.markdown('<span class="status-indicator status-ready"></span> **Ready**', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-error"></span> **Error**', unsafe_allow_html=True)
        
        st.markdown("""
        **Features:**
        <ul class="feature-list">
            <li>Parse W-2 PDF documents</li>
            <li>Extract employee and employer information</li>
            <li>Calculate annual and monthly income</li>
            <li>Income classification and verification</li>
            <li>Multiple file batch processing</li>
            <li>Export to JSON and CSV formats</li>
        </ul>
        """, unsafe_allow_html=True)
        
        if status["w2"] == "ready":
            if st.button("🚀 Launch W-2 Dashboard", type="primary", use_container_width=True):
                st.session_state.launch_dashboard = "w2"
                st.rerun()
        else:
            st.button("❌ W-2 Dashboard Unavailable", disabled=True, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 💰 Paystub Parser Dashboard")
        
        # Status indicator
        if status["paystub"] == "ready":
            st.markdown('<span class="status-indicator status-ready"></span> **Ready**', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-error"></span> **Error**', unsafe_allow_html=True)
        
        st.markdown("""
        **Features:**
        <ul class="feature-list">
            <li>Parse Paystub PDF documents</li>
            <li>Extract payroll and earnings data</li>
            <li>Calculate monthly qualifying income</li>
            <li>Income classification and YTD verification</li>
            <li>Multiple file batch processing</li>
            <li>Export to JSON and CSV formats</li>
        </ul>
        """, unsafe_allow_html=True)
        
        if status["paystub"] == "ready":
            if st.button("🚀 Launch Paystub Dashboard", type="primary", use_container_width=True):
                st.session_state.launch_dashboard = "paystub"
                st.rerun()
        else:
            st.button("❌ Paystub Dashboard Unavailable", disabled=True, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def launch_dashboard(dashboard_type):
    """Launch the selected dashboard"""
    if dashboard_type == "w2":
        # Import and run W-2 dashboard
        sys.path.insert(0, os.path.join(current_dir, "w2"))
        import w2_interactive_dashboard
        w2_interactive_dashboard.main()
    elif dashboard_type == "paystub":
        # Import and run Paystub dashboard
        sys.path.insert(0, os.path.join(current_dir, "paystub"))
        import paystub_interactive_dashboard
        paystub_interactive_dashboard.main()

def display_instructions():
    """Display usage instructions"""
    st.markdown("---")
    st.markdown("### 📋 How to Use")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **W-2 Parser:**
        1. Click "Launch W-2 Dashboard"
        2. Upload W-2 PDF files
        3. Review parsed results
        4. Export data as needed
        
        **Best for:** Annual income verification, tax document analysis
        """)
    
    with col2:
        st.markdown("""
        **Paystub Parser:**
        1. Click "Launch Paystub Dashboard"
        2. Upload Paystub PDF files
        3. Review parsed results
        4. Export data as needed
        
        **Best for:** Current income verification, payroll analysis
        """)
    
    st.markdown("---")
    st.markdown("### 🔧 System Requirements")
    st.markdown("""
    - **OpenAI API Key**: Required for GPT-4 Vision analysis
    - **Python Dependencies**: All required packages installed
    - **File Formats**: PDF documents only
    - **Processing Time**: 15-45 seconds per document
    """)

def main():
    """Main launcher application"""
    
    # Initialize session state
    if 'launch_dashboard' not in st.session_state:
        st.session_state.launch_dashboard = None
    
    # Check if a dashboard should be launched
    if st.session_state.launch_dashboard:
        # Add back button with home icon and green styling
        if st.button("🏠 Back to Launcher", type="primary"):
            st.session_state.launch_dashboard = None
            st.rerun()
        
        # Launch the selected dashboard
        launch_dashboard(st.session_state.launch_dashboard)
    else:
        # Display launcher interface
        display_welcome()
        display_dashboard_cards()
        display_instructions()
        
        # Footer
        st.markdown("---")
        st.markdown(
            "**Document Parser Dashboard Launcher** | "
            "Unified interface for W-2 and Paystub document analysis"
        )

if __name__ == "__main__":
    main()
