"""
PDF W-2 Form Parser using Camelot + GPT Vision Pipeline

This module implements a single-file PDF W-2 parser that extracts structured data 
from regular PDF W-2 documents using Camelot for table extraction and GPT Vision 
for validation and enhancement.

Architecture: PDF → Camelot → GPT Vision → Structured JSON
"""

import os
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import re

# Core dependencies
import camelot
import pandas as pd
from pydantic import BaseModel, Field, validator
from pdf2image import convert_from_path
from PIL import Image
import openai

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


class Box12Code(BaseModel):
    """Box 12 code and amount"""
    code: str
    amount: Optional[float] = None


class EmployeeInfo(BaseModel):
    """Employee information from W-2"""
    ssn: Optional[str] = None
    name: Optional[str] = None
    address: Optional[AddressModel] = None


class EmployerInfo(BaseModel):
    """Employer information from W-2"""
    ein: Optional[str] = None
    name: Optional[str] = None
    address: Optional[AddressModel] = None
    control_number: Optional[str] = None


class IncomeTaxInfo(BaseModel):
    """Income and tax information from boxes 1-14"""
    wages_tips_compensation: Optional[float] = Field(None, description="Box 1")
    federal_income_tax_withheld: Optional[float] = Field(None, description="Box 2")
    social_security_wages: Optional[float] = Field(None, description="Box 3")
    social_security_tax_withheld: Optional[float] = Field(None, description="Box 4")
    medicare_wages_tips: Optional[float] = Field(None, description="Box 5")
    medicare_tax_withheld: Optional[float] = Field(None, description="Box 6")
    social_security_tips: Optional[float] = Field(None, description="Box 7")
    allocated_tips: Optional[float] = Field(None, description="Box 8")
    dependent_care_benefits: Optional[float] = Field(None, description="Box 10")
    nonqualified_plans: Optional[float] = Field(None, description="Box 11")
    box_12_codes: List[Box12Code] = Field(default_factory=list)
    statutory_employee: bool = False
    retirement_plan: bool = False
    third_party_sick_pay: bool = False


class StateLocalInfo(BaseModel):
    """State and local tax information"""
    state: Optional[str] = None
    state_wages: Optional[float] = None
    state_income_tax: Optional[float] = None
    locality: Optional[str] = None
    local_wages: Optional[float] = None
    local_income_tax: Optional[float] = None


class CalculatedIncome(BaseModel):
    """Calculated income information for mortgage approval"""
    primary_income: Optional[float] = Field(None, description="Box 1 - Wages, tips, other compensation")
    social_security_wages: Optional[float] = Field(None, description="Box 3 - Social security wages")
    medicare_wages: Optional[float] = Field(None, description="Box 5 - Medicare wages and tips")
    annual_income: Optional[float] = Field(None, description="Primary annual income for mortgage calculation")
    monthly_income: Optional[float] = Field(None, description="Monthly income for DTI calculation")
    income_verification_method: str = Field("box_1_wages", description="Method used for income calculation")
    additional_benefits: Optional[float] = Field(None, description="Total value of Box 12 benefits")


class W2Document(BaseModel):
    """Complete W-2 document structure"""
    document_type: str = "W-2"
    tax_year: Optional[str] = None
    employee: Optional[EmployeeInfo] = None
    employer: Optional[EmployerInfo] = None
    income_tax_info: Optional[IncomeTaxInfo] = None
    state_local_info: List[StateLocalInfo] = Field(default_factory=list)
    calculated_income: Optional[CalculatedIncome] = None
    raw_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    processing_metadata: Optional[Dict[str, Any]] = None


class W2Parser:
    """
    Main W-2 parser class implementing Camelot + GPT Vision pipeline
    
    Flow:
    1. Extract tables using Camelot
    2. Convert PDF to images for GPT Vision
    3. Send both Camelot data and images to GPT Vision
    4. Validate and format final output
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the W-2 parser"""
        self.openai_client = openai.OpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY')
        )
        
        # W-2 field patterns for extraction
        self.w2_field_patterns = {
            'ssn': [
                r'(\d{3}-\d{2}-\d{4})',
                r'(\*{3,5}\d{4})',
                r'(XXX-XX-\d{4})',
                r'(\d{9})'
            ],
            'ein': [
                r'(\d{2}-\d{7})',
                r'(\d{9})'
            ],
            'amounts': [
                r'\$?([0-9,]+\.?[0-9]{0,2})',
                r'([0-9,]+\.?[0-9]{0,2})'
            ],
            'box_12_codes': [
                r'([A-Z]{1,2})\s*([0-9,]+\.?[0-9]{0,2})',
                r'Code\s*([A-Z]+).*?([0-9,]+\.?[0-9]{0,2})'
            ]
        }

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main parsing method - public interface
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Structured W-2 data as dictionary
        """
        try:
            # Step 1: Extract with Camelot
            camelot_data = self.extract_with_camelot(pdf_path)
            
            # Step 2: Convert PDF to image for GPT Vision
            pdf_images = self.convert_pdf_to_images(pdf_path)
            
            # Step 3: Analyze with GPT Vision
            gpt_enhanced_data = self.analyze_with_gpt_vision(camelot_data, pdf_images[0] if pdf_images else None)
            
            # Step 4: Validate and format
            final_data = self.validate_and_format(gpt_enhanced_data)
            
            return final_data
            
        except Exception as e:
            return {
                "error": str(e),
                "document_type": "W-2",
                "status": "failed",
                "confidence_score": 0.0
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
            # Read tables from PDF
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            if not tables:
                # Try stream flavor if lattice fails
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            extracted_data = {
                "tables": [],
                "table_count": len(tables),
                "raw_text_data": {}
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
                
                # Try to extract W-2 specific fields from this table
                if not table.df.empty:
                    extracted_data["raw_text_data"].update(
                        self.extract_w2_fields_from_table(table.df)
                    )
            
            return extracted_data
            
        except Exception as e:
            return {
                "error": f"Camelot extraction failed: {str(e)}",
                "tables": [],
                "table_count": 0,
                "raw_text_data": {}
            }

    def extract_w2_fields_from_table(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract W-2 specific fields from a DataFrame
        
        Args:
            df: Pandas DataFrame from Camelot
            
        Returns:
            Dictionary with extracted W-2 fields
        """
        fields = {}
        
        # Convert DataFrame to string for pattern matching
        table_text = df.to_string()
        
        # Extract SSN
        for pattern in self.w2_field_patterns['ssn']:
            match = re.search(pattern, table_text)
            if match:
                fields['employee_ssn'] = match.group(1)
                break
        
        # Extract EIN
        for pattern in self.w2_field_patterns['ein']:
            match = re.search(pattern, table_text)
            if match:
                fields['employer_ein'] = match.group(1)
                break
        
        # Extract numeric amounts (boxes 1-11)
        amounts = []
        for pattern in self.w2_field_patterns['amounts']:
            matches = re.findall(pattern, table_text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    if amount > 0:
                        amounts.append(amount)
                except ValueError:
                    continue
        
        fields['detected_amounts'] = amounts[:15]  # Limit to reasonable number
        
        # Extract Box 12 codes
        box_12_codes = []
        for pattern in self.w2_field_patterns['box_12_codes']:
            matches = re.findall(pattern, table_text)
            for match in matches:
                if len(match) == 2:
                    try:
                        code, amount = match
                        box_12_codes.append({
                            'code': code,
                            'amount': float(amount.replace(',', ''))
                        })
                    except ValueError:
                        continue
        
        fields['box_12_codes'] = box_12_codes
        
        return fields

    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF to images for GPT Vision analysis
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Images
        """
        try:
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
            return images
        except Exception as e:
            print(f"PDF to image conversion failed: {e}")
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

    def analyze_with_gpt_vision(self, camelot_data: Dict[str, Any], pdf_image: Optional[Image.Image]) -> Dict[str, Any]:
        """
        Use GPT Vision to validate and enhance Camelot extraction
        
        Args:
            camelot_data: Data extracted by Camelot
            pdf_image: First page of PDF as image
            
        Returns:
            Enhanced data with GPT Vision analysis
        """
        try:
            # Prepare the prompt for GPT Vision
            prompt = self.create_gpt_vision_prompt(camelot_data)
            
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
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse the response
            gpt_response = response.choices[0].message.content
            enhanced_data = self.parse_gpt_response(gpt_response, camelot_data)
            
            return enhanced_data
            
        except Exception as e:
            print(f"GPT Vision analysis failed: {e}")
            # Fallback to Camelot data only
            return self.format_camelot_data_only(camelot_data)

    def create_gpt_vision_prompt(self, camelot_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive prompt for GPT Vision analysis
        
        Args:
            camelot_data: Data extracted by Camelot
            
        Returns:
            Formatted prompt string
        """
        return f"""
Analyze this W-2 tax document and extract ALL fields accurately. I have some preliminary data from table extraction below, but I need you to verify and complete the information by examining the image.

PRELIMINARY TABLE DATA:
{json.dumps(camelot_data, indent=2)}

Please extract and return a JSON object with the following structure:

{{
  "document_type": "W-2",
  "tax_year": "YYYY",
  "employee": {{
    "ssn": "XXX-XX-XXXX or masked format",
    "name": "Full Name",
    "address": {{
      "street": "Street Address",
      "city": "City",
      "state": "ST", 
      "zip": "12345"
    }}
  }},
  "employer": {{
    "ein": "XX-XXXXXXX",
    "name": "Company Name",
    "address": {{
      "street": "Street Address",
      "city": "City",
      "state": "ST",
      "zip": "12345"
    }},
    "control_number": "Control Number if present"
  }},
  "income_tax_info": {{
    "wages_tips_compensation": 0.00,
    "federal_income_tax_withheld": 0.00,
    "social_security_wages": 0.00,
    "social_security_tax_withheld": 0.00,
    "medicare_wages_tips": 0.00,
    "medicare_tax_withheld": 0.00,
    "social_security_tips": 0.00,
    "allocated_tips": 0.00,
    "dependent_care_benefits": 0.00,
    "nonqualified_plans": 0.00,
    "box_12_codes": [
      {{"code": "D", "amount": 0.00}}
    ],
    "statutory_employee": false,
    "retirement_plan": false,
    "third_party_sick_pay": false
  }},
  "state_local_info": [
    {{
      "state": "CA",
      "state_wages": 0.00,
      "state_income_tax": 0.00,
      "locality": "City Name",
      "local_wages": 0.00,
      "local_income_tax": 0.00
    }}
  ],
  "confidence_score": 0.95
}}

IMPORTANT INSTRUCTIONS:
1. Use the table data to guide you, but rely on the image for accuracy
2. Look for box numbers (1-20) on the form to identify fields correctly
3. Extract all monetary amounts as numbers (no $ signs or commas)
4. Handle SSN masking patterns like XXX-XX-1234 or *****1234
5. For Box 12, extract all codes (A, B, C, D, DD, W, etc.) with their amounts
6. Check boxes 13a-c for statutory employee, retirement plan, and third-party sick pay
7. Extract state/local information from boxes 15-20
8. Provide a confidence score based on data quality and completeness
9. Return ONLY the JSON object, no additional text

Focus on accuracy and completeness. If a field is not clearly visible, use null.
"""

    def parse_gpt_response(self, gpt_response: str, camelot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate GPT Vision response
        
        Args:
            gpt_response: Raw response from GPT Vision
            camelot_data: Original Camelot data for fallback
            
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
                    'gpt_vision_used': True,
                    'extraction_method': 'camelot_gpt_hybrid'
                }
                
                return parsed_data
            else:
                raise ValueError("No valid JSON found in GPT response")
                
        except Exception as e:
            print(f"Failed to parse GPT response: {e}")
            return self.format_camelot_data_only(camelot_data)

    def format_camelot_data_only(self, camelot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Camelot data into W-2 structure when GPT Vision fails
        
        Args:
            camelot_data: Raw Camelot extraction data
            
        Returns:
            Formatted W-2 data structure
        """
        raw_fields = camelot_data.get('raw_text_data', {})
        
        # Build basic structure from Camelot data
        w2_data = {
            "document_type": "W-2",
            "tax_year": None,
            "employee": {
                "ssn": raw_fields.get('employee_ssn'),
                "name": None,
                "address": None
            },
            "employer": {
                "ein": raw_fields.get('employer_ein'),
                "name": None,
                "address": None
            },
            "income_tax_info": {
                "box_12_codes": raw_fields.get('box_12_codes', [])
            },
            "state_local_info": [],
            "confidence_score": 0.6,  # Lower confidence without GPT Vision
            "processing_metadata": {
                'camelot_tables_found': camelot_data.get('table_count', 0),
                'gpt_vision_used': False,
                'extraction_method': 'camelot_only',
                'detected_amounts': raw_fields.get('detected_amounts', [])
            }
        }
        
        return w2_data

    def calculate_income(self, income_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate income information for mortgage approval
        
        Args:
            income_data: Income tax information from W-2
            
        Returns:
            Calculated income data
        """
        try:
            # Primary income from Box 1 (most important for mortgages)
            primary_income = income_data.get('wages_tips_compensation', 0) or 0
            social_security_wages = income_data.get('social_security_wages', 0) or 0
            medicare_wages = income_data.get('medicare_wages_tips', 0) or 0
            
            # Calculate additional benefits from Box 12
            box_12_codes = income_data.get('box_12_codes', [])
            additional_benefits = 0
            for code_info in box_12_codes:
                if isinstance(code_info, dict) and 'amount' in code_info:
                    additional_benefits += code_info.get('amount', 0) or 0
            
            # Use primary income (Box 1) as the main income for mortgage calculation
            annual_income = primary_income
            monthly_income = annual_income / 12 if annual_income > 0 else 0
            
            # Determine verification method
            verification_method = "box_1_wages"
            if primary_income == 0 and social_security_wages > 0:
                verification_method = "box_3_ss_wages"
                annual_income = social_security_wages
                monthly_income = annual_income / 12
            elif primary_income == 0 and medicare_wages > 0:
                verification_method = "box_5_medicare_wages"
                annual_income = medicare_wages
                monthly_income = annual_income / 12
            
            return {
                "primary_income": primary_income,
                "social_security_wages": social_security_wages,
                "medicare_wages": medicare_wages,
                "annual_income": annual_income,
                "monthly_income": round(monthly_income, 2),
                "income_verification_method": verification_method,
                "additional_benefits": additional_benefits if additional_benefits > 0 else None
            }
            
        except Exception as e:
            print(f"Income calculation failed: {e}")
            return {
                "primary_income": None,
                "social_security_wages": None,
                "medicare_wages": None,
                "annual_income": None,
                "monthly_income": None,
                "income_verification_method": "calculation_failed",
                "additional_benefits": None
            }

    def validate_and_format(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final validation and formatting of extracted data
        
        Args:
            raw_data: Raw extracted data
            
        Returns:
            Validated and formatted W-2 data
        """
        try:
            # Calculate income before validation
            income_data = raw_data.get('income_tax_info', {})
            calculated_income = self.calculate_income(income_data)
            raw_data['calculated_income'] = calculated_income
            
            # Use Pydantic model for validation
            w2_doc = W2Document(**raw_data)
            
            # Convert back to dict with proper formatting
            validated_data = w2_doc.model_dump(exclude_none=False)
            
            # Add final processing metadata
            if not validated_data.get('processing_metadata'):
                validated_data['processing_metadata'] = {}
            
            validated_data['processing_metadata'].update({
                'validation_passed': True,
                'validation_method': 'pydantic'
            })
            
            return validated_data
            
        except Exception as e:
            print(f"Validation failed: {e}")
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
    Example usage of the W-2 parser
    """
    import sys
    from pathlib import Path
    
    # Check if file path provided
    if len(sys.argv) < 2:
        print("Usage: python w2_camelot_parser.py <path_to_w2_pdf>")
        print("\nExample with sample files:")
        sample_files = Path("data/w2").glob("*.pdf") if Path("data/w2").exists() else []
        for sample in list(sample_files)[:3]:
            print(f"  python w2_camelot_parser.py {sample}")
        return
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    # Initialize parser
    parser = W2Parser()
    
    print(f"🔄 Parsing W-2 document: {Path(pdf_path).name}")
    print("=" * 50)
    
    # Parse the document
    import time
    start_time = time.time()
    
    result = parser.parse_pdf(pdf_path)
    
    processing_time = time.time() - start_time
    
    # Display results
    print(f"⏱️  Processing time: {processing_time:.2f} seconds")
    print(f"📊 Confidence score: {result.get('confidence_score', 'N/A')}")
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Extraction completed successfully!")
        
        # Print key extracted fields
        employee = result.get('employee', {})
        employer = result.get('employer', {})
        income = result.get('income_tax_info', {})
        calculated_income = result.get('calculated_income', {})
        
        print(f"\n📋 Key Information:")
        print(f"  Employee: {employee.get('name', 'N/A')}")
        print(f"  SSN: {employee.get('ssn', 'N/A')}")
        print(f"  Employer: {employer.get('name', 'N/A')}")
        print(f"  EIN: {employer.get('ein', 'N/A')}")
        wages = income.get('wages_tips_compensation', 0) or 0
        federal_tax = income.get('federal_income_tax_withheld', 0) or 0
        print(f"  Wages (Box 1): ${wages:,.2f}")
        print(f"  Federal Tax (Box 2): ${federal_tax:,.2f}")
        
        # Display calculated income for mortgage approval
        if calculated_income:
            annual_income = calculated_income.get('annual_income', 0) or 0
            monthly_income = calculated_income.get('monthly_income', 0) or 0
            method = calculated_income.get('income_verification_method', 'N/A')
            print(f"\n💰 Calculated Income for Mortgage:")
            print(f"  Annual Income: ${annual_income:,.2f}")
            print(f"  Monthly Income: ${monthly_income:,.2f}")
            print(f"  Verification Method: {method}")
            if calculated_income.get('additional_benefits'):
                print(f"  Additional Benefits: ${calculated_income['additional_benefits']:,.2f}")
    
    # Save results to data/w2/results directory
    results_dir = Path("data/w2/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output filename based on input file
    input_filename = Path(pdf_path).stem
    output_file = results_dir / f"{input_filename}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
