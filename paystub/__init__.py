"""
Paystub Parser Module

This module contains all paystub-related parsing functionality including:
- PaystubParser: Main generic paystub document parser
- Data models and validation logic
- Multi-modal processing pipeline
"""

from .paystub_parser import PaystubParser, PaystubData, EmployerInfo, EmployeeInfo, PayrollPeriod, EarningsDetail, DeductionDetail, TaxDetail, AddressModel

__all__ = [
    'PaystubParser',
    'PaystubData',
    'EmployerInfo',
    'EmployeeInfo', 
    'PayrollPeriod',
    'EarningsDetail',
    'DeductionDetail',
    'TaxDetail',
    'AddressModel'
]

__version__ = "1.0.0"







