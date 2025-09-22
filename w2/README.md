# W-2 Parser Module

A comprehensive W-2 document parser for mortgage verification services that extracts structured data from W-2 tax forms using multi-modal processing.

## 📁 Module Structure

```
w2/
├── __init__.py              # Module initialization and exports
├── w2_parser.py             # Main W-2 parser implementation
├── w2_dashboard.py          # Streamlit dashboard for W-2 review
├── w2_interactive_dashboard.py  # Interactive upload & parse dashboard
└── README.md               # This documentation file
```

## 🚀 Features

### Multi-Modal Processing Pipeline

- **Primary**: Camelot table extraction for structured data
- **Enhancement**: GPT-4 Vision for validation and field recognition
- **Enhancement**: GPT-4 Vision API for image-based analysis
- **Validation**: Data completeness scoring and processing quality assessment

### Data Extraction Capabilities

- **Employee Information**: Name, SSN (masked), address
- **Employer Information**: Company name, EIN, address, control number
- **Income Data**: Wages, tips, compensation (Box 1-6)
- **Tax Information**: Federal, state, local tax withholdings
- **Box 12 Codes**: All benefit codes and amounts
- **State/Local Info**: State wages, taxes, and locality information

## 📋 Data Models

### Core Pydantic Models

```python
class W2Document(BaseModel):
    document_type: str = "W-2"
    tax_year: Optional[str] = None
    employee: Optional[EmployeeInfo] = None
    employer: Optional[EmployerInfo] = None
    income_tax_info: Optional[IncomeTaxInfo] = None
    state_local_info: List[StateLocalInfo] = Field(default_factory=list)
    calculated_income: Optional[CalculatedIncome] = None
    confidence_score: Optional[float] = None
    processing_metadata: Optional[Dict[str, Any]] = None
```

## 🛠️ Usage

### Basic Usage

```python
from app.ai.parser.w2 import W2Parser

# Initialize parser
parser = W2Parser()

# Parse a W-2 PDF
result = parser.parse_pdf("path/to/w2.pdf")

# Access extracted data
employee_name = result['employee']['name']
wages = result['income_tax_info']['wages_tips_compensation']
confidence = result['confidence_score']
```

### Command Line Usage

```bash
# Parse a single W-2
python app/ai/parser/w2/w2_parser.py "data/w2/sample.pdf"

# Run dashboard
streamlit run app/ai/parser/w2/w2_dashboard.py
```

### Dashboard Usage

#### Static Dashboard (Review Existing Results)

```bash
# Launch the W-2 review dashboard for existing results
streamlit run app/ai/parser/w2/w2_dashboard.py
```

The static dashboard provides:

- Summary metrics and charts
- Document-by-document review
- Confidence score analysis
- Data export capabilities
- Filtering and search functionality

#### Interactive Dashboard (Upload & Parse)

```bash
# Launch the interactive W-2 parser dashboard
streamlit run app/ai/parser/w2/w2_interactive_dashboard.py
```

The interactive dashboard provides:

- **PDF Upload**: Upload W-2 PDFs directly in the browser
- **Real-time Parsing**: Parse documents with live progress updates
- **Drill-down Analysis**: Detailed breakdown of parsed results
- **Visual Validation**: Charts and graphs for data verification
- **Export Options**: Download results as JSON or CSV
- **Confidence Scoring**: Real-time quality assessment

## 📊 Output Structure

### Example Output

```json
{
  "document_type": "W-2",
  "tax_year": "2024",
  "employee": {
    "ssn": "XXX-XX-1234",
    "name": "John Doe",
    "address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "CA",
      "zip": "12345"
    }
  },
  "employer": {
    "ein": "12-3456789",
    "name": "Example Company Inc",
    "address": {
      "street": "456 Business Ave",
      "city": "Business City",
      "state": "CA",
      "zip": "54321"
    },
    "control_number": "123456789"
  },
  "income_tax_info": {
    "wages_tips_compensation": 75000.0,
    "federal_income_tax_withheld": 12000.0,
    "social_security_wages": 75000.0,
    "social_security_tax_withheld": 4650.0,
    "medicare_wages_tips": 75000.0,
    "medicare_tax_withheld": 1087.5,
    "box_12_codes": [{ "code": "D", "amount": 5000.0 }]
  },
  "calculated_income": {
    "annual_income": 75000.0,
    "monthly_income": 6250.0,
    "income_verification_method": "box_1_wages"
  },
  "confidence_score": 0.95
}
```

## 🎯 Confidence Scoring

The parser provides confidence scores based on:

### Scoring Factors (100 points total)

- **Basic Information (30 points)**

  - Employee name: 10 points
  - Employer name: 10 points
  - Tax year: 10 points

- **Financial Data (40 points)**

  - Box 1 wages: 15 points
  - Federal tax withheld: 15 points
  - Box 12 codes: 10 points

- **Detailed Breakdowns (20 points)**

  - State/local info: 10 points
  - Complete address info: 10 points

- **Processing Quality (10 points)**
  - GPT Vision used: 5 points
  - Tables found: 3 points
  - Text extraction: 2 points

## ⚠️ Validation & Quality Control

### Automatic Validation

- **Mathematical Consistency**: Tax calculations are verified
- **Field Completeness**: Critical fields are present
- **Format Compliance**: Data follows W-2 standards
- **Cross-Validation**: Multiple extraction methods agree

### Validation Warnings

- Missing critical financial data
- Inconsistent tax calculations
- Unusual amounts or patterns
- Format compliance issues

## 🔧 Processing Methods

### Multi-Modal Approach

1. **Camelot Table Extraction** (Primary)

   - Extracts structured tables from PDFs
   - High accuracy for well-formatted W-2s
   - Handles complex table layouts

2. **GPT-4 Vision Analysis** (Enhancement)

   - Extracts raw text from PDFs
   - Handles unstructured documents
   - Uses regex patterns for field identification

3. **GPT-4 Vision Analysis** (Enhancement)
   - Analyzes PDF images for visual confirmation
   - Cross-validates extracted data
   - Handles scanned documents and unusual formats

## 📈 Performance Metrics

### Processing Targets

- **Success Rate**: 95%+ of standard W-2 formats
- **Processing Time**: <30 seconds per W-2 (including AI calls)
- **Accuracy**: 99%+ on critical financial fields
- **Confidence**: 90%+ average confidence score

## 🧪 Testing

### Test Suite

```bash
# Test with sample W-2 files
python app/ai/parser/w2/w2_parser.py "data/w2/sample.pdf"

# Run dashboard for visual testing
streamlit run app/ai/parser/w2/w2_dashboard.py
```

## 🔒 Security & Compliance

### Data Protection

- **SSN Masking**: Automatically masks SSN data
- **Secure Processing**: No data persistence in logs
- **Audit Trail**: Comprehensive processing metadata
- **GDPR Compliance**: Handles sensitive data appropriately

## 🚀 Integration

### API Integration

```python
from app.ai.parser.w2 import W2Parser

def process_w2(pdf_path: str) -> dict:
    parser = W2Parser()
    result = parser.parse_pdf(pdf_path)

    # Validate confidence threshold
    if result['confidence_score'] < 0.85:
        raise ValueError("Low confidence extraction - manual review required")

    return result
```

### Database Integration

```python
# Save results to database
def save_w2_data(result: dict, loan_id: str):
    w2_record = {
        'loan_id': loan_id,
        'employee_name': result['employee']['name'],
        'annual_income': result['calculated_income']['annual_income'],
        'confidence_score': result['confidence_score'],
        'raw_data': result
    }
    # Save to database...
```

## 📝 Logging & Monitoring

### Log Levels

- **INFO**: Normal processing flow
- **WARNING**: Fallback methods used
- **ERROR**: Processing failures
- **DEBUG**: Detailed extraction steps

## 🔄 Maintenance & Updates

### Regular Maintenance

- Update field patterns for new W-2 formats
- Monitor GPT Vision API costs and usage
- Review confidence score thresholds
- Update validation rules based on edge cases

---

**Version**: 1.0.0  
**Last Updated**: September 2025  
**Maintainer**: Future Mortgage Verification Service Team
