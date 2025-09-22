# Paystub Interactive Dashboard

A dynamic Streamlit dashboard for uploading, parsing, and analyzing paystub PDFs in real-time.

## 🚀 Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Run the dashboard
streamlit run app/ai/parser/paystub/paystub_interactive_dashboard.py --server.port 8502
```

The dashboard will be available at: `http://localhost:8502`

## 📋 Features

### Core Functionality

- **PDF Upload**: Drag-and-drop paystub PDF upload
- **Real-time Parsing**: Instant parsing with progress indicators
- **Interactive Analysis**: Drill down into detailed results
- **Export Options**: Download results as JSON or CSV

### Data Extraction

- **Employee Information**: Name, SSN (masked), address
- **Employer Information**: Company name, employee ID, address
- **Payroll Period**: Start/end dates, pay date, frequency
- **Earnings Breakdown**: Regular pay, overtime, bonuses, commissions, holiday pay
- **Deductions**: Pre-tax and post-tax deductions with descriptions
- **Taxes**: Federal, state, local tax withholdings
- **Financial Summary**: Gross pay, net pay, YTD amounts

### Visualization & Analysis

- **Earnings Charts**: Pie charts and bar charts for earnings breakdown
- **Deductions Analysis**: Visual breakdown of all deductions
- **Validation Warnings**: Real-time validation with helpful warnings
- **Confidence Scoring**: Quality assessment of extraction accuracy

### Advanced Features

- **Employer Contribution Detection**: Automatically identifies employer-paid benefits
- **Mathematical Validation**: Checks earnings vs gross pay consistency
- **Flexible Parsing**: Handles various paystub formats and layouts
- **Error Handling**: Graceful fallbacks for complex documents

## 🎯 Confidence Scoring

The parser provides confidence scores based on:

- **Extraction Method Success**: Higher scores for successful Camelot + GPT Vision processing
- **Data Completeness**: Presence of key fields (employee name, gross pay, earnings)
- **Processing Quality**: Whether GPT-4 Vision validation was used
- **Error Handling**: Lower scores when fallback methods are needed

### Score Interpretation

- **95%+**: Excellent - High reliability
- **90-94%**: Very Good - Minor review recommended
- **85-89%**: Good - Some fields may need verification
- **<85%**: Poor - Manual review required

## ⚡ Processing Time

- **Typical processing time**: 15-45 seconds per document
- **Factors affecting speed**: PDF complexity, image quality, API response time
- **Confidence score**: Higher scores indicate more reliable extraction

## 🔍 Validation Features

- **Mathematical Consistency**: Checks earnings vs gross pay alignment
- **Data Quality**: Validates reasonable pay rates and amounts
- **Structure Validation**: Ensures proper paystub format recognition
- **Warning System**: Flags potential issues for manual review

## 📊 Dashboard Sections

### 1. Basic Information

- Employee and employer details
- Contact information and addresses

### 2. Payroll Period

- Pay period dates and frequency
- Pay date information

### 3. Financial Summary

- Key metrics in an easy-to-read format
- Gross pay, net pay, YTD amounts
- Total deductions

### 4. Earnings Breakdown

- Detailed breakdown of all earnings
- Employee vs employer contribution classification
- Individual earnings with rates and hours
- YTD amounts for each earning type

### 5. Deductions Breakdown

- Pre-tax vs post-tax deduction classification
- Individual deduction details
- YTD deduction amounts

### 6. Taxes Breakdown

- Federal, state, and local taxes
- Taxable wages information
- Effective tax rate calculation

### 7. Validation Warnings

- Real-time validation feedback
- Helpful warnings for data review
- Mathematical consistency checks

### 8. Visualizations

- Interactive charts for earnings and deductions
- Pie charts and bar charts
- Color-coded by type (employee vs employer)

### 9. Export Options

- JSON export for full data
- CSV export for summary data
- Timestamped file names

## 🛠️ Technical Requirements

- Python 3.8+
- Streamlit
- OpenAI API key (for GPT-4 Vision)
- Required dependencies from requirements.txt

## 🔧 Configuration

Set the following environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 📝 Usage Examples

### Basic Usage

1. Upload a paystub PDF using the file uploader
2. Click "Parse Paystub Document"
3. Review the parsed results
4. Export data if needed

### Advanced Analysis

1. Use the earnings breakdown to understand compensation structure
2. Check validation warnings for data quality issues
3. Use visualizations to identify patterns
4. Export data for further analysis

## 🐛 Troubleshooting

### Common Issues

- **API Key Error**: Ensure OPENAI_API_KEY is set
- **Parsing Errors**: Check PDF quality and format
- **Low Confidence**: Review validation warnings
- **Missing Data**: Verify paystub completeness

### Performance Tips

- Use high-quality PDF scans
- Ensure text is selectable in PDFs
- Avoid heavily formatted or complex layouts
- Check file size (keep under 10MB)

## 🔄 Updates

The dashboard automatically uses the latest parser improvements:

- Enhanced employer contribution detection
- Improved validation logic
- Better error handling
- Updated GPT Vision prompts

## 📞 Support

For issues or questions:

1. Check the validation warnings
2. Review the confidence score
3. Verify PDF quality
4. Check the console logs for detailed error messages

