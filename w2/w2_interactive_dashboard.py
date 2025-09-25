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
    initial_sidebar_state="collapsed"
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

def parse_multiple_w2s(uploaded_files) -> Dict[str, Dict[str, Any]]:
    """
    Parse multiple uploaded W-2 PDF files
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
        
    Returns:
        Dictionary mapping file names to parsed W-2 data
    """
    results = {}
    parser = initialize_parser()
    
    for uploaded_file in uploaded_files:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Parse the W-2
            result = parser.parse_pdf(tmp_path)
            results[uploaded_file.name] = result
        except Exception as e:
            # Store error result for this file
            results[uploaded_file.name] = {
                'error': f"Failed to parse {uploaded_file.name}: {str(e)}",
                'confidence_score': 0
            }
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    return results

def display_parsing_status(result: Dict[str, Any]):
    """
    Display parsing status and basic information
    
    Args:
        result: Parsed W-2 data
    """
    if result.get('error'):
        st.markdown('<div class="parsing-status error-status">', unsafe_allow_html=True)
        st.error(f"Parsing Failed: {result['error']}")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    confidence = result.get('confidence_score', 0) or 0
    
    if confidence >= 0.95:
        status_class = "success-status"
        status_text = "Excellent"
    elif confidence >= 0.90:
        status_class = "success-status"
        status_text = "Very Good"
    elif confidence >= 0.85:
        status_class = "warning-status"
        status_text = "Good"
    else:
        status_class = "warning-status"
        status_text = "Needs Review"
    
    st.markdown(f'<div class="parsing-status {status_class}">', unsafe_allow_html=True)
    st.success(f"Parsing {status_text} - Confidence: {confidence:.1%}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    return True

def display_basic_info(result: Dict[str, Any], file_key: str = ""):
    """
    Display basic W-2 information
    
    Args:
        result: Parsed W-2 data
        file_key: Unique key for this file to avoid duplicate element IDs
    """
    st.subheader("Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Employee Information**")
        employee = result.get('employee', {})
        st.write(f"**Name:** {employee.get('name', 'N/A')}")
        st.write(f"**SSN:** {employee.get('ssn', 'N/A')}")
        
        address = employee.get('address', {})
        if address:
            st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
    
    with col2:
        st.markdown("**Employer Information**")
        employer = result.get('employer', {})
        st.write(f"**Company:** {employer.get('name', 'N/A')}")
        st.write(f"**EIN:** {employer.get('ein', 'N/A')}")
        st.write(f"**Control Number:** {employer.get('control_number', 'N/A')}")
        
        emp_address = employer.get('address', {})
        if emp_address:
            st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")
        
        # Income Used multiselect
        st.markdown("**Income Used:**")
        income_sources = st.multiselect(
            "Select income sources used:",
            ["W-2s", "Personal Tax Returns", "1120's", "1099s", "Bank Statements", "Other"],
            default=["W-2s"],
            help="Select all income sources used for this person",
            key=f"income_sources_{file_key}"
        )

def display_financial_summary(result: Dict[str, Any]):
    """
    Display financial summary with key metrics
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("Financial Summary")
    
    income_info = result.get('income_tax_info', {})
    calculated_income = result.get('calculated_income', {})
    
    # Calculate additional metrics
    income_classification = calculate_income_classification(result)
    ytd_income_support, ytd_reason = calculate_ytd_income_support(result)
    
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
    
    # Additional classification and verification metrics
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Income Classification:**")
        st.write(f"**Status:** {income_classification}")
        if income_classification == "Part-time":
            st.info("Part-time employment detected based on income level")
        else:
            st.success("Full-time employment detected")
    
    with col2:
        st.markdown("**YTD Income Support:**")
        st.write(f"**Verification:** {ytd_income_support}")
        if ytd_income_support == "Yes - Verified":
            st.success("Income data is consistent and verified")
        else:
            st.warning(f"**Issue:** {ytd_reason}")

def display_detailed_breakdown(result: Dict[str, Any]):
    """
    Display detailed breakdown of W-2 data in the same format as w2_dashboard.py
    
    Args:
        result: Parsed W-2 data
    """
    st.subheader("Detailed Document Review")
    
    # Income Information
    st.subheader("Income & Tax Information")
    
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
        st.subheader("State & Local Tax Information")
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
        st.subheader("Processing Information")
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


def create_income_visualization(result: Dict[str, Any], chart_key: str = ""):
    """
    Create income visualization charts
    
    Args:
        result: Parsed W-2 data
        chart_key: Unique key for this chart to avoid duplicate element IDs
    """
    st.subheader("Income Visualization")
    
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
            st.plotly_chart(fig_pie, use_container_width=True, key=f"w2_income_pie_{chart_key}")
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
        st.plotly_chart(fig_bar, use_container_width=True, key=f"w2_income_bar_{chart_key}")

def calculate_income_classification(result: Dict[str, Any]) -> str:
    """
    Calculate income classification based on W-2 data
    
    Args:
        result: Parsed W-2 data
        
    Returns:
        "Part-time" or "Full-time" classification
    """
    # For W-2s, we don't have hours information, so we'll use a different approach
    # We can look at the wages and make an assumption, or use a default classification
    # Since W-2s are typically annual documents, we'll default to "Full-time"
    # unless there are specific indicators of part-time work
    
    income_info = result.get('income_tax_info', {})
    wages = income_info.get('wages_tips_compensation', 0) or 0
    
    # If wages are very low (less than $20,000), might indicate part-time
    if wages < 20000:
        return "Part-time"
    else:
        return "Full-time"

def calculate_ytd_income_support(result: Dict[str, Any]) -> tuple[str, str]:
    """
    Calculate YTD income support verification with detailed feedback
    
    Args:
        result: Parsed W-2 data
        
    Returns:
        Tuple of (verification_status, detailed_reason)
    """
    income_info = result.get('income_tax_info', {})
    wages = income_info.get('wages_tips_compensation', 0) or 0
    ss_wages = income_info.get('social_security_wages', 0) or 0
    medicare_wages = income_info.get('medicare_wages_tips', 0) or 0
    federal_tax = income_info.get('federal_income_tax_withheld', 0) or 0
    
    # Check for basic data completeness
    missing_fields = []
    if wages <= 0:
        missing_fields.append("Box 1 (Wages) is missing or zero")
    if ss_wages <= 0:
        missing_fields.append("Box 3 (SS Wages) is missing or zero")
    if medicare_wages <= 0:
        missing_fields.append("Box 5 (Medicare Wages) is missing or zero")
    if federal_tax < 0:
        missing_fields.append("Box 2 (Federal Tax) has invalid value")
    
    if missing_fields:
        return "No - Not Verified", f"Missing or invalid data: {', '.join(missing_fields)}"
    
    # Check for reasonable income amounts
    if wages > 1000000:  # Over $1M might need verification
        return "No - Not Verified", f"Unusually high income (${wages:,.0f}) - may need additional verification"
    
    if wages < 1000:  # Under $1K might be incomplete
        return "No - Not Verified", f"Very low income (${wages:,.0f}) - may be incomplete or part-time"
    
    # Check for box consistency (with more realistic tolerance)
    if wages > 0 and ss_wages > 0:
        wage_diff_percent = abs(wages - ss_wages) / max(wages, 1) * 100
        if wage_diff_percent > 20:  # More realistic 20% tolerance
            return "No - Not Verified", f"Significant difference between Box 1 (${wages:,.0f}) and Box 3 (${ss_wages:,.0f}) - {wage_diff_percent:.1f}% difference may indicate retirement contributions or data issues"
    
    # Check tax year
    tax_year = result.get('tax_year', '')
    if not tax_year or int(tax_year) < 2020:
        return "No - Not Verified", f"Old or missing tax year ({tax_year}) - current year W-2s preferred"
    
    # All checks passed
    return "Yes - Verified", "All income data appears consistent and complete"

def calculate_monthly_qualifying_income(result: Dict[str, Any]) -> float:
    """
    Calculate monthly qualifying income from W-2 data
    
    Args:
        result: Parsed W-2 data
        
    Returns:
        Monthly qualifying income amount
    """
    calculated_income = result.get('calculated_income', {})
    annual_income = calculated_income.get('annual_income', 0) or 0
    
    # Convert annual income to monthly
    monthly_income = annual_income / 12
    
    return monthly_income

def calculate_total_annual_income(results: Dict[str, Dict[str, Any]]) -> float:
    """
    Calculate total annual income from all W-2 files
    
    Args:
        results: Dictionary mapping file names to parsed W-2 data
        
    Returns:
        Total annual income amount
    """
    total_income = 0
    
    for file_name, result in results.items():
        if not result.get('error'):
            calculated_income = result.get('calculated_income', {})
            annual_income = calculated_income.get('annual_income', 0) or 0
            total_income += float(annual_income)
    
    return total_income

def display_total_monthly_income(results: Dict[str, Dict[str, Any]]):
    """
    Display total monthly qualifying income for all W-2 sources
    
    Args:
        results: Dictionary mapping file names to parsed W-2 data
    """
    st.subheader("Total Monthly Qualifying Income")
    
    # Calculate total income for each source
    income_sources = []
    total_annual_income = 0
    total_monthly_income = 0
    
    for file_name, result in results.items():
        if not result.get('error'):
            employee = result.get('employee', {})
            employer = result.get('employer', {})
            calculated_income = result.get('calculated_income', {})
            annual_income = calculated_income.get('annual_income', 0) or 0
            monthly_income = calculate_monthly_qualifying_income(result)
            
            if annual_income > 0:
                income_sources.append({
                    'Source': f"{employee.get('name', 'Unknown')} - {employer.get('name', 'Unknown Company')}",
                    'Tax Year': result.get('tax_year', 'N/A'),
                    'Annual Income': f"${annual_income:,.2f}",
                    'Monthly Income': f"${monthly_income:,.2f}",
                    'File': file_name
                })
                total_annual_income += annual_income
                total_monthly_income += monthly_income
    
    # Display income sources
    if income_sources:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Income Sources:**")
            for source in income_sources:
                st.write(f"• {source['Source']} ({source['Tax Year']}): {source['Annual Income']} annually / {source['Monthly Income']} monthly")
        
        with col2:
            st.markdown("**Total Qualifying Income:**")
            st.metric(
                label="Annual Income",
                value=f"${total_annual_income:,.2f}",
                help="Sum of all annual income sources"
            )
            st.metric(
                label="Monthly Income",
                value=f"${total_monthly_income:,.2f}",
                help="Sum of all monthly income sources"
            )
    else:
        st.info("No qualifying income sources found")

def display_total_annual_income(results: Dict[str, Dict[str, Any]]):
    """
    Display total annual income for all W-2 sources
    
    Args:
        results: Dictionary mapping file names to parsed W-2 data
    """
    st.subheader("Total Annual Income Summary")
    
    # Calculate total income for each source
    income_sources = []
    total_annual_income = 0
    
    for file_name, result in results.items():
        if not result.get('error'):
            employee = result.get('employee', {})
            employer = result.get('employer', {})
            calculated_income = result.get('calculated_income', {})
            annual_income = calculated_income.get('annual_income', 0) or 0
            
            if annual_income > 0:
                income_sources.append({
                    'Source': f"{employee.get('name', 'Unknown')} - {employer.get('name', 'Unknown Company')}",
                    'Tax Year': result.get('tax_year', 'N/A'),
                    'Annual Income': f"${annual_income:,.2f}",
                    'File': file_name
                })
                total_annual_income += annual_income
    
    # Display income sources
    if income_sources:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Income Sources:**")
            for source in income_sources:
                st.write(f"• {source['Source']} ({source['Tax Year']}): {source['Annual Income']}")
        
        with col2:
            st.markdown("**Total Annual Income:**")
            st.metric(
                label="Qualifying Income",
                value=f"${total_annual_income:,.2f}",
                help="Sum of all annual income sources"
            )
    else:
        st.info("No qualifying income sources found")

def display_multiple_files_summary(results: Dict[str, Dict[str, Any]]):
    """
    Display summary of all uploaded W-2 files
    
    Args:
        results: Dictionary mapping file names to parsed W-2 data
    """
    st.subheader("Files Summary")
    
    # Create summary data
    summary_data = []
    total_files = len(results)
    successful_parses = 0
    total_annual_income = 0
    
    for file_name, result in results.items():
        if result.get('error'):
            status = "Error"
            confidence = 0
            annual_income = 0
        else:
            status = "Success"
            confidence = result.get('confidence_score', 0) or 0
            calculated_income = result.get('calculated_income', {})
            annual_income = calculated_income.get('annual_income', 0) or 0
            successful_parses += 1
            total_annual_income += float(annual_income)
        
        employee_name = result.get('employee', {}).get('name', 'N/A') if not result.get('error') else 'N/A'
        employer_name = result.get('employer', {}).get('name', 'N/A') if not result.get('error') else 'N/A'
        tax_year = result.get('tax_year', 'N/A') if not result.get('error') else 'N/A'
        
        summary_data.append({
            'File Name': file_name,
            'Status': status,
            'Employee': employee_name,
            'Employer': employer_name,
            'Tax Year': tax_year,
            'Annual Income': f"${annual_income:,.2f}",
            'Confidence': f"{confidence:.1%}"
        })
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", total_files)
    
    with col2:
        st.metric("Successful Parses", f"{successful_parses}/{total_files}")
    
    with col3:
        st.metric("Total Annual Income", f"${total_annual_income:,.2f}")
    
    with col4:
        avg_confidence = sum(result.get('confidence_score', 0) or 0 for result in results.values() if not result.get('error')) / max(successful_parses, 1)
        st.metric("Average Confidence", f"{avg_confidence:.1%}")
    
    # Display summary table
    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)

def display_document_details(doc: Dict[str, Any], file_name: str, index: int):
    """
    Display detailed information for a single W-2 document in a collapsible section
    
    Args:
        doc: W-2 document data
        file_name: Name of the file
        index: Document index
    """
    # Determine status text
    if doc.get('error'):
        status_text = "Error"
    else:
        confidence = doc.get('confidence_score', 0) or 0
        if confidence >= 0.95:
            status_text = "Excellent"
        elif confidence >= 0.90:
            status_text = "Very Good"
        elif confidence >= 0.85:
            status_text = "Good"
        else:
            status_text = "Needs Review"
    
    # Check for validation warnings
    warnings = doc.get('validation_warnings', [])
    has_warnings = warnings and len(warnings) > 0
    
    # Create expander title with status and warning indicator
    if has_warnings:
        expander_title = f"Document {index + 1}: {file_name} ({status_text}) - Warning"
    else:
        expander_title = f"Document {index + 1}: {file_name} ({status_text})"
    
    with st.expander(expander_title, expanded=False):
        
        # Display parsing status
        if not display_parsing_status(doc):
            return
        
        # Basic information
        file_key = f"{index}_{file_name.replace('.', '_').replace(' ', '_')}"
        display_basic_info(doc, file_key)
        st.markdown("---")
        
        # Financial summary
        display_financial_summary(doc)
        st.markdown("---")
        
        # Detailed breakdown
        display_detailed_breakdown(doc)
        st.markdown("---")
        
        # Income visualization
        chart_key = f"{index}_{file_name.replace('.', '_').replace(' ', '_')}"
        create_income_visualization(doc, chart_key)
        st.markdown("---")
        
        # Export options for individual file
        file_key = f"{index}_{file_name.replace('.', '_').replace(' ', '_')}"
        export_results(doc, file_key)

def export_multiple_results(results: Dict[str, Dict[str, Any]]):
    """
    Provide export options for multiple parsed W-2 results
    
    Args:
        results: Dictionary mapping file names to parsed W-2 data
    """
    st.subheader("Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Combined JSON export
        json_data = json.dumps(results, indent=2, default=str)
        st.download_button(
            label="Download All as JSON",
            data=json_data,
            file_name=f"w2s_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="w2_multiple_json_download"
        )
    
    with col2:
        # Summary CSV export for all files
        summary_data = []
        
        for file_name, result in results.items():
            if not result.get('error'):
                employee = result.get('employee', {})
                employer = result.get('employer', {})
                income_info = result.get('income_tax_info', {})
                calculated_income = result.get('calculated_income', {})
                
                summary_data.append({
                    'File Name': file_name,
                    'Employee Name': employee.get('name', 'N/A'),
                    'Employer Name': employer.get('name', 'N/A'),
                    'Tax Year': result.get('tax_year', 'N/A'),
                    'Wages (Box 1)': f"${income_info.get('wages_tips_compensation', 0) or 0:,.2f}",
                    'Federal Tax (Box 2)': f"${income_info.get('federal_income_tax_withheld', 0) or 0:,.2f}",
                    'Annual Income': f"${calculated_income.get('annual_income', 0) or 0:,.2f}",
                    'Monthly Income': f"${calculated_income.get('monthly_income', 0) or 0:,.2f}",
                    'Confidence Score': f"{(result.get('confidence_score', 0) or 0):.2%}"
                })
            else:
                summary_data.append({
                    'File Name': file_name,
                    'Employee Name': 'ERROR',
                    'Employer Name': 'ERROR',
                    'Tax Year': 'ERROR',
                    'Wages (Box 1)': 'ERROR',
                    'Federal Tax (Box 2)': 'ERROR',
                    'Annual Income': 'ERROR',
                    'Monthly Income': 'ERROR',
                    'Confidence Score': '0.0%'
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            csv_data = summary_df.to_csv(index=False)
            
            st.download_button(
                label="Download Summary as CSV",
                data=csv_data,
                file_name=f"w2s_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="w2_multiple_csv_download"
            )

def export_results(result: Dict[str, Any], file_key: str = ""):
    """
    Provide export options for the parsed results
    
    Args:
        result: Parsed W-2 data
        file_key: Unique key for this file to avoid duplicate element IDs
    """
    st.subheader("Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_data = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name=f"w2_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"w2_json_download_{file_key}"
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
            label="Download Summary as CSV",
            data=csv_data,
            file_name=f"w2_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key=f"w2_csv_download_{file_key}"
        )

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">Interactive W-2 Parser Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Upload W-2 PDFs, parse them in real-time, and drill down into detailed results**")
    
    # API Key check
    if not os.getenv('OPENAI_API_KEY'):
        st.error("OpenAI API key is required for GPT-4 Vision analysis. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Upload section
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### Upload W-2 PDFs")
    
    # Upload mode selection
    upload_mode = st.radio(
        "Choose upload mode:",
        ["Single File", "Multiple Files"],
        index=1,  # Default to "Multiple Files"
        horizontal=True,
        help="Select whether to upload one file or multiple files at once"
    )
    
    if upload_mode == "Single File":
        uploaded_files = st.file_uploader(
            "Choose a W-2 PDF file",
            type=['pdf'],
            help="Upload a W-2 PDF file to parse and analyze"
        )
        if uploaded_files:
            uploaded_files = [uploaded_files]  # Convert to list for consistency
    else:
        uploaded_files = st.file_uploader(
            "Choose W-2 PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload multiple W-2 PDF files to parse and analyze"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_files is not None and len(uploaded_files) > 0:
        # Display file info
        if len(uploaded_files) == 1:
            st.info(f"**File:** {uploaded_files[0].name} ({uploaded_files[0].size:,} bytes)")
        else:
            file_info = []
            total_size = 0
            for file in uploaded_files:
                file_info.append(f"{file.name} ({file.size:,} bytes)")
                total_size += file.size
            st.info(f"**Files:** {len(uploaded_files)} files selected (Total: {total_size:,} bytes)")
            for info in file_info:
                st.write(f"  • {info}")
        
        # Parse button
        button_text = f"Parse {'W-2 Document' if len(uploaded_files) == 1 else f'{len(uploaded_files)} W-2 Documents'}"
        if st.button(button_text, type="primary"):
            if len(uploaded_files) == 1:
                # Single file processing
                with st.spinner("Parsing W-2 document... This may take 15-45 seconds."):
                    result = parse_uploaded_w2(uploaded_files[0])
                    results = {uploaded_files[0].name: result}
            else:
                # Multiple files processing
                with st.spinner(f"Parsing {len(uploaded_files)} W-2 documents... This may take several minutes."):
                    results = parse_multiple_w2s(uploaded_files)
            
            # Store results in session state
            st.session_state.parsed_results = results
            st.session_state.uploaded_files = uploaded_files
        
        # Display results if available
        if 'parsed_results' in st.session_state:
            results = st.session_state.parsed_results
            uploaded_files = st.session_state.get('uploaded_files', [])
            
            st.markdown("---")
            
            if len(results) == 1:
                # Single file display (original behavior)
                file_name = list(results.keys())[0]
                result = results[file_name]
                
                st.markdown(f"## Parsed Results: {file_name}")
                
                # Display parsing status
                if display_parsing_status(result):
                    
                    # Basic information
                    file_key = f"single_{file_name.replace('.', '_').replace(' ', '_')}"
                    display_basic_info(result, file_key)
                    
                    # Financial summary
                    display_financial_summary(result)
                    
                    # Detailed breakdown
                    display_detailed_breakdown(result)
                    
                    # Income visualization
                    chart_key = f"single_{file_name.replace('.', '_').replace(' ', '_')}"
                    create_income_visualization(result, chart_key)
                    
                    # Export options
                    file_key = f"single_{file_name.replace('.', '_').replace(' ', '_')}"
                    export_results(result, file_key)
            else:
                # Multiple files display
                st.markdown(f"## Parsed Results: {len(results)} Files")
                
                # Display total monthly qualifying income at the top
                display_total_monthly_income(results)
                
                # Display files summary
                display_multiple_files_summary(results)
                
                # Detailed document view with collapsible sections
                st.markdown("---")
                st.markdown("### Detailed Document Review")
                
                for index, (file_name, result) in enumerate(results.items()):
                    display_document_details(result, file_name, index)
                
                # Export options for multiple files
                st.markdown("---")
                export_multiple_results(results)
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ## How to Use This Dashboard
        
        1. **Choose upload mode**: Single file or multiple files
        2. **Upload W-2 PDF(s)** using the file uploader above
        3. **Click "Parse W-2 Document(s)"** to process the file(s)
        4. **Review the results** in the detailed breakdown below
        5. **Export the data** in JSON or CSV format
        
        ### Multiple File Upload Features
        
        - **Batch Processing**: Upload and parse multiple W-2s at once
        - **Summary View**: See overview of all uploaded files with status indicators
        - **Individual Details**: Select any file to view detailed breakdown
        - **Bulk Export**: Download all results as combined JSON or summary CSV
        - **Progress Tracking**: Monitor parsing progress for multiple files
        
        ### What Gets Extracted
        
        - **Employee Information**: Name, SSN (masked), address
        - **Employer Information**: Company name, EIN, address
        - **Income Data**: Wages, tips, compensation (Box 1-6)
        - **Tax Information**: Federal, state, local tax withholdings
        - **Box 12 Codes**: All benefit codes and amounts
        - **Calculated Income**: Annual and monthly income for mortgage approval
        
        ### Confidence Scoring
        
        The parser provides confidence scores based on:
        - **Extraction Method Success**: Higher scores for successful Camelot + GPT Vision processing
        - **Data Completeness**: Presence of key fields (employee name, wages, taxes)
        - **Processing Quality**: Whether GPT-4 Vision validation was used
        - **Error Handling**: Lower scores when fallback methods are needed
        
        ### Processing Time
        
        - **Single file**: 15-45 seconds per document
        - **Multiple files**: 15-45 seconds per document (processed sequentially)
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
