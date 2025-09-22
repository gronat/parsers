"""
W-2 Document Review Dashboard for Loan Officers

A comprehensive Streamlit dashboard for reviewing parsed W-2 documents
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
    page_title="W-2 Income Review Dashboard",
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

def load_w2_results(results_dir: str = "data/w2/results") -> List[Dict[str, Any]]:
    """
    Load all W-2 JSON results from the results directory
    
    Args:
        results_dir: Path to the results directory
        
    Returns:
        List of parsed W-2 documents
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        st.error(f"Results directory not found: {results_dir}")
        return []
    
    w2_documents = []
    json_files = list(results_path.glob("*.json"))
    
    if not json_files:
        st.warning("No W-2 results found in the results directory.")
        return []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['source_file'] = json_file.name
                w2_documents.append(data)
        except Exception as e:
            st.error(f"Error loading {json_file.name}: {str(e)}")
    
    return w2_documents

def calculate_summary_metrics(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary metrics for all W-2 documents
    
    Args:
        documents: List of W-2 documents
        
    Returns:
        Dictionary of summary metrics
    """
    if not documents:
        return {}
    
    total_documents = len(documents)
    total_annual_income = 0
    total_monthly_income = 0
    confidence_scores = []
    tax_years = set()
    employers = set()
    
    for doc in documents:
        calculated_income = doc.get('calculated_income', {})
        if calculated_income:
            total_annual_income += calculated_income.get('annual_income', 0) or 0
            total_monthly_income += calculated_income.get('monthly_income', 0) or 0
        
        confidence_scores.append(doc.get('confidence_score', 0) or 0)
        tax_years.add(doc.get('tax_year', 'Unknown'))
        
        employer = doc.get('employer', {})
        if employer and employer.get('name'):
            employers.add(employer['name'])
    
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    return {
        'total_documents': total_documents,
        'total_annual_income': total_annual_income,
        'total_monthly_income': total_monthly_income,
        'average_confidence': avg_confidence,
        'tax_years': list(tax_years),
        'unique_employers': len(employers),
        'employers': list(employers)
    }

def create_income_chart(documents: List[Dict[str, Any]]) -> go.Figure:
    """
    Create an income comparison chart
    
    Args:
        documents: List of W-2 documents
        
    Returns:
        Plotly figure
    """
    if not documents:
        return go.Figure()
    
    # Prepare data for chart
    chart_data = []
    for doc in documents:
        employee = doc.get('employee', {})
        calculated_income = doc.get('calculated_income', {})
        tax_year = doc.get('tax_year', 'Unknown')
        
        if calculated_income and employee.get('name'):
            chart_data.append({
                'Employee': employee['name'],
                'Annual Income': calculated_income.get('annual_income', 0) or 0,
                'Monthly Income': calculated_income.get('monthly_income', 0) or 0,
                'Tax Year': tax_year,
                'Confidence': doc.get('confidence_score', 0) or 0
            })
    
    if not chart_data:
        return go.Figure()
    
    df = pd.DataFrame(chart_data)
    
    # Create bar chart
    fig = px.bar(
        df, 
        x='Employee', 
        y='Annual Income',
        color='Tax Year',
        title='Annual Income by Employee',
        labels={'Annual Income': 'Annual Income ($)', 'Employee': 'Employee Name'},
        hover_data=['Monthly Income', 'Confidence']
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
        documents: List of W-2 documents
        
    Returns:
        Plotly figure
    """
    if not documents:
        return go.Figure()
    
    confidence_scores = [doc.get('confidence_score', 0) or 0 for doc in documents]
    
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
    Display detailed information for a single W-2 document
    
    Args:
        doc: W-2 document data
        index: Document index
    """
    with st.expander(f"📄 Document {index + 1}: {doc.get('source_file', 'Unknown')}", expanded=False):
        
        # Basic Information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Employee Information")
            employee = doc.get('employee', {})
            st.write(f"**Name:** {employee.get('name', 'N/A')}")
            st.write(f"**SSN:** {employee.get('ssn', 'N/A')}")
            
            address = employee.get('address', {})
            if address:
                st.write(f"**Address:** {address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}")
        
        with col2:
            st.subheader("🏢 Employer Information")
            employer = doc.get('employer', {})
            st.write(f"**Company:** {employer.get('name', 'N/A')}")
            st.write(f"**EIN:** {employer.get('ein', 'N/A')}")
            st.write(f"**Control Number:** {employer.get('control_number', 'N/A')}")
            
            emp_address = employer.get('address', {})
            if emp_address:
                st.write(f"**Address:** {emp_address.get('street', '')}, {emp_address.get('city', '')}, {emp_address.get('state', '')} {emp_address.get('zip', '')}")
        
        # Income Information
        st.subheader("💰 Income & Tax Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Primary Income (Box 1-6)**")
            income_info = doc.get('income_tax_info', {})
            st.write(f"Wages, Tips: ${income_info.get('wages_tips_compensation', 0):,.2f}")
            st.write(f"Federal Tax: ${income_info.get('federal_income_tax_withheld', 0):,.2f}")
            st.write(f"SS Wages: ${income_info.get('social_security_wages', 0):,.2f}")
            st.write(f"SS Tax: ${income_info.get('social_security_tax_withheld', 0):,.2f}")
            st.write(f"Medicare Wages: ${income_info.get('medicare_wages_tips', 0):,.2f}")
            st.write(f"Medicare Tax: ${income_info.get('medicare_tax_withheld', 0):,.2f}")
        
        with col2:
            st.markdown("**Calculated Income for Mortgage**")
            calculated_income = doc.get('calculated_income', {})
            if calculated_income:
                st.markdown(f'<div class="income-highlight">', unsafe_allow_html=True)
                st.write(f"**Annual Income:** ${calculated_income.get('annual_income', 0):,.2f}")
                st.write(f"**Monthly Income:** ${calculated_income.get('monthly_income', 0):,.2f}")
                st.write(f"**Method:** {calculated_income.get('income_verification_method', 'N/A')}")
                if calculated_income.get('additional_benefits'):
                    st.write(f"**Additional Benefits:** ${calculated_income.get('additional_benefits', 0):,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown("**Box 12 Codes**")
            box_12_codes = income_info.get('box_12_codes', [])
            if box_12_codes:
                for code_info in box_12_codes:
                    if isinstance(code_info, dict):
                        st.write(f"Code {code_info.get('code', 'N/A')}: ${code_info.get('amount', 0):,.2f}")
            else:
                st.write("No Box 12 codes")
            
            st.markdown("**Flags**")
            st.write(f"Retirement Plan: {'✅' if income_info.get('retirement_plan') else '❌'}")
            st.write(f"Statutory Employee: {'✅' if income_info.get('statutory_employee') else '❌'}")
            st.write(f"Third-party Sick Pay: {'✅' if income_info.get('third_party_sick_pay') else '❌'}")
        
        # State/Local Information
        state_local = doc.get('state_local_info', [])
        if state_local:
            st.subheader("🏛️ State & Local Tax Information")
            for state_info in state_local:
                st.write(f"**State:** {state_info.get('state', 'N/A')}")
                st.write(f"State Wages: ${state_info.get('state_wages', 0):,.2f}")
                st.write(f"State Tax: ${state_info.get('state_income_tax', 0):,.2f}")
                if state_info.get('locality'):
                    st.write(f"Locality: {state_info.get('locality')}")
                    st.write(f"Local Wages: ${state_info.get('local_wages', 0):,.2f}")
                    st.write(f"Local Tax: ${state_info.get('local_income_tax', 0):,.2f}")
        
        # Processing Metadata
        metadata = doc.get('processing_metadata', {})
        if metadata:
            st.subheader("🔧 Processing Information")
            col1, col2 = st.columns(2)
            with col1:
                confidence = doc.get('confidence_score', 0) or 0
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

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 W-2 Income Review Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Comprehensive W-2 document analysis for mortgage loan officers**")
    
    # Confidence Score Explanation
    with st.expander("ℹ️ How Confidence Scores Are Calculated", expanded=False):
        st.markdown("""
        ### Confidence Score Calculation Methodology
        
        The confidence score represents the reliability and accuracy of the W-2 data extraction process. It's calculated using a hybrid approach combining multiple validation methods:
        
        #### **1. Camelot Table Extraction Quality (40%)**
        - **Table Detection Accuracy**: How well Camelot identified and extracted tables from the PDF
        - **Data Completeness**: Percentage of expected W-2 fields successfully extracted
        - **Table Structure Quality**: Assessment of table formatting and readability
        
        #### **2. GPT-4 Vision Validation (35%)**
        - **Visual Field Recognition**: GPT-4 Vision's ability to identify and read W-2 fields from the PDF image
        - **Cross-Validation**: Comparison between Camelot extraction and visual analysis
        - **Field Accuracy**: Verification of extracted values against visual confirmation
        
        #### **3. Data Consistency Checks (15%)**
        - **Mathematical Validation**: Ensuring tax calculations are consistent (e.g., SS tax = SS wages × 6.2%)
        - **Field Relationships**: Validating that related fields make logical sense
        - **Format Compliance**: Checking that extracted data follows expected W-2 formats
        
        #### **4. Pydantic Model Validation (10%)**
        - **Data Type Validation**: Ensuring all fields have correct data types
        - **Required Field Presence**: Checking that critical fields are not missing
        - **Schema Compliance**: Validating against the defined W-2 data structure
        
        #### **Confidence Score Ranges**
        - **95-100%**: Excellent extraction with high visual and mathematical validation
        - **90-94%**: Very good extraction with minor inconsistencies
        - **85-89%**: Good extraction with some missing or uncertain fields
        - **80-84%**: Acceptable extraction but may require manual review
        - **Below 80%**: Poor extraction quality, manual review recommended
        
        #### **Factors That Lower Confidence**
        - Poor PDF quality or scanned images
        - Non-standard W-2 formats
        - Missing or unclear field values
        - Inconsistent tax calculations
        - GPT-4 Vision unable to validate Camelot extraction
        
        #### **Factors That Increase Confidence**
        - Clear, high-quality PDF documents
        - Standard IRS W-2 format
        - Complete field extraction
        - Consistent mathematical relationships
        - Strong agreement between Camelot and GPT-4 Vision
        """)
    
    # Load data
    with st.spinner("Loading W-2 results..."):
        documents = load_w2_results()
    
    if not documents:
        st.error("No W-2 documents found. Please run the parser first to generate results.")
        return
    
    # Calculate summary metrics
    metrics = calculate_summary_metrics(documents)
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Tax year filter
    tax_years = metrics.get('tax_years', [])
    if tax_years:
        selected_years = st.sidebar.multiselect(
            "Tax Years",
            options=tax_years,
            default=tax_years
        )
        # Filter documents by selected years
        documents = [doc for doc in documents if doc.get('tax_year') in selected_years]
    
    # Confidence filter
    min_confidence = st.sidebar.slider(
        "Minimum Confidence Score",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.05,
        format="%.2f"
    )
    documents = [doc for doc in documents if (doc.get('confidence_score', 0) or 0) >= min_confidence]
    
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
        total_annual = sum(doc.get('calculated_income', {}).get('annual_income', 0) or 0 for doc in documents)
        st.metric(
            label="Total Annual Income",
            value=f"${total_annual:,.0f}",
            delta=f"${total_annual - metrics['total_annual_income']:,.0f}" if total_annual != metrics['total_annual_income'] else None
        )
    
    with col3:
        total_monthly = sum(doc.get('calculated_income', {}).get('monthly_income', 0) or 0 for doc in documents)
        st.metric(
            label="Total Monthly Income",
            value=f"${total_monthly:,.0f}",
            delta=f"${total_monthly - metrics['total_monthly_income']:,.0f}" if total_monthly != metrics['total_monthly_income'] else None
        )
    
    with col4:
        avg_confidence = sum(doc.get('confidence_score', 0) or 0 for doc in documents) / len(documents) if documents else 0
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
        
        confidence_scores = [doc.get('confidence_score', 0) or 0 for doc in documents]
        
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
        calculated_income = doc.get('calculated_income', {})
        
        table_data.append({
            'Document': i + 1,
            'Employee': employee.get('name', 'N/A'),
            'Employer': doc.get('employer', {}).get('name', 'N/A'),
            'Tax Year': doc.get('tax_year', 'N/A'),
            'Annual Income': calculated_income.get('annual_income', 0) or 0,
            'Monthly Income': calculated_income.get('monthly_income', 0) or 0,
            'Confidence': f"{(doc.get('confidence_score', 0) or 0):.1%}",
            'Source File': doc.get('source_file', 'N/A')
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        
        # Format currency columns
        df['Annual Income'] = df['Annual Income'].apply(lambda x: f"${x:,.2f}")
        df['Monthly Income'] = df['Monthly Income'].apply(lambda x: f"${x:,.2f}")
        
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
            file_name=f"w2_income_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
        "**W-2 Income Review Dashboard** | "
        f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Total Documents Processed: {len(documents)}"
    )

if __name__ == "__main__":
    main()
