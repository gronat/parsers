"""
Paystub Document Review Dashboard for Loan Officers

A comprehensive Streamlit dashboard for reviewing parsed paystub documents
and analyzing income data for mortgage approval decisions.
"""

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Any
import datetime

# Page configuration
st.set_page_config(
    page_title="Paystub Income Review Dashboard",
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
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

def load_paystub_results(results_dir: str = "data/paystubs/results") -> List[Dict[str, Any]]:
    """
    Load all paystub JSON results from the results directory
    
    Args:
        results_dir: Path to the results directory
        
    Returns:
        List of parsed paystub documents
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        st.error(f"Results directory not found: {results_dir}")
        return []
    
    paystub_documents = []
    json_files = list(results_path.glob("*.json"))
    
    if not json_files:
        st.warning("No paystub results found in the results directory.")
        return []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['source_file'] = json_file.name
                paystub_documents.append(data)
        except Exception as e:
            st.error(f"Error loading {json_file.name}: {str(e)}")
    
    return paystub_documents

def calculate_summary_metrics(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary metrics for all paystub documents
    
    Args:
        documents: List of paystub documents
        
    Returns:
        Dictionary of summary metrics
    """
    if not documents:
        return {}
    
    total_documents = len(documents)
    total_gross_income = 0
    total_net_income = 0
    confidence_scores = []
    companies = set()
    employees = set()
    
    for doc in documents:
        gross_pay = doc.get('gross_pay_current', 0) or 0
        net_pay = doc.get('net_pay_current', 0) or 0
        
        if gross_pay:
            total_gross_income += float(gross_pay)
        if net_pay:
            total_net_income += float(net_pay)
        
        confidence_scores.append(doc.get('extraction_confidence', 0) or 0)
        
        employer = doc.get('employer', {})
        if employer and employer.get('company_name'):
            companies.add(employer['company_name'])
        
        employee = doc.get('employee', {})
        if employee and employee.get('name'):
            employees.add(employee['name'])
    
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    return {
        'total_documents': total_documents,
        'total_gross_income': total_gross_income,
        'total_net_income': total_net_income,
        'average_confidence': avg_confidence,
        'unique_companies': len(companies),
        'unique_employees': len(employees),
        'companies': list(companies),
        'employees': list(employees)
    }

def create_income_chart(documents: List[Dict[str, Any]]) -> go.Figure:
    """
    Create an income comparison chart
    
    Args:
        documents: List of paystub documents
        
    Returns:
        Plotly figure
    """
    if not documents:
        return go.Figure()
    
    # Prepare data for chart
    chart_data = []
    for doc in documents:
        employee = doc.get('employee', {})
        employer = doc.get('employer', {})
        gross_pay = float(doc.get('gross_pay_current', 0) or 0)
        net_pay = float(doc.get('net_pay_current', 0) or 0)
        confidence = doc.get('extraction_confidence', 0) or 0
        
        if gross_pay > 0 and employee.get('name'):
            chart_data.append({
                'Employee': employee['name'],
                'Company': employer.get('company_name', 'Unknown'),
                'Gross Pay': gross_pay,
                'Net Pay': net_pay,
                'Confidence': confidence
            })
    
    if not chart_data:
        return go.Figure()
    
    df = pd.DataFrame(chart_data)
    
    # Create bar chart
    fig = px.bar(
        df, 
        x='Employee', 
        y='Gross Pay',
        color='Company',
        title='Gross Pay by Employee',
        labels={'Gross Pay': 'Gross Pay ($)', 'Employee': 'Employee Name'},
        hover_data=['Net Pay', 'Confidence']
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=True
    )
    
    return fig

def create_confidence_chart(documents: List[Dict[str, Any]]) -> go.Figure:
    """
    Create a confidence score distribution chart with quality indicators
    
    Args:
        documents: List of paystub documents
        
    Returns:
        Plotly figure
    """
    if not documents:
        return go.Figure()
    
    confidence_scores = [doc.get('extraction_confidence', 0) or 0 for doc in documents]
    
    # Create histogram with color coding based on confidence ranges
    colors = []
    for score in confidence_scores:
        if score >= 0.95:
            colors.append('#28a745')  # Green - Excellent
        elif score >= 0.90:
            colors.append('#ffc107')  # Yellow - Very Good
        elif score >= 0.85:
            colors.append('#fd7e14')  # Orange - Good
        else:
            colors.append('#dc3545')  # Red - Poor
    
    fig = go.Figure(data=[
        go.Histogram(
            x=confidence_scores,
            nbinsx=10,
            marker_color=colors,
            opacity=0.7,
            hovertemplate='<b>Confidence Range:</b> %{x:.2%}<br>' +
                         '<b>Count:</b> %{y}<br>' +
                         '<extra></extra>'
        )
    ])
    
    # Add vertical lines for confidence thresholds
    fig.add_vline(x=0.95, line_dash="dash", line_color="green", 
                  annotation_text="Excellent (95%+)", annotation_position="top")
    fig.add_vline(x=0.90, line_dash="dash", line_color="orange", 
                  annotation_text="Very Good (90%+)", annotation_position="top")
    fig.add_vline(x=0.85, line_dash="dash", line_color="red", 
                  annotation_text="Good (85%+)", annotation_position="top")
    
    fig.update_layout(
        title='Confidence Score Distribution with Quality Indicators',
        xaxis_title='Confidence Score',
        yaxis_title='Number of Documents',
        height=400,
        xaxis=dict(tickformat='.0%')
    )
    
    return fig

def display_document_details(doc: Dict[str, Any], index: int):
    """
    Display detailed information for a single paystub document
    
    Args:
        doc: Paystub document data
        index: Document index
    """
    with st.expander(f"💰 Document {index + 1}: {doc.get('source_file', 'Unknown')}", expanded=False):
        
        # Basic Information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Employee Information")
            employee = doc.get('employee', {})
            st.write(f"**Name:** {employee.get('name', 'N/A')}")
            st.write(f"**SSN:** {employee.get('ssn_masked', 'N/A')}")
            
            address = employee.get('address', {})
            if address:
                st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
        
        with col2:
            st.subheader("🏢 Employer Information")
            employer = doc.get('employer', {})
            st.write(f"**Company:** {employer.get('company_name', 'N/A')}")
            st.write(f"**Employee ID:** {employer.get('employee_id', 'N/A')}")
            
            emp_address = employer.get('address', {})
            if emp_address:
                st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")
        
        # Payroll Period Information
        st.subheader("📅 Payroll Period")
        payroll_period = doc.get('payroll_period', {})
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Start Date:** {payroll_period.get('start_date', 'N/A')}")
        with col2:
            st.write(f"**End Date:** {payroll_period.get('end_date', 'N/A')}")
        with col3:
            st.write(f"**Pay Date:** {payroll_period.get('pay_date', 'N/A')}")
        
        # Financial Information
        st.subheader("💰 Financial Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Current Period**")
            gross_pay = float(doc.get('gross_pay_current', 0) or 0)
            net_pay = float(doc.get('net_pay_current', 0) or 0)
            st.write(f"Gross Pay: ${gross_pay:,.2f}")
            st.write(f"Net Pay: ${net_pay:,.2f}")
        
        with col2:
            st.markdown("**Year-to-Date**")
            gross_ytd = doc.get('gross_pay_ytd')
            net_ytd = doc.get('net_pay_ytd')
            if gross_ytd:
                st.write(f"Gross YTD: ${float(gross_ytd):,.2f}")
            if net_ytd:
                st.write(f"Net YTD: ${float(net_ytd):,.2f}")
        
        with col3:
            st.markdown("**Pay Details**")
            pay_freq = doc.get('pay_frequency', 'N/A')
            total_hours = doc.get('total_hours_current')
            st.write(f"Frequency: {pay_freq}")
            if total_hours:
                st.write(f"Total Hours: {total_hours}")
        
        # Earnings Breakdown
        earnings = doc.get('earnings', [])
        if earnings:
            st.subheader("💵 Earnings Breakdown")
            earnings_df = pd.DataFrame(earnings)
            st.dataframe(earnings_df, use_container_width=True)
        
        # Deductions
        deductions = doc.get('deductions', [])
        if deductions:
            st.subheader("📉 Deductions")
            deductions_df = pd.DataFrame(deductions)
            st.dataframe(deductions_df, use_container_width=True)
        
        # Taxes
        taxes = doc.get('taxes', [])
        if taxes:
            st.subheader("🏛️ Tax Information")
            taxes_df = pd.DataFrame(taxes)
            st.dataframe(taxes_df, use_container_width=True)
        
        # Validation Warnings
        warnings = doc.get('validation_warnings', [])
        if warnings:
            st.subheader("⚠️ Validation Warnings")
            for warning in warnings:
                st.warning(f"• {warning}")
        
        # Processing Metadata
        metadata = doc.get('processing_metadata', {})
        if metadata:
            st.subheader("🔧 Processing Information")
            col1, col2 = st.columns(2)
            with col1:
                confidence = doc.get('extraction_confidence', 0) or 0
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
                st.write(f"**Text Length:** {metadata.get('pdfplumber_text_length', 'N/A')} characters")
                st.write(f"**Validation:** {'✅' if metadata.get('validation_passed') else '❌'}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">💰 Paystub Income Review Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Comprehensive paystub document analysis for mortgage loan officers**")
    
    # Confidence Score Explanation
    with st.expander("ℹ️ How Confidence Scores Are Calculated", expanded=False):
        st.markdown("""
        ### Confidence Score Calculation Methodology
        
        The confidence score represents the reliability and accuracy of the paystub data extraction process. It's calculated using a 100-point scoring system based on data completeness and processing quality:
        
        #### **1. Basic Information (30 points)**
        - **Company Name**: 10 points
        - **Employee Name**: 10 points
        - **Pay Date**: 10 points
        
        #### **2. Financial Data (40 points)**
        - **Gross Pay**: 15 points
        - **Net Pay**: 15 points
        - **Earnings Breakdown**: 10 points
        
        #### **3. Detailed Breakdowns (20 points)**
        - **Tax Information**: 10 points
        - **Deductions**: 10 points
        
        #### **4. Processing Quality (10 points)**
        - **GPT Vision Used**: 5 points
        - **Tables Found**: 3 points
        - **Text Extraction**: 2 points
        
        #### **Confidence Score Ranges**
        - **95-100%**: Excellent extraction with complete data and high-quality processing
        - **90-94%**: Very good extraction with most fields present
        - **85-89%**: Good extraction with some missing fields
        - **80-84%**: Acceptable extraction but may require manual review
        - **Below 80%**: Poor extraction quality, manual review recommended
        """)
    
    # Load data
    with st.spinner("Loading paystub results..."):
        documents = load_paystub_results()
    
    if not documents:
        st.error("No paystub documents found. Please run the parser first to generate results.")
        return
    
    # Calculate summary metrics
    metrics = calculate_summary_metrics(documents)
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Company filter
    companies = metrics.get('companies', [])
    if companies:
        selected_companies = st.sidebar.multiselect(
            "Companies",
            options=companies,
            default=companies
        )
        # Filter documents by selected companies
        documents = [doc for doc in documents if doc.get('employer', {}).get('company_name') in selected_companies]
    
    # Confidence filter
    min_confidence = st.sidebar.slider(
        "Minimum Confidence Score",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.05,
        format="%.2f"
    )
    documents = [doc for doc in documents if (doc.get('extraction_confidence', 0) or 0) >= min_confidence]
    
    # Summary metrics
    st.header("📈 Summary Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Documents",
            value=len(documents),
            delta=f"{len(documents) - metrics['total_documents']}" if len(documents) != metrics['total_documents'] else None
        )
    
    with col2:
        total_gross = sum(float(doc.get('gross_pay_current', 0) or 0) for doc in documents)
        st.metric(
            label="Total Gross Income",
            value=f"${total_gross:,.0f}",
            delta=f"${total_gross - metrics['total_gross_income']:,.0f}" if total_gross != metrics['total_gross_income'] else None
        )
    
    with col3:
        total_net = sum(float(doc.get('net_pay_current', 0) or 0) for doc in documents)
        st.metric(
            label="Total Net Income",
            value=f"${total_net:,.0f}",
            delta=f"${total_net - metrics['total_net_income']:,.0f}" if total_net != metrics['total_net_income'] else None
        )
    
    with col4:
        avg_confidence = sum(doc.get('extraction_confidence', 0) or 0 for doc in documents) / len(documents) if documents else 0
        st.metric(
            label="Average Confidence",
            value=f"{avg_confidence:.1%}",
            delta=f"{avg_confidence - metrics['average_confidence']:.1%}" if avg_confidence != metrics['average_confidence'] else None
        )
    
    # Charts
    st.header("📊 Income Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        income_chart = create_income_chart(documents)
        if income_chart.data:
            st.plotly_chart(income_chart, use_container_width=True)
        else:
            st.info("No income data available for charting")
    
    with col2:
        confidence_chart = create_confidence_chart(documents)
        if confidence_chart.data:
            st.plotly_chart(confidence_chart, use_container_width=True)
        else:
            st.info("No confidence data available for charting")
    
    # Confidence Score Summary
    if documents:
        st.header("🎯 Confidence Score Analysis")
        
        confidence_scores = [doc.get('extraction_confidence', 0) or 0 for doc in documents]
        
        # Calculate confidence categories
        excellent = sum(1 for score in confidence_scores if score >= 0.95)
        very_good = sum(1 for score in confidence_scores if 0.90 <= score < 0.95)
        good = sum(1 for score in confidence_scores if 0.85 <= score < 0.90)
        poor = sum(1 for score in confidence_scores if score < 0.85)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🟢 Excellent (95%+)",
                value=excellent,
                help="High reliability, minimal review needed"
            )
        
        with col2:
            st.metric(
                label="🟡 Very Good (90-94%)",
                value=very_good,
                help="Minor review recommended"
            )
        
        with col3:
            st.metric(
                label="🟠 Good (85-89%)",
                value=good,
                help="Some fields may need verification"
            )
        
        with col4:
            st.metric(
                label="🔴 Poor (<85%)",
                value=poor,
                help="Manual review required"
            )
        
        # Overall confidence assessment
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        if avg_confidence >= 0.95:
            st.success(f"🎉 **Overall Quality: Excellent** - Average confidence: {avg_confidence:.1%}")
        elif avg_confidence >= 0.90:
            st.info(f"✅ **Overall Quality: Very Good** - Average confidence: {avg_confidence:.1%}")
        elif avg_confidence >= 0.85:
            st.warning(f"⚠️ **Overall Quality: Good** - Average confidence: {avg_confidence:.1%}")
        else:
            st.error(f"🚨 **Overall Quality: Needs Review** - Average confidence: {avg_confidence:.1%}")
    
    # Data table
    st.header("📋 Document Summary Table")
    
    # Prepare data for table
    table_data = []
    for i, doc in enumerate(documents):
        employee = doc.get('employee', {})
        employer = doc.get('employer', {})
        gross_pay = float(doc.get('gross_pay_current', 0) or 0)
        net_pay = float(doc.get('net_pay_current', 0) or 0)
        
        table_data.append({
            'Document': i + 1,
            'Employee': employee.get('name', 'N/A'),
            'Company': employer.get('company_name', 'N/A'),
            'Gross Pay': gross_pay,
            'Net Pay': net_pay,
            'Confidence': f"{(doc.get('extraction_confidence', 0) or 0):.1%}",
            'Source File': doc.get('source_file', 'N/A')
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        
        # Format currency columns
        df['Gross Pay'] = df['Gross Pay'].apply(lambda x: f"${x:,.2f}")
        df['Net Pay'] = df['Net Pay'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Summary as CSV",
            data=csv,
            file_name=f"paystub_income_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No documents match the current filters")
    
    # Detailed document view
    st.header("📄 Detailed Document Review")
    
    if documents:
        for i, doc in enumerate(documents):
            display_document_details(doc, i)
    else:
        st.info("No documents available for detailed review")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Paystub Income Review Dashboard** | "
        f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Total Documents Processed: {len(documents)}"
    )

if __name__ == "__main__":
    main()
