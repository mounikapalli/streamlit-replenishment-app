import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from pathlib import Path
import warnings
from typing import Dict, Tuple, List, Union
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Configuration ---
CONFIG = {
    'CURRENT_STORE_COUNT': 45,  # Current operational stores
    'STORE_CAPACITY': 9000,     # Standard store capacity
    'STORE_AREA': 2000,        # Standard store area (sq ft)
    'LEAD_TIME_MONTHS': 4,
    'MONTHS_STOCK': 4,
    'SAFETY_FACTOR': 1.3,
    'MIN_MONTHS_HISTORY': 3,
    'GROWTH_FACTOR': 1.1,      # 10% natural growth in existing stores
    'NEW_STORES_TIMELINE': {
        'JAN': 5,   # 5 new stores in January
        'FEB': 5,   # 5 new stores in February
        'MAR': 5,   # 5 new stores in March
        'APR': 0    # No new stores in April
    },
    'STORE_PROJECTIONS': {
        '2026-01': 50,  # 45 + 5 new stores
        '2026-02': 55,  # 50 + 5 new stores
        '2026-03': 60,  # 55 + 5 new stores
        '2026-04': 60   # No new stores
    },
    'SEASONAL_FACTORS': {
        'JAN': 1.4,  # High season (festive/walking period)
        'FEB': 0.8,  # Decline period
        'MAR': 1.2,  # Recovery/increase
        'APR': 1.0,  # Normal baseline
        'MAY': 0.9,
        'JUN': 0.8,
        'JUL': 0.9,
        'AUG': 1.1,
        'SEP': 1.2,
        'OCT': 1.3,
        'NOV': 1.4,
        'DEC': 1.5   # Peak season
    }
}

# --- File paths ---
BASE_PATH = Path(r"D:\DATA TILL DATE\Desktop\EBO FOLDER")
input_sales_path = BASE_PATH / "EBO SALES FOLDER" / "EBO SALES DATA.xlsx"
sku_master_path = BASE_PATH / "MASTERS" / "SKU MASTER.xlsx"
exclude_styles_path = BASE_PATH / "DT Exc Styles.xlsx"
output_excel_path = Path(r"D:\DATA TILL DATE\Desktop") / "SKU_Level_MRR_Without_Store.xlsx"

# --- Constants ---
FREEBIE_SKUS = [
    'MABOATPB3990', 'MAAIRPODS4999', 'MAPOWBANK3999',
    'MAAIRPODS3599', 'MATROLLEY9999', 'UAGY01BLK699', 'MAKRAFTBAGBIG'
]

DTYPE_SPECS = {
    'SKU': str,
    'STYLE': str,
    'CODE': str,
    'COLOUR': str,
    'SIZE': str,
    'SIZE MAP': str,
    'SIZE NUM': str,
    'BILL_QUANTITY': float
}