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

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from paystub_parser import PaystubParser

# Page configuration
st.set_page_config(
    page_title="Interactive Paystub Parser Dashboard",
    page_icon="💰",
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

def parse_multiple_paystubs(uploaded_files) -> Dict[str, Dict[str, Any]]:
    """
    Parse multiple uploaded paystub PDF files
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
        
    Returns:
        Dictionary mapping file names to parsed paystub data
    """
    results = {}
    parser = initialize_parser()
    
    for uploaded_file in uploaded_files:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Parse the paystub
            result = parser.parse_pdf(tmp_path)
            results[uploaded_file.name] = result
        except Exception as e:
            # Store error result for this file
            results[uploaded_file.name] = {
                'error': f"Failed to parse {uploaded_file.name}: {str(e)}",
                'extraction_confidence': 0
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
        result: Parsed paystub data
    """
    if result.get('error'):
        st.markdown('<div class="parsing-status error-status">', unsafe_allow_html=True)
        st.error(f"Parsing Failed: {result['error']}")
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    confidence = result.get('extraction_confidence', 0) or 0
    
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

def display_basic_info(result: Dict[str, Any]):
    """
    Display basic paystub information
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Employee Information**")
        employee = result.get('employee', {})
        st.write(f"**Name:** {employee.get('name', 'N/A')}")
        st.write(f"**SSN:** {employee.get('ssn_masked', 'N/A')}")
        
        address = employee.get('address', {})
        if address:
            st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
    
    with col2:
        st.markdown("**Employer Information**")
        employer = result.get('employer', {})
        st.write(f"**Company:** {employer.get('company_name', 'N/A')}")
        st.write(f"**Employee ID:** {employer.get('employee_id', 'N/A')}")
        
        emp_address = employer.get('address', {})
        if emp_address:
            st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")
        
        # Income Used toggle
        st.markdown("**Income Used:**")
        income_sources = ["Paystubs", "Personal Tax Returns", "1120's", "Other Business Income"]
        selected_income = st.multiselect(
            "Select income sources:",
            options=income_sources,
            default=["Paystubs"],
            key=f"income_sources_{id(result)}"
        )

def calculate_income_classification(result: Dict[str, Any]) -> str:
    """
    Calculate income classification based on hours per week
    
    Args:
        result: Parsed paystub data
        
    Returns:
        'Part-time' or 'Full-time'
    """
    # Get total hours from earnings
    total_hours = 0
    earnings = result.get('earnings', [])
    
    for earning in earnings:
        if not earning.get('is_employer_contribution', False):
            hours = earning.get('hours', 0)
            if hours and hours != 'N/A':
                try:
                    total_hours += float(hours)
                except (ValueError, TypeError):
                    pass
    
    # If no hours found in earnings, try to get from total_hours_current
    if total_hours == 0:
        total_hours = result.get('total_hours_current', 0)
        if total_hours and total_hours != 'N/A':
            try:
                total_hours = float(total_hours)
            except (ValueError, TypeError):
                total_hours = 0
    
    # Determine classification
    if total_hours >= 40:
        return "Full-time"
    else:
        return "Part-time"

def calculate_ytd_income_support(result: Dict[str, Any]) -> tuple[str, str]:
    """
    Calculate YTD Income Support verification with detailed feedback
    
    Args:
        result: Parsed paystub data
        
    Returns:
        Tuple of (verification_status, detailed_reason)
    """
    # Get current period gross pay
    current_gross = float(result.get('gross_pay_current', 0) or 0)
    ytd_gross = float(result.get('gross_pay_ytd', 0) or 0)
    
    # Check for missing data
    missing_fields = []
    if current_gross == 0:
        missing_fields.append("Current period gross pay is missing or zero")
    if ytd_gross == 0:
        missing_fields.append("YTD gross pay is missing or zero")
    
    if missing_fields:
        return "No - Not Verified", f"Missing data: {', '.join(missing_fields)}"
    
    # Get pay frequency to calculate expected YTD
    pay_frequency = result.get('pay_frequency', '').lower()
    
    # Calculate expected YTD based on frequency
    if 'weekly' in pay_frequency:
        expected_periods = 26  # 52 weeks / 2
        frequency_desc = "weekly"
    elif 'bi-weekly' in pay_frequency or 'biweekly' in pay_frequency:
        expected_periods = 13  # 26 bi-weekly periods / 2
        frequency_desc = "bi-weekly"
    elif 'semi-monthly' in pay_frequency or 'semimonthly' in pay_frequency:
        expected_periods = 6   # 12 semi-monthly periods / 2
        frequency_desc = "semi-monthly"
    elif 'monthly' in pay_frequency:
        expected_periods = 6   # 12 months / 2
        frequency_desc = "monthly"
    else:
        # Default to bi-weekly if unknown
        expected_periods = 13
        frequency_desc = "bi-weekly (assumed)"
    
    expected_ytd = current_gross * expected_periods
    
    # Check if YTD is within 5% of expected
    if expected_ytd > 0:
        variance = abs(ytd_gross - expected_ytd) / expected_ytd
        variance_percent = variance * 100
        
        if variance <= 0.05:  # Within 5%
            return "Yes - Verified", f"YTD income (${ytd_gross:,.2f}) matches expected amount (${expected_ytd:,.2f}) for {frequency_desc} pay"
        else:
            if ytd_gross > expected_ytd:
                return "No - Not Verified", f"YTD income (${ytd_gross:,.2f}) is {variance_percent:.1f}% higher than expected (${expected_ytd:,.2f}) for {frequency_desc} pay - may indicate raises, bonuses, or overtime"
            else:
                return "No - Not Verified", f"YTD income (${ytd_gross:,.2f}) is {variance_percent:.1f}% lower than expected (${expected_ytd:,.2f}) for {frequency_desc} pay - may indicate recent start date, reduced hours, or missing pay periods"
    
    return "No - Not Verified", "Unable to calculate expected YTD income"

def display_payroll_period(result: Dict[str, Any]):
    """
    Display payroll period information with income classification and YTD support
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("Payroll Period & Income Analysis")
    
    payroll_period = result.get('payroll_period', {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Start Date:** {payroll_period.get('start_date', 'N/A')}")
    with col2:
        st.write(f"**End Date:** {payroll_period.get('end_date', 'N/A')}")
    with col3:
        st.write(f"**Pay Date:** {payroll_period.get('pay_date', 'N/A')}")
    
    # Pay frequency and income classification
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pay_frequency = result.get('pay_frequency', 'N/A')
        st.write(f"**Pay Frequency:** {pay_frequency}")
    
    with col2:
        income_classification = calculate_income_classification(result)
        st.write(f"**Income Classification:** {income_classification}")
    
    with col3:
        ytd_support, ytd_reason = calculate_ytd_income_support(result)
        st.write(f"**YTD Income Support:** {ytd_support}")
        if ytd_support == "No - Not Verified":
            st.warning(f"**Issue:** {ytd_reason}")
        else:
            st.success(f"**Details:** {ytd_reason}")

def display_financial_summary(result: Dict[str, Any]):
    """
    Display financial summary with key metrics
    
    Args:
        result: Parsed paystub data
    """
    st.subheader("Financial Summary")
    
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
    st.subheader("Earnings Breakdown")
    
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
    st.subheader("Deductions Breakdown")
    
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
    st.subheader("Taxes Breakdown")
    
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
        st.subheader("Validation Warnings")
        
        for warning in warnings:
            st.markdown('<div class="warning-box">', unsafe_allow_html=True)
            st.warning(warning)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.subheader("Validation Status")
        st.success("No validation warnings - all data looks good!")

def create_earnings_visualization(result: Dict[str, Any], chart_key: str = ""):
    """
    Create earnings visualization charts
    
    Args:
        result: Parsed paystub data
        chart_key: Unique key for this chart to avoid duplicate element IDs
    """
    st.subheader("Earnings Visualization")
    
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
            st.plotly_chart(fig_pie, use_container_width=True, key=f"earnings_pie_{chart_key}")
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
            st.plotly_chart(fig_bar, use_container_width=True, key=f"earnings_bar_{chart_key}")
        else:
            st.info("No earnings data for visualization")

def create_deductions_visualization(result: Dict[str, Any], chart_key: str = ""):
    """
    Create deductions visualization charts
    
    Args:
        result: Parsed paystub data
        chart_key: Unique key for this chart to avoid duplicate element IDs
    """
    st.subheader("Deductions Visualization")
    
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
            st.plotly_chart(fig_pie, use_container_width=True, key=f"deductions_pie_{chart_key}")
        
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
            st.plotly_chart(fig_bar, use_container_width=True, key=f"deductions_bar_{chart_key}")

def calculate_monthly_qualifying_income(result: Dict[str, Any]) -> float:
    """
    Calculate monthly qualifying income based on pay frequency
    
    Args:
        result: Parsed paystub data
        
    Returns:
        Monthly qualifying income amount
    """
    current_gross = float(result.get('gross_pay_current', 0) or 0)
    pay_frequency = result.get('pay_frequency', '').lower()
    
    if current_gross == 0:
        return 0.0
    
    # Convert to monthly based on pay frequency
    if 'weekly' in pay_frequency:
        return current_gross * 4.33  # 52 weeks / 12 months
    elif 'bi-weekly' in pay_frequency or 'biweekly' in pay_frequency:
        return current_gross * 2.17  # 26 bi-weekly periods / 12 months
    elif 'semi-monthly' in pay_frequency or 'semimonthly' in pay_frequency:
        return current_gross * 2  # 24 semi-monthly periods / 12 months
    elif 'monthly' in pay_frequency:
        return current_gross
    else:
        # Default to bi-weekly if unknown
        return current_gross * 2.17

def display_total_monthly_income(results: Dict[str, Dict[str, Any]]):
    """
    Display total monthly qualifying income for all sources
    
    Args:
        results: Dictionary mapping file names to parsed paystub data
    """
    st.subheader("💰 Total Monthly Qualifying Income")
    
    # Calculate monthly income for each source
    income_sources = []
    total_monthly_income = 0
    
    for file_name, result in results.items():
        if not result.get('error'):
            employee = result.get('employee', {})
            employer = result.get('employer', {})
            monthly_income = calculate_monthly_qualifying_income(result)
            
            if monthly_income > 0:
                income_sources.append({
                    'Source': f"{employee.get('name', 'Unknown')} - {employer.get('company_name', 'Unknown Company')}",
                    'Type': 'Paystubs',
                    'Monthly Income': f"${monthly_income:,.2f}",
                    'File': file_name
                })
                total_monthly_income += monthly_income
    
    # Display income sources
    if income_sources:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Income Sources:**")
            for source in income_sources:
                st.write(f"• {source['Source']}: {source['Monthly Income']}")
        
        with col2:
            st.markdown("**Total Monthly Income:**")
            st.metric(
                label="Qualifying Income",
                value=f"${total_monthly_income:,.2f}",
                help="Sum of all monthly qualifying income sources"
            )
    else:
        st.info("No qualifying income sources found")

def display_multiple_files_summary(results: Dict[str, Dict[str, Any]]):
    """
    Display summary of all uploaded files
    
    Args:
        results: Dictionary mapping file names to parsed paystub data
    """
    st.subheader("📊 Files Summary")
    
    # Create summary data
    summary_data = []
    total_files = len(results)
    successful_parses = 0
    total_gross_pay = 0
    total_net_pay = 0
    
    for file_name, result in results.items():
        if result.get('error'):
            status = "❌ Error"
            confidence = 0
            gross_pay = 0
            net_pay = 0
        else:
            status = "✅ Success"
            confidence = result.get('extraction_confidence', 0) or 0
            gross_pay = float(result.get('gross_pay_current', 0) or 0)
            net_pay = float(result.get('net_pay_current', 0) or 0)
            successful_parses += 1
            total_gross_pay += gross_pay
            total_net_pay += net_pay
        
        employee_name = result.get('employee', {}).get('name', 'N/A') if not result.get('error') else 'N/A'
        employer_name = result.get('employer', {}).get('company_name', 'N/A') if not result.get('error') else 'N/A'
        
        summary_data.append({
            'File Name': file_name,
            'Status': status,
            'Employee': employee_name,
            'Employer': employer_name,
            'Gross Pay': f"${gross_pay:,.2f}",
            'Net Pay': f"${net_pay:,.2f}",
            'Confidence': f"{confidence:.1%}"
        })
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", total_files)
    
    with col2:
        st.metric("Successful Parses", f"{successful_parses}/{total_files}")
    
    with col3:
        st.metric("Total Gross Pay", f"${total_gross_pay:,.2f}")
    
    with col4:
        st.metric("Total Net Pay", f"${total_net_pay:,.2f}")
    
    # Display summary table
    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)

def display_document_details(doc: Dict[str, Any], file_name: str, index: int):
    """
    Display detailed information for a single paystub document in a collapsible section
    
    Args:
        doc: Paystub document data
        file_name: Name of the file
        index: Document index
    """
    # Determine status text
    if doc.get('error'):
        status_text = "Error"
    else:
        confidence = doc.get('extraction_confidence', 0) or 0
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
        
        # Basic Information
        display_basic_info(doc)
        st.markdown("---")
        
        # Payroll period
        display_payroll_period(doc)
        st.markdown("---")
        
        # Financial summary
        display_financial_summary(doc)
        st.markdown("---")
        
        # Earnings breakdown
        display_earnings_breakdown(doc)
        st.markdown("---")
        
        # Deductions breakdown
        display_deductions_breakdown(doc)
        st.markdown("---")
        
        # Taxes breakdown
        display_taxes_breakdown(doc)
        st.markdown("---")
        
        # Validation warnings
        display_validation_warnings(doc)
        
        # Visualizations
        chart_key = f"{index}_{file_name.replace('.', '_').replace(' ', '_')}"
        create_earnings_visualization(doc, chart_key)
        create_deductions_visualization(doc, chart_key)
        st.markdown("---")
        
        # Export options for individual file
        # Create unique key from file name and index
        file_key = f"{index}_{file_name.replace('.', '_').replace(' ', '_')}"
        export_results(doc, file_key)

def export_multiple_results(results: Dict[str, Dict[str, Any]]):
    """
    Provide export options for multiple parsed results
    
    Args:
        results: Dictionary mapping file names to parsed paystub data
    """
    st.subheader("Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Combined JSON export
        json_data = json.dumps(results, indent=2, default=str)
        st.download_button(
            label="Download All as JSON",
            data=json_data,
            file_name=f"paystubs_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="multiple_json_download"
        )
    
    with col2:
        # Summary CSV export for all files
        summary_data = []
        
        for file_name, result in results.items():
            if not result.get('error'):
                employee = result.get('employee', {})
                employer = result.get('employer', {})
                
                summary_data.append({
                    'File Name': file_name,
                    'Employee Name': employee.get('name', 'N/A'),
                    'Employer Name': employer.get('company_name', 'N/A'),
                    'Pay Period Start': result.get('payroll_period', {}).get('start_date', 'N/A'),
                    'Pay Period End': result.get('payroll_period', {}).get('end_date', 'N/A'),
                    'Gross Pay Current': f"${float(result.get('gross_pay_current', 0) or 0):,.2f}",
                    'Net Pay Current': f"${float(result.get('net_pay_current', 0) or 0):,.2f}",
                    'Gross Pay YTD': f"${float(result.get('gross_pay_ytd', 0) or 0):,.2f}",
                    'Total Deductions': f"${sum(float(d.get('current_amount', 0) or 0) for d in result.get('deductions', [])):,.2f}",
                    'Total Taxes': f"${sum(float(t.get('current_amount', 0) or 0) for t in result.get('taxes', [])):,.2f}",
                    'Confidence Score': f"{(result.get('extraction_confidence', 0) or 0):.2%}"
                })
            else:
                summary_data.append({
                    'File Name': file_name,
                    'Employee Name': 'ERROR',
                    'Employer Name': 'ERROR',
                    'Pay Period Start': 'ERROR',
                    'Pay Period End': 'ERROR',
                    'Gross Pay Current': 'ERROR',
                    'Net Pay Current': 'ERROR',
                    'Gross Pay YTD': 'ERROR',
                    'Total Deductions': 'ERROR',
                    'Total Taxes': 'ERROR',
                    'Confidence Score': '0.0%'
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            csv_data = summary_df.to_csv(index=False)
            
            st.download_button(
                label="Download Summary as CSV",
                data=csv_data,
                file_name=f"paystubs_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="multiple_csv_download"
            )

def export_results(result: Dict[str, Any], file_key: str = ""):
    """
    Provide export options for the parsed results
    
    Args:
        result: Parsed paystub data
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
            file_name=f"paystub_parsed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=f"json_download_{file_key}"
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
            label="Download Summary as CSV",
            data=csv_data,
            file_name=f"paystub_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key=f"csv_download_{file_key}"
        )

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">💰 Interactive Paystub Parser Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Upload paystub PDFs, parse them in real-time, and drill down into detailed results**")
    
    # API Key check
    if not os.getenv('OPENAI_API_KEY'):
        st.error("OpenAI API key is required for GPT-4 Vision analysis. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Upload section
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 📁 Upload Paystub PDFs")
    
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
            "Choose a paystub PDF file",
            type=['pdf'],
            help="Upload a paystub PDF file to parse and analyze"
        )
        if uploaded_files:
            uploaded_files = [uploaded_files]  # Convert to list for consistency
    else:
        uploaded_files = st.file_uploader(
            "Choose paystub PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload multiple paystub PDF files to parse and analyze"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_files is not None and len(uploaded_files) > 0:
        # Display file info
        if len(uploaded_files) == 1:
            st.info(f"📄 **File:** {uploaded_files[0].name} ({uploaded_files[0].size:,} bytes)")
        else:
            file_info = []
            total_size = 0
            for file in uploaded_files:
                file_info.append(f"{file.name} ({file.size:,} bytes)")
                total_size += file.size
            st.info(f"📄 **Files:** {len(uploaded_files)} files selected (Total: {total_size:,} bytes)")
            for info in file_info:
                st.write(f"  • {info}")
        
        # Parse button
        button_text = f"🚀 Parse {'Paystub Document' if len(uploaded_files) == 1 else f'{len(uploaded_files)} Paystub Documents'}"
        if st.button(button_text, type="primary"):
            if len(uploaded_files) == 1:
                # Single file processing
                with st.spinner("Parsing paystub document... This may take 15-45 seconds."):
                    result = parse_uploaded_paystub(uploaded_files[0])
                    results = {uploaded_files[0].name: result}
            else:
                # Multiple files processing
                with st.spinner(f"Parsing {len(uploaded_files)} paystub documents... This may take several minutes."):
                    results = parse_multiple_paystubs(uploaded_files)
            
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
                    chart_key = f"single_{file_name.replace('.', '_').replace(' ', '_')}"
                    create_earnings_visualization(result, chart_key)
                    create_deductions_visualization(result, chart_key)
                    
                    # Export options
                    file_key = f"single_{file_name.replace('.', '_').replace(' ', '_')}"
                    export_results(result, file_key)
            else:
                # Multiple files display
                st.markdown(f"## 📋 Parsed Results: {len(results)} Files")
                
                # Display total monthly qualifying income at the top
                display_total_monthly_income(results)
                
                # Display files summary
                display_multiple_files_summary(results)
                
                # Detailed document view with collapsible sections
                st.markdown("---")
                st.markdown("### 📄 Detailed Document Review")
                
                for index, (file_name, result) in enumerate(results.items()):
                    display_document_details(result, file_name, index)
                
                # Export options for multiple files
                st.markdown("---")
                export_multiple_results(results)
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ## 🚀 How to Use This Dashboard
        
        1. **Choose upload mode**: Single file or multiple files
        2. **Upload paystub PDF(s)** using the file uploader above
        3. **Click "Parse Paystub Document(s)"** to process the file(s)
        4. **Review the results** in the detailed breakdown below
        5. **Export the data** in JSON or CSV format
        
        ### 📁 Multiple File Upload Features
        
        - **Batch Processing**: Upload and parse multiple paystubs at once
        - **Summary View**: See overview of all uploaded files with status indicators
        - **Individual Details**: Select any file to view detailed breakdown
        - **Bulk Export**: Download all results as combined JSON or summary CSV
        - **Progress Tracking**: Monitor parsing progress for multiple files
        
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
        
        - **Single file**: 15-45 seconds per document
        - **Multiple files**: 15-45 seconds per document (processed sequentially)
        - **Factors affecting speed**: PDF complexity, image quality, API response time
        - **Confidence score**: Higher scores indicate more reliable extraction
        
        ### 🔍 Validation Features
        
        - **Mathematical Consistency**: Checks earnings vs gross pay alignment
        - **Data Quality**: Validates reasonable pay rates and amounts
        - **Structure Validation**: Ensures proper paystub format recognition
        - **Warning System**: Flags potential issues for manual review
        - **Error Handling**: Graceful handling of parsing failures in batch mode
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Interactive Paystub Parser Dashboard** | "
        f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

if __name__ == "__main__":
    main()
