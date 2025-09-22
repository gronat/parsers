"""
Enhanced Paystub Parser for Mortgage Verification Service

A comprehensive, production-ready paystub parser that handles diverse paystub formats
with high accuracy and reliability. Implements multi-modal PDF processing pipeline
with AI integration for mortgage approval workflows.

Architecture: PDF → Camelot/pdfplumber → GPT-4 Vision → Structured JSON
"""

import os
import json
import base64
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
import logging

# Core dependencies
import camelot
import pandas as pd
import pdfplumber
from pydantic import BaseModel, Field, validator, field_validator
from pdf2image import convert_from_path
from PIL import Image
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')


# Pydantic Models for Data Validation
class AddressModel(BaseModel):
    """Address structure for employee/employer"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    full_address: Optional[str] = None


class PayrollPeriod(BaseModel):
    """Payroll period information"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    pay_date: Optional[date] = None


class EarningsDetail(BaseModel):
    """Individual earnings line item"""
    description: str
    rate: Optional[Decimal] = None
    hours: Optional[Decimal] = None
    current_amount: Decimal
    ytd_amount: Optional[Decimal] = None
    is_employer_contribution: bool = False  # True for 401k match, employer benefits, etc.


class DeductionDetail(BaseModel):
    """Individual deduction line item"""
    description: str
    current_amount: Decimal
    ytd_amount: Optional[Decimal] = None
    is_pre_tax: bool = False


class TaxDetail(BaseModel):
    """Tax withholding information"""
    tax_type: str  # Federal, State, FICA, etc.
    current_amount: Decimal
    ytd_amount: Optional[Decimal] = None
    taxable_wages_current: Optional[Decimal] = None
    taxable_wages_ytd: Optional[Decimal] = None


class EmployerInfo(BaseModel):
    """Employer information"""
    company_name: str
    address: Optional[AddressModel] = None
    employee_id: Optional[str] = None


class EmployeeInfo(BaseModel):
    """Employee information"""
    name: str
    address: Optional[AddressModel] = None
    ssn_masked: Optional[str] = None


class PaystubData(BaseModel):
    """Complete paystub data structure"""
    # Meta information
    employer: EmployerInfo
    employee: EmployeeInfo
    payroll_period: PayrollPeriod
    
    # Financial data
    gross_pay_current: Decimal
    gross_pay_ytd: Optional[Decimal] = None
    net_pay_current: Decimal
    net_pay_ytd: Optional[Decimal] = None
    
    # Detailed breakdowns
    earnings: List[EarningsDetail] = Field(default_factory=list)
    deductions: List[DeductionDetail] = Field(default_factory=list)
    taxes: List[TaxDetail] = Field(default_factory=list)
    
    # Validation fields
    total_hours_current: Optional[Decimal] = None
    pay_frequency: Optional[str] = None  # Weekly, Bi-weekly, Monthly, etc.
    
    # Quality metrics
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    validation_warnings: List[str] = Field(default_factory=list)
    
    # Processing metadata
    processing_metadata: Optional[Dict[str, Any]] = None


class PaystubParser:
    """
    Enhanced paystub parser with multi-modal processing pipeline
    
    Processing Flow:
    1. Try Camelot for structured table extraction
    2. Fallback to pdfplumber for text-based extraction
    3. Convert PDF to images for GPT-4 Vision analysis
    4. Cross-validate and enhance with AI
    5. Validate and format final output
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the paystub parser"""
        self.openai_client = openai.OpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY')
        )
        
        # Paystub field patterns for extraction
        self.paystub_patterns = {
            'amounts': [
                r'\$?([0-9,]+\.?[0-9]{0,2})',
                r'([0-9,]+\.?[0-9]{0,2})'
            ],
            'dates': [
                r'(\d{1,2}/\d{1,2}/\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}-\d{1,2}-\d{2,4})'
            ],
            'ssn': [
                r'(\d{3}-\d{2}-\d{4})',
                r'(\*{3,5}\d{4})',
                r'(XXX-XX-\d{4})',
                r'(\d{9})'
            ],
            'employee_id': [
                r'Employee\s+ID[:\s]*([A-Za-z0-9\-]+)',
                r'ID[:\s]*([A-Za-z0-9\-]+)',
                r'Employee\s+Number[:\s]*([A-Za-z0-9\-]+)'
            ],
            'pay_frequency': [
                r'(Weekly|Bi-weekly|Biweekly|Monthly|Semi-monthly|Quarterly|Annual)',
                r'(WEEKLY|BI-WEEKLY|BIWEEKLY|MONTHLY|SEMI-MONTHLY)'
            ]
        }
        
        # Generic paystub field mappings - flexible patterns for any paystub format
        self.field_mappings = {
            'gross_pay': [
                'gross pay', 'gross earnings', 'total earnings', 'earnings', 'gross wages',
                'total pay', 'gross income', 'total gross', 'gross amount', 'earned',
                'total compensation', 'gross compensation', 'pay before deductions'
            ],
            'net_pay': [
                'net pay', 'take home', 'direct deposit', 'net earnings', 'net wages',
                'take home pay', 'net amount', 'pay after deductions', 'final pay',
                'net income', 'disposable income', 'net compensation'
            ],
            'federal_tax': [
                'federal tax', 'fed tax', 'federal withholding', 'federal income tax',
                'federal income', 'fed withholding', 'federal', 'federal tax withheld',
                'federal income tax withheld', 'federal deduction'
            ],
            'state_tax': [
                'state tax', 'state withholding', 'state income tax', 'state income',
                'state withholding tax', 'state', 'state tax withheld', 'state deduction'
            ],
            'fica': [
                'fica', 'social security', 'ss tax', 'medicare', 'social security tax',
                'medicare tax', 'ss withholding', 'medicare withholding', 'fica tax',
                'social security withholding', 'medicare withholding', 'ss', 'med'
            ],
            'regular_pay': [
                'regular', 'regular pay', 'regular earnings', 'salary', 'regular wages',
                'base pay', 'base salary', 'hourly', 'hourly pay', 'standard pay',
                'normal pay', 'regular hours', 'straight time'
            ],
            'overtime': [
                'overtime', 'ot', 'overtime pay', 'overtime earnings', 'overtime wages',
                'ot pay', 'overtime hours', 'time and half', '1.5x', 'overtime premium'
            ],
            'bonus': [
                'bonus', 'incentive', 'commission', 'bonus pay', 'incentive pay',
                'commission pay', 'performance bonus', 'sales bonus', 'year end bonus',
                'holiday bonus', 'special pay', 'additional pay'
            ],
            'deductions': [
                'deduction', 'deductions', 'withholding', 'withholdings', 'benefits',
                'insurance', 'retirement', '401k', '403b', 'pension', 'health',
                'dental', 'vision', 'life insurance', 'disability', 'union dues',
                'parking', 'meals', 'uniform', 'tools', 'loan', 'advance'
            ]
        }

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main parsing method - public interface
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Structured paystub data as dictionary
        """
        try:
            logger.info(f"Starting paystub parsing for: {pdf_path}")
            
            # Step 1: Try Camelot for table extraction
            camelot_data = self.extract_with_camelot(pdf_path)
            
            # Step 2: Fallback to pdfplumber for text extraction
            pdfplumber_data = self.extract_with_pdfplumber(pdf_path)
            
            # Step 3: Convert PDF to images for GPT Vision
            pdf_images = self.convert_pdf_to_images(pdf_path)
            
            # Step 4: Analyze with GPT Vision
            gpt_enhanced_data = self.analyze_with_gpt_vision(
                camelot_data, pdfplumber_data, pdf_images[0] if pdf_images else None
            )
            
            # Step 5: Categorize earnings
            if 'earnings' in gpt_enhanced_data:
                gpt_enhanced_data['earnings'] = self.categorize_earnings(gpt_enhanced_data['earnings'])
            
            # Step 6: Validate and format
            final_data = self.validate_and_format(gpt_enhanced_data)
            
            logger.info(f"Paystub parsing completed with confidence: {final_data.get('extraction_confidence', 0):.2%}")
            return final_data
            
        except Exception as e:
            logger.error(f"Paystub parsing failed: {e}")
            return {
                "error": str(e),
                "document_type": "paystub",
                "status": "failed",
                "extraction_confidence": 0.0
            }

    def extract_with_camelot(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract structured data using Camelot table detection
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted table data
        """
        try:
            logger.info("Attempting Camelot table extraction...")
            
            # Try lattice flavor first (better for structured tables)
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            if not tables:
                # Try stream flavor if lattice fails
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            extracted_data = {
                "tables": [],
                "table_count": len(tables),
                "raw_text_data": {},
                "extraction_method": "camelot"
            }
            
            # Process each table
            for i, table in enumerate(tables):
                table_data = {
                    "table_index": i,
                    "accuracy": table.accuracy,
                    "whitespace": table.whitespace,
                    "data": table.df.to_dict('records') if not table.df.empty else [],
                    "raw_dataframe": table.df.to_string() if not table.df.empty else ""
                }
                extracted_data["tables"].append(table_data)
                
                # Try to extract paystub specific fields from this table
                if not table.df.empty:
                    extracted_data["raw_text_data"].update(
                        self.extract_paystub_fields_from_table(table.df)
                    )
            
            logger.info(f"Camelot extracted {len(tables)} tables")
            return extracted_data
            
        except Exception as e:
            logger.warning(f"Camelot extraction failed: {e}")
            return {
                "error": f"Camelot extraction failed: {str(e)}",
                "tables": [],
                "table_count": 0,
                "raw_text_data": {},
                "extraction_method": "camelot_failed"
            }

    def extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text data using pdfplumber as fallback
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text data
        """
        try:
            logger.info("Attempting pdfplumber text extraction...")
            
            extracted_data = {
                "text_content": "",
                "pages": [],
                "raw_text_data": {},
                "extraction_method": "pdfplumber"
            }
            
            with pdfplumber.open(pdf_path) as pdf:
                extracted_data["page_count"] = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    extracted_data["text_content"] += page_text + "\n"
                    extracted_data["pages"].append({
                        "page_number": i + 1,
                        "text": page_text,
                        "char_count": len(page_text)
                    })
                
                # Extract paystub fields from text
                extracted_data["raw_text_data"] = self.extract_paystub_fields_from_text(
                    extracted_data["text_content"]
                )
            
            logger.info(f"pdfplumber extracted {len(extracted_data['text_content'])} characters")
            return extracted_data
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return {
                "error": f"pdfplumber extraction failed: {str(e)}",
                "text_content": "",
                "pages": [],
                "raw_text_data": {},
                "extraction_method": "pdfplumber_failed"
            }

    def extract_paystub_fields_from_table(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract paystub specific fields from a DataFrame
        
        Args:
            df: Pandas DataFrame from Camelot
            
        Returns:
            Dictionary with extracted paystub fields
        """
        fields = {}
        
        # Convert DataFrame to string for pattern matching
        table_text = df.to_string()
        
        # Extract amounts
        amounts = []
        for pattern in self.paystub_patterns['amounts']:
            matches = re.findall(pattern, table_text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    if amount > 0:
                        amounts.append(amount)
                except ValueError:
                    continue
        
        fields['detected_amounts'] = amounts[:20]  # Limit to reasonable number
        
        # Extract dates
        dates = []
        for pattern in self.paystub_patterns['dates']:
            matches = re.findall(pattern, table_text)
            dates.extend(matches)
        
        fields['detected_dates'] = dates[:10]  # Limit to reasonable number
        
        # Extract SSN
        for pattern in self.paystub_patterns['ssn']:
            match = re.search(pattern, table_text)
            if match:
                fields['employee_ssn'] = match.group(1)
                break
        
        # Extract employee ID
        for pattern in self.paystub_patterns['employee_id']:
            match = re.search(pattern, table_text, re.IGNORECASE)
            if match:
                fields['employee_id'] = match.group(1)
                break
        
        # Extract pay frequency
        for pattern in self.paystub_patterns['pay_frequency']:
            match = re.search(pattern, table_text, re.IGNORECASE)
            if match:
                fields['pay_frequency'] = match.group(1)
                break
        
        return fields

    def extract_paystub_fields_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract paystub specific fields from raw text
        
        Args:
            text: Raw text content from pdfplumber
            
        Returns:
            Dictionary with extracted paystub fields
        """
        fields = {}
        
        # Extract amounts
        amounts = []
        for pattern in self.paystub_patterns['amounts']:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    if amount > 0:
                        amounts.append(amount)
                except ValueError:
                    continue
        
        fields['detected_amounts'] = amounts[:20]
        
        # Extract dates
        dates = []
        for pattern in self.paystub_patterns['dates']:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        fields['detected_dates'] = dates[:10]
        
        # Extract SSN
        for pattern in self.paystub_patterns['ssn']:
            match = re.search(pattern, text)
            if match:
                fields['employee_ssn'] = match.group(1)
                break
        
        # Extract employee ID
        for pattern in self.paystub_patterns['employee_id']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['employee_id'] = match.group(1)
                break
        
        # Extract pay frequency
        for pattern in self.paystub_patterns['pay_frequency']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields['pay_frequency'] = match.group(1)
                break
        
        # Extract company name (usually at the top)
        company_patterns = [
            r'^([A-Za-z\s&,\.]+(?:Inc|LLC|Corp|Company|Group|Limited|Ltd|Incorporated|Corporation|Associates|Partners|Enterprises|Services|Systems|Solutions|Technologies|Industries|Manufacturing|Holdings|International|Global|Worldwide|USA|US|America))',
            r'([A-Za-z\s&,\.]+(?:Inc|LLC|Corp|Company|Group|Limited|Ltd|Incorporated|Corporation|Associates|Partners|Enterprises|Services|Systems|Solutions|Technologies|Industries|Manufacturing|Holdings|International|Global|Worldwide|USA|US|America))',
            # Generic pattern for any capitalized company name at the start
            r'^([A-Z][A-Za-z\s&,\.]{2,50}(?:\s+(?:Inc|LLC|Corp|Company|Group|Limited|Ltd|Incorporated|Corporation|Associates|Partners|Enterprises|Services|Systems|Solutions|Technologies|Industries|Manufacturing|Holdings|International|Global|Worldwide|USA|US|America))?)',
            # Pattern for company names without suffixes
            r'^([A-Z][A-Za-z\s&,\.]{2,30}(?=\s|$))'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                company_name = match.group(1).strip()
                # Filter out common false positives
                if not any(word in company_name.lower() for word in ['pay', 'statement', 'earnings', 'employee', 'period', 'date', 'gross', 'net']):
                    fields['company_name'] = company_name
                    break
        
        # Extract employee name (usually after company info)
        name_patterns = [
            r'([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',  # First Middle Last
            r'([A-Z][a-z]+ [A-Z][a-z]+)',  # First Last
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                fields['employee_name'] = match.group(1).strip()
                break
        
        return fields

    def extract_dynamic_field_mappings(self, text: str) -> Dict[str, List[str]]:
        """
        Dynamically extract field mappings from paystub text to handle any format
        
        Args:
            text: Raw text content from paystub
            
        Returns:
            Dictionary of field mappings specific to this paystub
        """
        dynamic_mappings = {}
        
        # Look for common paystub section headers
        section_patterns = {
            'earnings': [
                r'earnings?', r'pay\s+details?', r'wages?', r'salary', r'compensation',
                r'regular\s+pay', r'hourly\s+pay', r'base\s+pay'
            ],
            'deductions': [
                r'deductions?', r'withholdings?', r'benefits?', r'pre-tax\s+deductions?',
                r'post-tax\s+deductions?', r'voluntary\s+deductions?'
            ],
            'taxes': [
                r'taxes?', r'tax\s+withholdings?', r'federal\s+tax', r'state\s+tax',
                r'fica', r'social\s+security', r'medicare'
            ],
            'summary': [
                r'summary', r'totals?', r'net\s+pay', r'gross\s+pay', r'final\s+pay',
                r'take\s+home', r'direct\s+deposit'
            ]
        }
        
        # Extract section-specific terminology
        for section, patterns in section_patterns.items():
            section_terms = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                section_terms.extend(matches)
            dynamic_mappings[section] = list(set(section_terms))
        
        return dynamic_mappings

    def categorize_earnings(self, earnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Categorize earnings as employee earnings vs employer contributions
        
        Args:
            earnings: List of earnings dictionaries
            
        Returns:
            List of earnings with is_employer_contribution flag set
        """
        employer_contribution_keywords = [
            '401k match', '401k matching', 'employer match', 'company match',
            'employer contribution', 'company contribution', 'employer benefit',
            'employer paid', 'company paid', 'employer 401k', 'company 401k',
            'pension contribution', 'employer pension', 'retirement match',
            'employer retirement', 'company retirement', 'employer hsa',
            'company hsa', 'employer fsa', 'company fsa', 'er cost', 'er cost of'
        ]
        
        categorized_earnings = []
        for earning in earnings:
            earning_copy = earning.copy()
            description = earning.get('description', '').lower()
            
            # Check if this is an employer contribution
            is_employer_contribution = any(
                keyword in description for keyword in employer_contribution_keywords
            )
            
            earning_copy['is_employer_contribution'] = is_employer_contribution
            categorized_earnings.append(earning_copy)
        
        return categorized_earnings

    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF to images for GPT Vision analysis
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Images
        """
        try:
            logger.info("Converting PDF to images for GPT Vision...")
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
            logger.info(f"Converted PDF to {len(images)} images")
            return images
        except Exception as e:
            logger.warning(f"PDF to image conversion failed: {e}")
            return []

    def encode_image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string for OpenAI API
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded image string
        """
        import io
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr = img_byte_arr.getvalue()
        
        # Encode to base64
        return base64.b64encode(img_byte_arr).decode('utf-8')

    def analyze_with_gpt_vision(self, camelot_data: Dict[str, Any], pdfplumber_data: Dict[str, Any], pdf_image: Optional[Image.Image]) -> Dict[str, Any]:
        """
        Use GPT Vision to validate and enhance extraction
        
        Args:
            camelot_data: Data extracted by Camelot
            pdfplumber_data: Data extracted by pdfplumber
            pdf_image: First page of PDF as image
            
        Returns:
            Enhanced data with GPT Vision analysis
        """
        try:
            logger.info("Analyzing with GPT-4 Vision...")
            
            # Prepare the prompt for GPT Vision
            prompt = self.create_gpt_vision_prompt(camelot_data, pdfplumber_data)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Add image if available
            if pdf_image:
                image_base64 = self.encode_image_to_base64(pdf_image)
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "high"
                    }
                })
            
            # Call GPT-4 Vision
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=3000,
                temperature=0.1
            )
            
            # Parse the response
            gpt_response = response.choices[0].message.content
            enhanced_data = self.parse_gpt_response(gpt_response, camelot_data, pdfplumber_data)
            
            logger.info("GPT-4 Vision analysis completed")
            return enhanced_data
            
        except Exception as e:
            logger.warning(f"GPT Vision analysis failed: {e}")
            # Fallback to combined extraction data
            return self.format_extraction_data_only(camelot_data, pdfplumber_data)

    def create_gpt_vision_prompt(self, camelot_data: Dict[str, Any], pdfplumber_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive prompt for GPT Vision analysis
        
        Args:
            camelot_data: Data extracted by Camelot
            pdfplumber_data: Data extracted by pdfplumber
            
        Returns:
            Formatted prompt string
        """
        return f"""
Analyze this paystub document and extract ALL fields accurately. This is a generic paystub parser that should work with ANY paystub format from ANY company. I have some preliminary data from table and text extraction below, but I need you to verify and complete the information by examining the image.

PRELIMINARY CAMELOT TABLE DATA:
{json.dumps(camelot_data, indent=2)}

PRELIMINARY PDFPLUMBER TEXT DATA:
{json.dumps(pdfplumber_data, indent=2)}

Please extract and return a JSON object with the following structure:

{{
  "document_type": "paystub",
  "employer": {{
    "company_name": "Company Name",
    "address": {{
      "street": "Street Address",
      "city": "City",
      "state": "ST",
      "zip": "12345"
    }},
    "employee_id": "Employee ID"
  }},
  "employee": {{
    "name": "Full Name",
    "address": {{
      "street": "Street Address",
      "city": "City",
      "state": "ST",
      "zip": "12345"
    }},
    "ssn_masked": "XXX-XX-XXXX"
  }},
  "payroll_period": {{
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "pay_date": "YYYY-MM-DD"
  }},
  "gross_pay_current": 0.00,
  "gross_pay_ytd": 0.00,
  "net_pay_current": 0.00,
  "net_pay_ytd": 0.00,
  "earnings": [
    {{
      "description": "Regular Pay",
      "rate": 0.00,
      "hours": 0.00,
      "current_amount": 0.00,
      "ytd_amount": 0.00,
      "is_employer_contribution": false
    }}
  ],
  "deductions": [
    {{
      "description": "Health Insurance",
      "current_amount": 0.00,
      "ytd_amount": 0.00,
      "is_pre_tax": true
    }}
  ],
  "taxes": [
    {{
      "tax_type": "Federal Tax",
      "current_amount": 0.00,
      "ytd_amount": 0.00,
      "taxable_wages_current": 0.00,
      "taxable_wages_ytd": 0.00
    }}
  ],
  "total_hours_current": 0.00,
  "pay_frequency": "Bi-weekly",
  "extraction_confidence": 0.95
}}

IMPORTANT INSTRUCTIONS:
1. Use the preliminary data to guide you, but rely on the image for accuracy
2. Look for standard paystub sections: Employee Info, Pay Period, Earnings, Deductions, Taxes, Net Pay
3. Extract all monetary amounts as numbers (no $ signs or commas)
4. Handle date formats consistently (YYYY-MM-DD)
5. For earnings, include description, rate, hours, current amount, YTD amount, and is_employer_contribution flag
6. For deductions, include description, current amount, YTD amount, and whether it's pre-tax
7. For taxes, include tax type, current amount, YTD amount, and taxable wages
8. Calculate total hours from all earnings entries
9. Determine pay frequency from the document (Weekly, Bi-weekly, Monthly, etc.)
10. Extract company name from the header/top of the document
11. Extract employee name from the employee information section
12. CRITICAL: Set is_employer_contribution to true for ALL employer-paid items including:
    - 401k match, 401k matching, employer match, company match
    - Employer contributions, company contributions, employer benefits
    - Employer paid, company paid items
    - ER Cost, ER Cost of, Employer Cost, Company Cost
    - Pension contributions, retirement matches
    - Employer HSA, FSA contributions
    - Any item clearly marked as employer expense or cost
13. For gross_pay_current, extract the main gross pay amount (usually base salary + regular earnings)
14. Holiday pay, bonuses, and additional compensation should be included in earnings but may not always equal gross pay
15. Provide a confidence score based on data quality and completeness
16. Return ONLY the JSON object, no additional text

GENERIC EXTRACTION GUIDELINES:
- Work with ANY paystub format, not just specific companies
- Adapt to different layouts and terminology
- Handle both digital and scanned paystubs
- Extract data based on semantic meaning, not position
- Be flexible with field names and descriptions
- Focus on accuracy and completeness. If a field is not clearly visible, use null.

PAYROLL STRUCTURE UNDERSTANDING:
- Gross pay may represent base compensation (regular + commission) or total compensation
- Additional earnings like holiday pay, bonuses, overtime may be separate from base gross pay
- Employer costs (ER Cost, employer contributions) should be marked as employer contributions
- Some paystubs have complex structures where total earnings ≠ gross pay
- Always prioritize accuracy over strict mathematical consistency
- When in doubt about classification, err on the side of including items in earnings but mark employer costs correctly
"""

    def parse_gpt_response(self, gpt_response: str, camelot_data: Dict[str, Any], pdfplumber_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate GPT Vision response
        
        Args:
            gpt_response: Raw response from GPT Vision
            camelot_data: Original Camelot data for fallback
            pdfplumber_data: Original pdfplumber data for fallback
            
        Returns:
            Parsed and validated data
        """
        try:
            # Extract JSON from response
            json_start = gpt_response.find('{')
            json_end = gpt_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = gpt_response[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Add metadata
                parsed_data['processing_metadata'] = {
                    'camelot_tables_found': camelot_data.get('table_count', 0),
                    'pdfplumber_text_length': len(pdfplumber_data.get('text_content', '')),
                    'gpt_vision_used': True,
                    'extraction_method': 'multi_modal_ai_enhanced'
                }
                
                return parsed_data
            else:
                raise ValueError("No valid JSON found in GPT response")
                
        except Exception as e:
            logger.warning(f"Failed to parse GPT response: {e}")
            return self.format_extraction_data_only(camelot_data, pdfplumber_data)

    def format_extraction_data_only(self, camelot_data: Dict[str, Any], pdfplumber_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format extraction data into paystub structure when GPT Vision fails
        
        Args:
            camelot_data: Raw Camelot extraction data
            pdfplumber_data: Raw pdfplumber extraction data
            
        Returns:
            Formatted paystub data structure
        """
        # Combine data from both extraction methods
        combined_data = {}
        combined_data.update(camelot_data.get('raw_text_data', {}))
        combined_data.update(pdfplumber_data.get('raw_text_data', {}))
        
        # Build basic structure from combined data
        paystub_data = {
            "document_type": "paystub",
            "employer": {
                "company_name": combined_data.get('company_name', 'Unknown Company'),
                "address": None,
                "employee_id": combined_data.get('employee_id')
            },
            "employee": {
                "name": combined_data.get('employee_name', 'Unknown Employee'),
                "address": None,
                "ssn_masked": combined_data.get('employee_ssn')
            },
            "payroll_period": {
                "start_date": None,
                "end_date": None,
                "pay_date": None
            },
            "gross_pay_current": 0.00,
            "gross_pay_ytd": None,
            "net_pay_current": 0.00,
            "net_pay_ytd": None,
            "earnings": [],
            "deductions": [],
            "taxes": [],
            "total_hours_current": None,
            "pay_frequency": combined_data.get('pay_frequency'),
            "extraction_confidence": 0.6,  # Lower confidence without GPT Vision
            "processing_metadata": {
                'camelot_tables_found': camelot_data.get('table_count', 0),
                'pdfplumber_text_length': len(pdfplumber_data.get('text_content', '')),
                'gpt_vision_used': False,
                'extraction_method': 'traditional_extraction_only',
                'detected_amounts': combined_data.get('detected_amounts', []),
                'detected_dates': combined_data.get('detected_dates', [])
            }
        }
        
        return paystub_data

    def calculate_confidence_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data completeness and quality
        
        Args:
            data: Extracted paystub data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        max_score = 100.0
        
        # Basic information (30 points)
        if data.get('employer', {}).get('company_name'):
            score += 10
        if data.get('employee', {}).get('name'):
            score += 10
        if data.get('payroll_period', {}).get('pay_date'):
            score += 10
        
        # Financial data (40 points)
        if data.get('gross_pay_current', 0) > 0:
            score += 15
        if data.get('net_pay_current', 0) > 0:
            score += 15
        if data.get('earnings') and len(data['earnings']) > 0:
            score += 10
        
        # Detailed breakdowns (20 points)
        if data.get('taxes') and len(data['taxes']) > 0:
            score += 10
        if data.get('deductions') and len(data['deductions']) > 0:
            score += 10
        
        # Processing quality (10 points)
        metadata = data.get('processing_metadata', {})
        if metadata.get('gpt_vision_used'):
            score += 5
        if metadata.get('camelot_tables_found', 0) > 0:
            score += 3
        if metadata.get('pdfplumber_text_length', 0) > 100:
            score += 2
        
        return min(score / max_score, 1.0)

    def validate_paystub_data(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate paystub data for consistency and completeness
        
        Args:
            data: Extracted paystub data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for required fields
        if not data.get('gross_pay_current', 0):
            warnings.append("Missing gross pay current amount")
        
        if not data.get('net_pay_current', 0):
            warnings.append("Missing net pay current amount")
        
        # Check mathematical consistency
        gross_pay = data.get('gross_pay_current', 0)
        net_pay = data.get('net_pay_current', 0)
        
        if gross_pay > 0 and net_pay > 0:
            if net_pay >= gross_pay:
                warnings.append("Net pay is greater than or equal to gross pay - check deductions")
        
        # Check earnings consistency (exclude employer contributions)
        earnings = data.get('earnings', [])
        if earnings:
            # Calculate total employee earnings (exclude employer contributions)
            employee_earnings = sum(
                earn.get('current_amount', 0) 
                for earn in earnings 
                if not earn.get('is_employer_contribution', False)
            )
            total_earnings = sum(earn.get('current_amount', 0) for earn in earnings)
            
            # Check if employee earnings match gross pay (with more tolerance for complex payroll structures)
            earnings_difference = abs(employee_earnings - gross_pay)
            if earnings_difference > 0.01:
                # Only warn if the difference is significant (more than 5% or $100)
                if earnings_difference > max(100, gross_pay * 0.05):
                    warnings.append(f"Employee earnings total ({employee_earnings}) doesn't match gross pay ({gross_pay}) - difference: ${earnings_difference:.2f}")
            
            # Also check total earnings for reference (including employer contributions)
            total_difference = abs(total_earnings - gross_pay)
            if total_difference > 0.01 and employee_earnings != total_earnings:
                # Only warn if the difference is significant
                if total_difference > max(100, gross_pay * 0.05):
                    warnings.append(f"Total earnings ({total_earnings}) includes employer contributions and doesn't match gross pay ({gross_pay}) - difference: ${total_difference:.2f}")
        
        # Check for reasonable values
        if gross_pay > 0 and gross_pay < 100:
            warnings.append("Gross pay seems unusually low")
        
        if gross_pay > 0 and gross_pay > 50000:
            warnings.append("Gross pay seems unusually high for a single pay period")
        
        return warnings

    def validate_and_format(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final validation and formatting of extracted data
        
        Args:
            raw_data: Raw extracted data
            
        Returns:
            Validated and formatted paystub data
        """
        try:
            # Calculate confidence score
            confidence = self.calculate_confidence_score(raw_data)
            raw_data['extraction_confidence'] = confidence
            
            # Validate data
            validation_warnings = self.validate_paystub_data(raw_data)
            raw_data['validation_warnings'] = validation_warnings
            
            # Use Pydantic model for validation
            paystub_doc = PaystubData(**raw_data)
            
            # Convert back to dict with proper formatting
            validated_data = paystub_doc.model_dump(exclude_none=False)
            
            # Add final processing metadata
            if not validated_data.get('processing_metadata'):
                validated_data['processing_metadata'] = {}
            
            validated_data['processing_metadata'].update({
                'validation_passed': True,
                'validation_method': 'pydantic',
                'validation_warnings_count': len(validation_warnings)
            })
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            # Return raw data with validation error
            raw_data['processing_metadata'] = raw_data.get('processing_metadata', {})
            raw_data['processing_metadata'].update({
                'validation_passed': False,
                'validation_error': str(e),
                'validation_method': 'pydantic'
            })
            return raw_data


def main():
    """
    Example usage of the paystub parser
    """
    import sys
    from pathlib import Path
    
    # Check if file path provided
    if len(sys.argv) < 2:
        print("Usage: python paystub_parser.py <path_to_paystub_pdf>")
        print("\nExample with sample files:")
        sample_files = Path("data/paystubs").glob("*.pdf") if Path("data/paystubs").exists() else []
        for sample in list(sample_files)[:3]:
            print(f"  python paystub_parser.py {sample}")
        return
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    # Initialize parser
    parser = PaystubParser()
    
    print(f"🔄 Parsing paystub document: {Path(pdf_path).name}")
    print("=" * 50)
    
    # Parse the document
    import time
    start_time = time.time()
    
    result = parser.parse_pdf(pdf_path)
    
    processing_time = time.time() - start_time
    
    # Display results
    print(f"⏱️  Processing time: {processing_time:.2f} seconds")
    print(f"📊 Confidence score: {result.get('extraction_confidence', 'N/A')}")
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Extraction completed successfully!")
        
        # Print key extracted fields
        employer = result.get('employer', {})
        employee = result.get('employee', {})
        payroll_period = result.get('payroll_period', {})
        
        print(f"\n📋 Key Information:")
        print(f"  Employee: {employee.get('name', 'N/A')}")
        print(f"  Company: {employer.get('company_name', 'N/A')}")
        print(f"  Employee ID: {employer.get('employee_id', 'N/A')}")
        print(f"  Pay Date: {payroll_period.get('pay_date', 'N/A')}")
        
        gross_pay = result.get('gross_pay_current', 0) or 0
        net_pay = result.get('net_pay_current', 0) or 0
        print(f"  Gross Pay: ${gross_pay:,.2f}")
        print(f"  Net Pay: ${net_pay:,.2f}")
        
        # Display earnings breakdown
        earnings = result.get('earnings', [])
        if earnings:
            print(f"\n💰 Earnings Breakdown:")
            for earning in earnings:
                desc = earning.get('description', 'Unknown')
                amount = earning.get('current_amount', 0) or 0
                hours = earning.get('hours')
                rate = earning.get('rate')
                
                if hours and rate:
                    print(f"    {desc}: {hours} hrs @ ${rate:.2f}/hr = ${amount:,.2f}")
                else:
                    print(f"    {desc}: ${amount:,.2f}")
        
        # Display validation warnings
        warnings = result.get('validation_warnings', [])
        if warnings:
            print(f"\n⚠️  Validation Warnings:")
            for warning in warnings:
                print(f"    • {warning}")
        
        # Display processing metadata
        metadata = result.get('processing_metadata', {})
        if metadata:
            print(f"\n🔧 Processing Information:")
            print(f"    Extraction Method: {metadata.get('extraction_method', 'N/A')}")
            print(f"    GPT Vision Used: {'✅' if metadata.get('gpt_vision_used') else '❌'}")
            print(f"    Tables Found: {metadata.get('camelot_tables_found', 0)}")
            print(f"    Text Length: {metadata.get('pdfplumber_text_length', 0)} characters")
    
    # Save results to data/paystubs/results directory
    results_dir = Path("data/paystubs/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output filename based on input file
    input_filename = Path(pdf_path).stem
    output_file = results_dir / f"{input_filename}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
