"""
Interactive W-2 Parser Dashboard

A dynamic Streamlit dashboard that allows users to upload W-2 PDFs,
parse them in real-time, and drill down into the parsed results
with detailed analysis and validation.
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Any, Optional
import datetime
import tempfile
import os

# Import the W2 parser
import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from w2_parser import W2Parser

# Page configuration
st.set_page_config(
    page_title="Interactive W-2 Parser Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 0.5rem;
        border: 2px dashed #dee2e6;
        text-align: center;
        margin: 2rem 0;
    }
    .parsing-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-status {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-status {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .warning-status {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .income-highlight {
        background-color: #e8f5e8;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

def initialize_parser():
    """Initialize the W2 parser"""
    if 'w2_parser' not in st.session_state:
        st.session_state.w2_parser = W2Parser()
    return st.session_state.w2_parser

def parse_uploaded_w2(uploaded_file) -> Dict[str, Any]:
    """
    Parse an uploaded W-2 PDF file
    
    Args:
        uploaded_file: Uploaded file object from Streamlit
        
    Returns:
        Parsed W-2 data as dictionary
    """
    parser = initialize_parser()
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Parse the W-2
        result = parser.parse_pdf(tmp_path)
        return result
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def display_parsing_status(result: Dict[str, Any]):
    """
    Display parsing status and basic information
    
    Args:
        result: Parsed W-2 data
    """
    if result.get('error'):
        st.markdown('<div class="parsing-status error-status">', unsafe_allow_html=True)
        st.error(f"❌ Parsing Failed: {result['error']}")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    confidence = result.get('confidence_score', 0) or 0
    
    if confidence >= 0.95:
        status_class = "success-status"
        status_icon = "✅"
        status_text = "Excellent"
    elif confidence >= 0.90:
        status_class = "success-status"
        status_icon = "✅"
        status_text = "Very Good"
    elif confidence >= 0.85:
        status_class = "warning-status"
        status_icon = "⚠️"
        status_text = "Good"
    else:
        status_class = "warning-status"
        status_icon = "⚠️"
        status_text = "Needs Review"
    
    st.markdown(f'<div class="parsing-status {status_class}">', unsafe_allow_html=True)
    st.success(f"{status_icon} Parsing {status_text} - Confidence: {confidence:.1%}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    return True

def display_basic_info(result: Dict[str, Any]):
    """
    Display basic W-2 information
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("📋 Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👤 Employee Information**")
        employee = result.get('employee', {})
        st.write(f"**Name:** {employee.get('name', 'N/A')}")
        st.write(f"**SSN:** {employee.get('ssn', 'N/A')}")
        
        address = employee.get('address', {})
        if address:
            st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
    
    with col2:
        st.markdown("**🏢 Employer Information**")
        employer = result.get('employer', {})
        st.write(f"**Company:** {employer.get('name', 'N/A')}")
        st.write(f"**EIN:** {employer.get('ein', 'N/A')}")
        st.write(f"**Control Number:** {employer.get('control_number', 'N/A')}")
        
        emp_address = employer.get('address', {})
        if emp_address:
            st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")

def display_financial_summary(result: Dict[str, Any]):
    """
    Display financial summary with key metrics
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("💰 Financial Summary")
    
    income_info = result.get('income_tax_info', {})
    calculated_income = result.get('calculated_income', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        wages = income_info.get('wages_tips_compensation', 0) or 0
        st.metric(
            label="Wages, Tips, Compensation (Box 1)",
            value=f"${wages:,.2f}",
            help="Primary income for mortgage calculation"
        )
    
    with col2:
        federal_tax = income_info.get('federal_income_tax_withheld', 0) or 0
        st.metric(
            label="Federal Tax Withheld (Box 2)",
            value=f"${federal_tax:,.2f}",
            help="Federal income tax withheld"
        )
    
    with col3:
        annual_income = calculated_income.get('annual_income', 0) or 0
        st.metric(
            label="Annual Income (Calculated)",
            value=f"${annual_income:,.2f}",
            help="Annual income for mortgage approval"
        )
    
    with col4:
        monthly_income = calculated_income.get('monthly_income', 0) or 0
        st.metric(
            label="Monthly Income (Calculated)",
            value=f"${monthly_income:,.2f}",
            help="Monthly income for DTI calculation"
        )

def display_detailed_breakdown(result: Dict[str, Any]):
    """
    Display detailed breakdown of W-2 data in the same format as w2_dashboard.py
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("📊 Detailed Document Review")
    
    # Income Information
    st.subheader("💰 Income & Tax Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Primary Income (Box 1-6)**")
        income_info = result.get('income_tax_info', {})
        st.write(f"Wages, Tips: ${income_info.get('wages_tips_compensation', 0) or 0:,.2f}")
        st.write(f"Federal Tax: ${income_info.get('federal_income_tax_withheld', 0) or 0:,.2f}")
        st.write(f"SS Wages: ${income_info.get('social_security_wages', 0) or 0:,.2f}")
        st.write(f"SS Tax: ${income_info.get('social_security_tax_withheld', 0) or 0:,.2f}")
        st.write(f"Medicare Wages: ${income_info.get('medicare_wages_tips', 0) or 0:,.2f}")
        st.write(f"Medicare Tax: ${income_info.get('medicare_tax_withheld', 0) or 0:,.2f}")
    
    with col2:
        st.markdown("**Calculated Income for Mortgage**")
        calculated_income = result.get('calculated_income', {})
        if calculated_income:
            st.markdown('<div class="income-highlight">', unsafe_allow_html=True)
            st.write(f"**Annual Income:** ${calculated_income.get('annual_income', 0) or 0:,.2f}")
            st.write(f"**Monthly Income:** ${calculated_income.get('monthly_income', 0) or 0:,.2f}")
            st.write(f"**Method:** {calculated_income.get('income_verification_method', 'N/A')}")
            if calculated_income.get('additional_benefits'):
                st.write(f"**Additional Benefits:** ${calculated_income.get('additional_benefits', 0) or 0:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("**Box 12 Codes**")
        box_12_codes = income_info.get('box_12_codes', [])
        if box_12_codes:
            for code_info in box_12_codes:
                if isinstance(code_info, dict):
                    st.write(f"Code {code_info.get('code', 'N/A')}: ${code_info.get('amount', 0) or 0:,.2f}")
        else:
            st.write("No Box 12 codes")
        
        st.markdown("**Flags**")
        st.write(f"Retirement Plan: {'✅' if income_info.get('retirement_plan') else '❌'}")
        st.write(f"Statutory Employee: {'✅' if income_info.get('statutory_employee') else '❌'}")
        st.write(f"Third-party Sick Pay: {'✅' if income_info.get('third_party_sick_pay') else '❌'}")
    
    # State/Local Information
    state_local = result.get('state_local_info', [])
    if state_local:
        st.subheader("🏛️ State & Local Tax Information")
        for state_info in state_local:
            st.write(f"**State:** {state_info.get('state', 'N/A')}")
            st.write(f"State Wages: ${state_info.get('state_wages', 0) or 0:,.2f}")
            st.write(f"State Tax: ${state_info.get('state_income_tax', 0) or 0:,.2f}")
            if state_info.get('locality'):
                st.write(f"Locality: {state_info.get('locality')}")
                st.write(f"Local Wages: ${state_info.get('local_wages', 0) or 0:,.2f}")
                st.write(f"Local Tax: ${state_info.get('local_income_tax', 0) or 0:,.2f}")
    
    # Processing Metadata
    metadata = result.get('processing_metadata', {})
    if metadata:
        st.subheader("🔧 Processing Information")
        col1, col2 = st.columns(2)
        with col1:
            confidence = result.get('confidence_score', 0) or 0
            st.write(f"**Confidence Score:** {confidence:.2%}")
            
            # Confidence score interpretation
            if confidence >= 0.95:
                st.success("🟢 Excellent - High reliability")
            elif confidence >= 0.90:
                st.info("🟡 Very Good - Minor review recommended")
            elif confidence >= 0.85:
                st.warning("🟠 Good - Some fields may need verification")
            else:
                st.error("🔴 Poor - Manual review required")
            
            st.write(f"**Tables Found:** {metadata.get('camelot_tables_found', 'N/A')}")
            st.write(f"**Extraction Method:** {metadata.get('extraction_method', 'N/A')}")
        with col2:
            st.write(f"**GPT Vision Used:** {'✅' if metadata.get('gpt_vision_used') else '❌'}")
            st.write(f"**Validation:** {'✅' if metadata.get('validation_passed') else '❌'}")
            st.write(f"**Validation Method:** {metadata.get('validation_method', 'N/A')}")
            
            # Show confidence factors
            if metadata.get('gpt_vision_used'):
                st.write("**Confidence Factors:**")
                st.write("• ✅ Camelot table extraction")
                st.write("• ✅ GPT-4 Vision validation")
                st.write("• ✅ High-quality processing")
            else:
                st.write("**Confidence Factors:**")
                st.write("• ✅ Camelot table extraction")
                st.write("• ❌ GPT-4 Vision validation")
                st.write("• ⚠️ Basic processing only")


def create_income_visualization(result: Dict[str, Any]):
    """
    Create income visualization charts
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("📊 Income Visualization")
    
    income_info = result.get('income_tax_info', {})
    calculated_income = result.get('calculated_income', {})
    
    # Prepare data for visualization
    wages = income_info.get('wages_tips_compensation', 0) or 0
    federal_tax = income_info.get('federal_income_tax_withheld', 0) or 0
    ss_tax = income_info.get('social_security_tax_withheld', 0) or 0
    medicare_tax = income_info.get('medicare_tax_withheld', 0) or 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Tax breakdown pie chart
        tax_data = {
            'Tax Type': ['Federal Tax', 'Social Security Tax', 'Medicare Tax'],
            'Amount': [federal_tax, ss_tax, medicare_tax]
        }
        
        if sum(tax_data['Amount']) > 0:
            fig_pie = px.pie(
                values=tax_data['Amount'],
                names=tax_data['Tax Type'],
                title="Tax Withholding Breakdown",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No tax data available for visualization")
    
    with col2:
        # Income vs Tax bar chart
        income_tax_data = {
            'Category': ['Wages', 'Federal Tax', 'SS Tax', 'Medicare Tax'],
            'Amount': [wages, federal_tax, ss_tax, medicare_tax]
        }
        
        fig_bar = px.bar(
            x=income_tax_data['Category'],
            y=income_tax_data['Amount'],
            title="Income vs Tax Withholdings",
            color=income_tax_data['Amount'],
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

def export_results(result: Dict[str, Any]):
    """
    Provide export options for the parsed results
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("📥 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_data = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="📄 Download as JSON",
            data=json_data,
            file_name=f"w2_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Summary CSV export
        employee = result.get('employee', {})
        employer = result.get('employer', {})
        income_info = result.get('income_tax_info', {})
        calculated_income = result.get('calculated_income', {})
        
        summary_data = {
            'Field': [
                'Employee Name',
                'Employer Name',
                'Tax Year',
                'Wages (Box 1)',
                'Federal Tax (Box 2)',
                'Annual Income',
                'Monthly Income',
                'Confidence Score'
            ],
            'Value': [
                employee.get('name', 'N/A'),
                employer.get('name', 'N/A'),
                result.get('tax_year', 'N/A'),
                f"${income_info.get('wages_tips_compensation', 0) or 0:,.2f}",
                f"${income_info.get('federal_income_tax_withheld', 0) or 0:,.2f}",
                f"${calculated_income.get('annual_income', 0) or 0:,.2f}",
                f"${calculated_income.get('monthly_income', 0) or 0:,.2f}",
                f"{(result.get('confidence_score', 0) or 0):.2%}"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        csv_data = summary_df.to_csv(index=False)
        
        st.download_button(
            label="📊 Download Summary as CSV",
            data=csv_data,
            file_name=f"w2_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Interactive W-2 Parser Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Upload W-2 PDFs, parse them in real-time, and drill down into detailed results**")
    
    # Sidebar
    st.sidebar.header("🔧 Parser Settings")
    
    # API Key check
    if not os.getenv('OPENAI_API_KEY'):
        st.sidebar.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        st.error("OpenAI API key is required for GPT-4 Vision analysis. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Upload section
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 📁 Upload W-2 PDF")
    uploaded_file = st.file_uploader(
        "Choose a W-2 PDF file",
        type=['pdf'],
        help="Upload a W-2 PDF file to parse and analyze"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file is not None:
        # Display file info
        st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        # Parse button
        if st.button("🚀 Parse W-2 Document", type="primary"):
            with st.spinner("Parsing W-2 document... This may take 15-45 seconds."):
                # Parse the uploaded file
                result = parse_uploaded_w2(uploaded_file)
                
                # Store result in session state
                st.session_state.parsed_result = result
                st.session_state.file_name = uploaded_file.name
        
        # Display results if available
        if 'parsed_result' in st.session_state:
            result = st.session_state.parsed_result
            file_name = st.session_state.get('file_name', 'Unknown')
            
            st.markdown("---")
            st.markdown(f"## 📋 Parsed Results: {file_name}")
            
            # Display parsing status
            if display_parsing_status(result):
                
                # Basic information
                display_basic_info(result)
                
                # Financial summary
                display_financial_summary(result)
                
                # Detailed breakdown
                display_detailed_breakdown(result)
                
                # Income visualization
                create_income_visualization(result)
                
                # Export options
                export_results(result)
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ## 🚀 How to Use This Dashboard
        
        1. **Upload a W-2 PDF** using the file uploader above
        2. **Click "Parse W-2 Document"** to process the file
        3. **Review the results** in the detailed breakdown below
        4. **Export the data** in JSON or CSV format
        
        ### 📋 What Gets Extracted
        
        - **Employee Information**: Name, SSN (masked), address
        - **Employer Information**: Company name, EIN, address
        - **Income Data**: Wages, tips, compensation (Box 1-6)
        - **Tax Information**: Federal, state, local tax withholdings
        - **Box 12 Codes**: All benefit codes and amounts
        - **Calculated Income**: Annual and monthly income for mortgage approval
        
        ### 🎯 Confidence Scoring
        
        The parser provides confidence scores based on:
        - **Extraction Method Success**: Higher scores for successful Camelot + GPT Vision processing
        - **Data Completeness**: Presence of key fields (employee name, wages, taxes)
        - **Processing Quality**: Whether GPT-4 Vision validation was used
        - **Error Handling**: Lower scores when fallback methods are needed
        
        ### ⚡ Processing Time
        
        - **Typical processing time**: 15-45 seconds per document
        - **Factors affecting speed**: PDF complexity, image quality, API response time
        - **Confidence score**: Higher scores indicate more reliable extraction
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Interactive W-2 Parser Dashboard** | "
        f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

if __name__ == "__main__":
    main()
