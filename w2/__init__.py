"""
W-2 Parser Module

This module contains all W-2 related parsing functionality including:
- W2Parser: Main W-2 document parser
- W2Dashboard: Streamlit dashboard for W-2 review
- Data models and validation logic
"""

from .w2_parser import W2Parser, W2Document, EmployeeInfo, EmployerInfo, IncomeTaxInfo, StateLocalInfo, CalculatedIncome, AddressModel, Box12Code

__all__ = [
    'W2Parser',
    'W2Document', 
    'EmployeeInfo',
    'EmployerInfo',
    'IncomeTaxInfo',
    'StateLocalInfo',
    'CalculatedIncome',
    'AddressModel',
    'Box12Code'
]

__version__ = "1.0.0"
