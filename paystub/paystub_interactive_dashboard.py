"""
Interactive Paystub Parser Dashboard

A dynamic Streamlit dashboard that allows users to upload paystub PDFs,
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

# Import the Paystub parser
import sys
import os

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.ai.parser.paystub.paystub_parser import PaystubParser

# Page configuration
st.set_page_config(
    page_title="Interactive Paystub Parser Dashboard",
    page_icon="💰",
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
    .earnings-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .employer-contribution {
        background-color: #e3f2fd;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #2196f3;
    }
    .employee-earnings {
        background-color: #e8f5e8;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 3px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

def initialize_parser():
    """Initialize the Paystub parser"""
    if 'paystub_parser' not in st.session_state:
        st.session_state.paystub_parser = PaystubParser()
    return st.session_state.paystub_parser

def parse_uploaded_paystub(uploaded_file) -> Dict[str, Any]:
    """
    Parse an uploaded paystub PDF file
    
    Args:
        uploaded_file: Uploaded file object from Streamlit
        
    Returns:
        Parsed paystub data as dictionary
    """
    parser = initialize_parser()
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Parse the paystub
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
        result: Parsed paystub data
    """
    if result.get('error'):
        st.markdown('<div class="parsing-status error-status">', unsafe_allow_html=True)
        st.error(f"❌ Parsing Failed: {result['error']}")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    confidence = result.get('extraction_confidence', 0) or 0
    
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
    Display basic paystub information
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("📋 Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👤 Employee Information**")
        employee = result.get('employee', {})
        st.write(f"**Name:** {employee.get('name', 'N/A')}")
        st.write(f"**SSN:** {employee.get('ssn_masked', 'N/A')}")
        
        address = employee.get('address', {})
        if address:
            st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
    
    with col2:
        st.markdown("**🏢 Employer Information**")
        employer = result.get('employer', {})
        st.write(f"**Company:** {employer.get('company_name', 'N/A')}")
        st.write(f"**Employee ID:** {employer.get('employee_id', 'N/A')}")
        
        emp_address = employer.get('address', {})
        if emp_address:
            st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")

def display_payroll_period(result: Dict[str, Any]):
    """
    Display payroll period information
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("📅 Payroll Period")
    
    payroll_period = result.get('payroll_period', {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Start Date:** {payroll_period.get('start_date', 'N/A')}")
    with col2:
        st.write(f"**End Date:** {payroll_period.get('end_date', 'N/A')}")
    with col3:
        st.write(f"**Pay Date:** {payroll_period.get('pay_date', 'N/A')}")
    
    pay_frequency = result.get('pay_frequency', 'N/A')
    st.write(f"**Pay Frequency:** {pay_frequency}")

def display_financial_summary(result: Dict[str, Any]):
    """
    Display financial summary with key metrics
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("💰 Financial Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gross_pay = float(result.get('gross_pay_current', 0) or 0)
        st.metric(
            label="Gross Pay (Current)",
            value=f"${gross_pay:,.2f}",
            help="Total gross pay for this period"
        )
    
    with col2:
        net_pay = float(result.get('net_pay_current', 0) or 0)
        st.metric(
            label="Net Pay (Current)",
            value=f"${net_pay:,.2f}",
            help="Take-home pay after deductions and taxes"
        )
    
    with col3:
        gross_ytd = float(result.get('gross_pay_ytd', 0) or 0)
        st.metric(
            label="Gross Pay (YTD)",
            value=f"${gross_ytd:,.2f}",
            help="Year-to-date gross pay"
        )
    
    with col4:
        # Calculate total deductions
        deductions = result.get('deductions', [])
        total_deductions = sum(float(d.get('current_amount', 0) or 0) for d in deductions)
        st.metric(
            label="Total Deductions",
            value=f"${total_deductions:,.2f}",
            help="Total deductions for this period"
        )

def display_earnings_breakdown(result: Dict[str, Any]):
    """
    Display detailed earnings breakdown
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("💵 Earnings Breakdown")
    
    earnings = result.get('earnings', [])
    if not earnings:
        st.warning("No earnings data found")
        return
    
    # Calculate totals
    employee_earnings = 0
    employer_contributions = 0
    
    for earning in earnings:
        amount = float(earning.get('current_amount', 0) or 0)
        if earning.get('is_employer_contribution', False):
            employer_contributions += amount
        else:
            employee_earnings += amount
    
    # Display totals
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="employee-earnings">', unsafe_allow_html=True)
        st.metric("Employee Earnings", f"${employee_earnings:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="employer-contribution">', unsafe_allow_html=True)
        st.metric("Employer Contributions", f"${employer_contributions:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.metric("Total Earnings", f"${employee_earnings + employer_contributions:,.2f}")
    
    # Display individual earnings
    st.markdown("**Individual Earnings:**")
    
    for earning in earnings:
        desc = earning.get('description', 'N/A')
        amount = float(earning.get('current_amount', 0) or 0)
        rate = earning.get('rate', 'N/A')
        hours = earning.get('hours', 'N/A')
        ytd_amount = earning.get('ytd_amount', 'N/A')
        is_employer = earning.get('is_employer_contribution', False)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if is_employer:
                st.markdown(f'<div class="employer-contribution">{desc} (EMPLOYER)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="employee-earnings">{desc}</div>', unsafe_allow_html=True)
        
        with col2:
            st.write(f"${amount:,.2f}")
        
        with col3:
            st.write(f"${rate}" if rate != 'N/A' else 'N/A')
        
        with col4:
            st.write(f"{hours}" if hours != 'N/A' else 'N/A')
        
        with col5:
            st.write(f"${ytd_amount:,.2f}" if ytd_amount is not None and ytd_amount != 'N/A' else 'N/A')

def display_deductions_breakdown(result: Dict[str, Any]):
    """
    Display deductions breakdown
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("💸 Deductions Breakdown")
    
    deductions = result.get('deductions', [])
    if not deductions:
        st.info("No deductions found")
        return
    
    # Calculate totals
    pre_tax_total = 0
    post_tax_total = 0
    
    for deduction in deductions:
        amount = float(deduction.get('current_amount', 0) or 0)
        if deduction.get('is_pre_tax', False):
            pre_tax_total += amount
        else:
            post_tax_total += amount
    
    # Display totals
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Pre-Tax Deductions", f"${pre_tax_total:,.2f}")
    
    with col2:
        st.metric("Post-Tax Deductions", f"${post_tax_total:,.2f}")
    
    with col3:
        st.metric("Total Deductions", f"${pre_tax_total + post_tax_total:,.2f}")
    
    # Display individual deductions
    st.markdown("**Individual Deductions:**")
    
    for deduction in deductions:
        desc = deduction.get('description', 'N/A')
        amount = float(deduction.get('current_amount', 0) or 0)
        ytd_amount = deduction.get('ytd_amount', 'N/A')
        is_pre_tax = deduction.get('is_pre_tax', False)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write(desc)
        
        with col2:
            st.write(f"${amount:,.2f}")
        
        with col3:
            st.write(f"${ytd_amount:,.2f}" if ytd_amount is not None and ytd_amount != 'N/A' else 'N/A')
        
        with col4:
            st.write("Pre-Tax" if is_pre_tax else "Post-Tax")

def display_taxes_breakdown(result: Dict[str, Any]):
    """
    Display taxes breakdown
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("🏛️ Taxes Breakdown")
    
    taxes = result.get('taxes', [])
    if not taxes:
        st.info("No tax information found")
        return
    
    # Calculate total taxes
    total_taxes = sum(float(t.get('current_amount', 0) or 0) for t in taxes)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Taxes", f"${total_taxes:,.2f}")
    
    with col2:
        gross_pay = float(result.get('gross_pay_current', 0) or 0)
        if gross_pay > 0:
            tax_rate = (total_taxes / gross_pay) * 100
            st.metric("Effective Tax Rate", f"{tax_rate:.1f}%")
    
    # Display individual taxes
    st.markdown("**Individual Taxes:**")
    
    for tax in taxes:
        tax_type = tax.get('tax_type', 'N/A')
        current_amount = float(tax.get('current_amount', 0) or 0)
        ytd_amount = tax.get('ytd_amount', 'N/A')
        taxable_wages = tax.get('taxable_wages_current', 'N/A')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write(tax_type)
        
        with col2:
            st.write(f"${current_amount:,.2f}")
        
        with col3:
            st.write(f"${ytd_amount:,.2f}" if ytd_amount is not None and ytd_amount != 'N/A' else 'N/A')
        
        with col4:
            st.write(f"${taxable_wages:,.2f}" if taxable_wages is not None and taxable_wages != 'N/A' else 'N/A')

def display_validation_warnings(result: Dict[str, Any]):
    """
    Display validation warnings if any
    
    Args:
        result: Parsed paystub data
    """
    warnings = result.get('validation_warnings', [])
    if warnings:
        st.subheader("⚠️ Validation Warnings")
        
        for warning in warnings:
            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
            st.warning(warning)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.subheader("✅ Validation Status")
        st.success("No validation warnings - all data looks good!")

def create_earnings_visualization(result: Dict[str, Any]):
    """
    Create earnings visualization charts
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("📊 Earnings Visualization")
    
    earnings = result.get('earnings', [])
    if not earnings:
        st.info("No earnings data available for visualization")
        return
    
    # Prepare data for visualization
    employee_earnings = []
    employer_contributions = []
    
    for earning in earnings:
        desc = earning.get('description', 'Unknown')
        amount = float(earning.get('current_amount', 0) or 0)
        is_employer = earning.get('is_employer_contribution', False)
        
        if is_employer:
            employer_contributions.append({'Description': desc, 'Amount': amount, 'Type': 'Employer'})
        else:
            employee_earnings.append({'Description': desc, 'Amount': amount, 'Type': 'Employee'})
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Employee earnings pie chart
        if employee_earnings:
            df_employee = pd.DataFrame(employee_earnings)
            fig_pie = px.pie(
                df_employee,
                values='Amount',
                names='Description',
                title="Employee Earnings Breakdown",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No employee earnings data for visualization")
    
    with col2:
        # Combined earnings bar chart
        all_earnings = employee_earnings + employer_contributions
        if all_earnings:
            df_all = pd.DataFrame(all_earnings)
            fig_bar = px.bar(
                df_all,
                x='Description',
                y='Amount',
                color='Type',
                title="All Earnings by Type",
                color_discrete_map={'Employee': '#4caf50', 'Employer': '#2196f3'}
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No earnings data for visualization")

def create_deductions_visualization(result: Dict[str, Any]):
    """
    Create deductions visualization charts
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("📊 Deductions Visualization")
    
    deductions = result.get('deductions', [])
    if not deductions:
        st.info("No deductions data available for visualization")
        return
    
    # Prepare data for visualization
    deduction_data = []
    for deduction in deductions:
        desc = deduction.get('description', 'Unknown')
        amount = float(deduction.get('current_amount', 0) or 0)
        is_pre_tax = deduction.get('is_pre_tax', False)
        deduction_data.append({
            'Description': desc,
            'Amount': amount,
            'Type': 'Pre-Tax' if is_pre_tax else 'Post-Tax'
        })
    
    if deduction_data:
        df = pd.DataFrame(deduction_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Deductions pie chart
            fig_pie = px.pie(
                df,
                values='Amount',
                names='Description',
                title="Deductions Breakdown",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Deductions by type bar chart
            fig_bar = px.bar(
                df,
                x='Description',
                y='Amount',
                color='Type',
                title="Deductions by Type",
                color_discrete_map={'Pre-Tax': '#ff9800', 'Post-Tax': '#f44336'}
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)

def export_results(result: Dict[str, Any]):
    """
    Provide export options for the parsed results
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("📥 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_data = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="📄 Download as JSON",
            data=json_data,
            file_name=f"paystub_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Summary CSV export
        employee = result.get('employee', {})
        employer = result.get('employer', {})
        
        summary_data = {
            'Field': [
                'Employee Name',
                'Employer Name',
                'Pay Period Start',
                'Pay Period End',
                'Gross Pay Current',
                'Net Pay Current',
                'Gross Pay YTD',
                'Total Deductions',
                'Total Taxes',
                'Confidence Score'
            ],
            'Value': [
                employee.get('name', 'N/A'),
                employer.get('company_name', 'N/A'),
                result.get('payroll_period', {}).get('start_date', 'N/A'),
                result.get('payroll_period', {}).get('end_date', 'N/A'),
                f"${float(result.get('gross_pay_current', 0) or 0):,.2f}",
                f"${float(result.get('net_pay_current', 0) or 0):,.2f}",
                f"${float(result.get('gross_pay_ytd', 0) or 0):,.2f}",
                f"${sum(float(d.get('current_amount', 0) or 0) for d in result.get('deductions', [])):,.2f}",
                f"${sum(float(t.get('current_amount', 0) or 0) for t in result.get('taxes', [])):,.2f}",
                f"{(result.get('extraction_confidence', 0) or 0):.2%}"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        csv_data = summary_df.to_csv(index=False)
        
        st.download_button(
            label="📊 Download Summary as CSV",
            data=csv_data,
            file_name=f"paystub_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">💰 Interactive Paystub Parser Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Upload paystub PDFs, parse them in real-time, and drill down into detailed results**")
    
    # Sidebar
    st.sidebar.header("🔧 Parser Settings")
    
    # API Key check
    if not os.getenv('OPENAI_API_KEY'):
        st.sidebar.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        st.error("OpenAI API key is required for GPT-4 Vision analysis. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Upload section
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 📁 Upload Paystub PDF")
    uploaded_file = st.file_uploader(
        "Choose a paystub PDF file",
        type=['pdf'],
        help="Upload a paystub PDF file to parse and analyze"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file is not None:
        # Display file info
        st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        # Parse button
        if st.button("🚀 Parse Paystub Document", type="primary"):
            with st.spinner("Parsing paystub document... This may take 15-45 seconds."):
                # Parse the uploaded file
                result = parse_uploaded_paystub(uploaded_file)
                
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
                
                # Payroll period
                display_payroll_period(result)
                
                # Financial summary
                display_financial_summary(result)
                
                # Earnings breakdown
                display_earnings_breakdown(result)
                
                # Deductions breakdown
                display_deductions_breakdown(result)
                
                # Taxes breakdown
                display_taxes_breakdown(result)
                
                # Validation warnings
                display_validation_warnings(result)
                
                # Visualizations
                create_earnings_visualization(result)
                create_deductions_visualization(result)
                
                # Export options
                export_results(result)
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ## 🚀 How to Use This Dashboard
        
        1. **Upload a paystub PDF** using the file uploader above
        2. **Click "Parse Paystub Document"** to process the file
        3. **Review the results** in the detailed breakdown below
        4. **Export the data** in JSON or CSV format
        
        ### 📋 What Gets Extracted
        
        - **Employee Information**: Name, SSN (masked), address
        - **Employer Information**: Company name, employee ID, address
        - **Payroll Period**: Start date, end date, pay date, frequency
        - **Earnings Data**: Regular pay, overtime, bonuses, commissions, holiday pay
        - **Deductions**: Pre-tax and post-tax deductions with descriptions
        - **Taxes**: Federal, state, local tax withholdings
        - **Financial Summary**: Gross pay, net pay, YTD amounts
        
        ### 🎯 Confidence Scoring
        
        The parser provides confidence scores based on:
        - **Extraction Method Success**: Higher scores for successful Camelot + GPT Vision processing
        - **Data Completeness**: Presence of key fields (employee name, gross pay, earnings)
        - **Processing Quality**: Whether GPT-4 Vision validation was used
        - **Error Handling**: Lower scores when fallback methods are needed
        
        ### ⚡ Processing Time
        
        - **Typical processing time**: 15-45 seconds per document
        - **Factors affecting speed**: PDF complexity, image quality, API response time
        - **Confidence score**: Higher scores indicate more reliable extraction
        
        ### 🔍 Validation Features
        
        - **Mathematical Consistency**: Checks earnings vs gross pay alignment
        - **Data Quality**: Validates reasonable pay rates and amounts
        - **Structure Validation**: Ensures proper paystub format recognition
        - **Warning System**: Flags potential issues for manual review
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Interactive Paystub Parser Dashboard** | "
        f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

if __name__ == "__main__":
    main()
