import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from pathlib import Path
import warnings
from typing import Dict, Tuple, List, Union
import logging

# --- File paths ---
BASE_PATH = Path(r"D:\DATA TILL DATE\Desktop\EBO FOLDER")
input_sales_path = BASE_PATH / "EBO SALES FOLDER" / "EBO SALES DATA.xlsx"
sku_master_path = BASE_PATH / "MASTERS" / "SKU MASTER.xlsx"
exclude_styles_path = BASE_PATH / "DT Exc Styles.xlsx"
output_excel_path = Path(r"D:\DATA TILL DATE\Desktop") / "SKU_Level_MRR_Without_Store.xlsx"

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
output_excel_path = BASE_PATH / "Jan_skuwise_projection.xlsx"

# --- Constants ---
FREEBIE_SKUS = [
    'MABOATPB3990', 'MAAIRPODS4999', 'MAPOWBANK3999',
    'MAAIRPODS3599', 'MATROLLEY9999', 'UAGY01BLK699', 'MAKRAFTBAGBIG',
    'MAKRAFTBAGSML', 'MATUMOFW299'  # Additional SKUs to exclude
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

def load_data_safely(file_path: Path, dtype_dict: Dict = None) -> pd.DataFrame:
    """Safely load data with proper error handling and dtype specifications."""
    try:
        df = pd.read_excel(file_path, dtype=dtype_dict)
        df.columns = df.columns.str.strip().str.upper()
        logging.info(f"Successfully loaded data from {file_path}")
        return df
    except Exception as e:
        logging.error(f"Error loading {file_path}: {str(e)}")
        raise

def exclude_freebies(df: pd.DataFrame, sku_column: str = 'SKU') -> pd.DataFrame:
    """Return df excluding known freebie SKUs with validation."""
    if sku_column not in df.columns:
        raise ValueError(f"Column {sku_column} not found in dataframe")
    return df[~df[sku_column].isin(FREEBIE_SKUS)].copy()

def get_last_n_months_ranges(max_date, n=4):
    """Return dictionary of last n months ranges {label:(start,end)}."""
    months = {}
    current = max_date.replace(day=1)
    for i in range(n):
        month_label = current.strftime("%b").upper()  # e.g., JUL
        start = current
        end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
        months[month_label] = (start, end)
        # Move one month back
        prev_month = current.month - 1 or 12
        prev_year = current.year if current.month > 1 else current.year - 1
        current = current.replace(year=prev_year, month=prev_month, day=1)
    return dict(reversed(months.items()))  # Keep chronological order

def analyze_growth_trends(df: pd.DataFrame) -> Dict:
    """Analyze sales growth trends and patterns."""
    mrr_cols = [col for col in df.columns if col.startswith('MRR_')]
    mrr_cols.sort()  # Ensure chronological order
    
    trends = {
        'growth_rates': [],
        'high_growth_styles': [],
        'declining_styles': [],
        'seasonal_patterns': {}
    }
    
    # Calculate month-over-month growth rates
    for i in range(1, len(mrr_cols)):
        prev_month = mrr_cols[i-1]
        curr_month = mrr_cols[i]
        
        # Overall growth rate
        growth_rate = ((df[curr_month].sum() - df[prev_month].sum()) / 
                      df[prev_month].sum() * 100)
        trends['growth_rates'].append({
            'period': f"{prev_month[-3:]} to {curr_month[-3:]}",
            'growth_rate': growth_rate
        })
        
        # Style-wise growth analysis
        style_growth = df.groupby('STYLE').agg({
            prev_month: 'sum',
            curr_month: 'sum'
        }).assign(
            growth_rate=lambda x: (x[curr_month] - x[prev_month]) / x[prev_month] * 100
        )
        
        # Identify high growth and declining styles
        high_growth = style_growth[style_growth.growth_rate > 50]
        declining = style_growth[style_growth.growth_rate < -30]
        
        if not high_growth.empty:
            trends['high_growth_styles'].append({
                'period': curr_month[-3:],
                'styles': high_growth.index.tolist()
            })
        
        if not declining.empty:
            trends['declining_styles'].append({
                'period': curr_month[-3:],
                'styles': declining.index.tolist()
            })
    
    return trends

def analyze_size_curves(df: pd.DataFrame) -> Dict:
    """Analyze size distribution patterns."""
    size_analysis = {
        'size_distribution': {},
        'irregular_patterns': [],
        'recommendations': []
    }
    
    # Calculate typical size distribution using REQ instead of QTY
    size_dist = df.groupby('SIZE MAP')['REQ'].sum()
    total_qty = size_dist.sum()
    if total_qty > 0:  # Avoid division by zero
        normal_dist = (size_dist / total_qty * 100).round(2)
        size_analysis['size_distribution'] = normal_dist.to_dict()
    
    # Analyze by style
    style_size_dist = df.pivot_table(
        index='STYLE',
        columns='SIZE MAP',
        values='REQ',
        aggfunc='sum',
        fill_value=0
    )
    
    # Convert to percentages
    row_sums = style_size_dist.sum(axis=1)
    style_size_pct = style_size_dist.div(row_sums, axis=0).fillna(0) * 100
    
    # Identify irregular patterns
    for style in style_size_pct.index:
        dist = style_size_pct.loc[style]
        
        # Check for missing sizes
        missing_sizes = dist[dist == 0].index.astype(str).tolist()
        if missing_sizes:
            size_analysis['irregular_patterns'].append({
                'style': style,
                'issue': f"Missing sizes: {', '.join(missing_sizes)}"
            })
        
        # Check for unusual distribution
        max_size = dist.idxmax()
        if dist[max_size] > 40:  # If any size is more than 40% of total
            size_analysis['irregular_patterns'].append({
                'style': style,
                'issue': f"Unusual concentration in size {max_size}: {dist[max_size]:.1f}%"
            })
    
    return size_analysis

def calculate_forward_planning_factors(target_date: datetime) -> Tuple[float, float, int]:
    """Calculate store growth, seasonal factors, and new stores for target date."""
    store_projections = CONFIG['STORE_PROJECTIONS']
    seasonal_factors = CONFIG['SEASONAL_FACTORS']
    new_stores = CONFIG['NEW_STORES_TIMELINE']
    
    current_stores = CONFIG['CURRENT_STORE_COUNT']
    target_month_key = target_date.strftime('%Y-%m')
    target_month = target_date.strftime('%b').upper()
    
    # Get projected store count
    projected_stores = store_projections.get(target_month_key, max(store_projections.values()))
    store_multiplier = projected_stores / current_stores
    
    # Get seasonal factor
    season_factor = seasonal_factors.get(target_month, 1.0)
    
    # Get new stores for the month
    new_stores_count = new_stores.get(target_month, 0)
    
    return store_multiplier, season_factor, new_stores_count

def validate_input_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """Validate input data quality and completeness and identify store column."""
    # Check required columns
    req_cols = ['BILL_DATE', 'BILL_QUANTITY', 'SKU']
    missing_cols = [col for col in req_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
    
    # Find store column
    store_col_options = ['STORE_CODE', 'STORE ID', 'STORECODE', 'STORE', 'LOCATION']
    store_col = None
    for col in store_col_options:
        if col in df.columns:
            store_col = col
            break
    
    if not store_col:
        logging.warning("No store column found. Using dummy store code.")
        df['STORE_CODE'] = 'STORE001'
        store_col = 'STORE_CODE'
    
    # Check for null values
    null_counts = df[req_cols].isnull().sum()
    if null_counts.any():
        logging.warning(f"Found null values in columns: \n{null_counts[null_counts > 0]}")
    
    # Check for negative quantities
    neg_qty = df[df['BILL_QUANTITY'] < 0]
    if not neg_qty.empty:
        logging.warning(f"Found {len(neg_qty)} records with negative quantities")
        
    return df, store_col

def calculate_mrr_all_stores(sales_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Calculate monthly MRRs and final MRR calculations with forward planning and validation."""
    try:
        df = sales_df.copy()
        df, store_col = validate_input_data(df)
        
        # Ensure store column is named correctly
        if store_col != 'STORE_CODE':
            df['STORE_CODE'] = df[store_col]

        # Performance optimization: Convert to datetime once
        df['DATE'] = pd.to_datetime(df['BILL_DATE'], errors='coerce')
        df.rename(columns={'BILL_QUANTITY': 'QTY'}, inplace=True)
        
        logging.info("Starting MRR calculations...")
        return process_mrr_calculations(df)
    except Exception as e:
        logging.error(f"Error in MRR calculations: {str(e)}")
        raise

def process_mrr_calculations(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Process MRR calculations with growth adjustment and store normalization."""
    logging.info("Processing MRR calculations...")
    
    # Ensure DATE column exists
    if 'DATE' not in df.columns:
        df['DATE'] = pd.to_datetime(df['BILL_DATE'], errors='coerce')
    
    # Get last 6 months dynamically for MRR calculation
    max_date = df['DATE'].max()
    month_defs = get_last_n_months_ranges(max_date, n=6)

    monthly_results = []
    store_counts = []
    
    for m, (start, end) in month_defs.items():
        month_sales = exclude_freebies(df[(df['DATE'] >= start) & (df['DATE'] <= end)])
        
        # Track store count progression
        store_count = month_sales['STORE_CODE'].nunique()
        store_counts.append({'month': m, 'store_count': store_count})
        
        # Calculate per-store metrics
        store_sales = month_sales.groupby(['SKU', 'STORE_CODE'])['QTY'].sum().reset_index()
        
        # Calculate average per store with growth adjustment
        store_avg = store_sales.groupby('SKU').agg(
            qty_sum=('QTY', 'sum'),
            store_count=('STORE_CODE', 'nunique')
        ).reset_index()
        
        # Adjust for growth trend
        months_old = len(month_defs) - list(month_defs.keys()).index(m)
        growth_factor = CONFIG['GROWTH_FACTOR'] ** (months_old / 12)  # Annualized growth
        
        store_avg[f'MRR_{m}'] = (
            (store_avg['qty_sum'] / store_avg['store_count']) * growth_factor
        ).fillna(0)
        
        monthly_results.append(store_avg[['SKU', f'MRR_{m}']])

    # Merge all months
    merged = monthly_results[0]
    for gr in monthly_results[1:]:
        merged = pd.merge(merged, gr, on='SKU', how='outer')

    merged.fillna(0, inplace=True)

    # Ensure numeric
    for col in merged.columns:
        if col.startswith("MRR_"):
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)

    # Best MRR (based on last 3 months except the earliest)
    last_months = list(month_defs.keys())[-3:]
    merged['BEST_MRR'] = merged[[f"MRR_{m}" for m in last_months]].max(axis=1)

    # New MRR calc (same logic as your version)
    merged['NEW_MRR'] = (merged['BEST_MRR'] / 9.0) * 2.0
    latest_month = list(month_defs.keys())[-1]
    merged[f'MRR_{latest_month}_FINAL'] = ((merged['BEST_MRR'] + merged['NEW_MRR']) * 1.2).round(0)

    # Forward planning calculations
    current_date = datetime.now()
    target_date = current_date + pd.DateOffset(months=4)  # 4 months lead time
    
    # Get store growth, seasonal factors and new stores count
    store_multiplier, season_factor, _ = calculate_forward_planning_factors(target_date)
    
    # Calculate requirements with forward planning factors
    merged['STORE_MULTIPLIER'] = store_multiplier
    merged['SEASONAL_FACTOR'] = season_factor
    merged['TARGET_MONTH'] = target_date.strftime('%b %Y')
    
    # Requirement calculation with forward planning
    merged['REQ'] = (
        merged['BEST_MRR'] *     # Base requirement
        store_multiplier *        # Store growth factor
        season_factor *          # Seasonal factor
        4 *                      # 4 months of stock
        1.3                      # Safety buffer
    ).round(0)
    
    # Add planning metadata
    merged['PLANNING_DATE'] = current_date.strftime('%Y-%m-%d')
    merged['EXPECTED_ARRIVAL'] = target_date.strftime('%Y-%m-%d')

    return merged, month_defs

# --- Helper Functions ---
def calculate_store_projections(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate projections with capacity constraints and seasonality."""
    projection_months = ['JAN', 'FEB', 'MAR', 'APR']
    result = df.copy()
    
    # Calculate store capacity per SKU (assuming even distribution)
    total_active_skus = len(df[df['BEST_MRR'] > 0])
    base_sku_capacity = CONFIG['STORE_CAPACITY'] / total_active_skus if total_active_skus > 0 else 0
    
    for month in projection_months:
        # Get planning factors
        _, season_factor, new_stores = calculate_forward_planning_factors(
            datetime.strptime(f"2026-{month}-01", "%Y-%b-%d")
        )
        
        # Sales projection for existing stores with seasonality and growth
        result[f'{month}_Sales_Proj'] = (
            result['BEST_MRR'] * 
            CONFIG['CURRENT_STORE_COUNT'] * 
            season_factor * 
            CONFIG['GROWTH_FACTOR']
        ).round(0)
        
        # New store allocation with ramp-up factor
        if new_stores > 0:
            # New stores start at 70% of mature store volume
            ramp_up_factor = 0.7
            result[f'{month}_New_Alloc'] = (
                result['BEST_MRR'] * 
                new_stores * 
                season_factor *
                ramp_up_factor *
                CONFIG['SAFETY_FACTOR']
            ).round(0)
        else:
            result[f'{month}_New_Alloc'] = 0
            
        # Apply capacity constraints
        result[f'{month}_Sales_Proj'] = result[f'{month}_Sales_Proj'].clip(0, base_sku_capacity)
        if new_stores > 0:
            result[f'{month}_New_Alloc'] = result[f'{month}_New_Alloc'].clip(0, base_sku_capacity)
            
        # Total for month
        result[f'{month}_Total'] = result[f'{month}_Sales_Proj'] + result[f'{month}_New_Alloc']
    
    # Calculate grand totals
    result['Total_Sales_Proj'] = sum(result[f'{m}_Sales_Proj'] for m in projection_months)
    result['Total_New_Alloc'] = sum(result[f'{m}_New_Alloc'] for m in projection_months)
    result['Grand_Total'] = result['Total_Sales_Proj'] + result['Total_New_Alloc']
    
    return result

def save_excel_with_analysis(
    final_mrr_df: pd.DataFrame,
    pivot: pd.DataFrame,
    pivot_style_colour: pd.DataFrame,
    filtered_mrr_df: pd.DataFrame,
    pivot_filtered: pd.DataFrame,
    output_path: Path
) -> None:
    """Save Excel with enhanced formatting and analysis sheets."""
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Create formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })
            number_format = workbook.add_format({'num_format': '#,##,##0'})
            percent_format = workbook.add_format({'num_format': '0.0%'})
            highlight_format = workbook.add_format({
                'bg_color': '#FFD700',
                'num_format': '#,##,##0'
            })
            
            # Write main data sheets
            sheets_data = {
                'SKU_MRR_Detail': final_mrr_df,
                'Pivot_Style_Code': pivot,
                'Pivot_Style_Colour': pivot_style_colour,
                'Filtered_MRR_No_ExcStyles': filtered_mrr_df,
                'Pivot_Filtered_No_ExcStyles': pivot_filtered
            }
            
            for sheet_name, data in sheets_data.items():
                data.to_excel(writer, sheet_name=sheet_name, index=(sheet_name.startswith('Pivot')))
                worksheet = writer.sheets[sheet_name]
                
                # Apply formats
                worksheet.set_row(0, None, header_format)
                worksheet.set_column('A:Z', 15, number_format)
                
                # Add conditional formatting
                if sheet_name in ['SKU_MRR_Detail', 'Filtered_MRR_No_ExcStyles']:
                    worksheet.conditional_format('J2:Z1048576', {
                        'type': 'cell',
                        'criteria': '>=',
                        'value': 1000,
                        'format': highlight_format
                    })
            
            # Add analysis sheets
            growth_trends = analyze_growth_trends(final_mrr_df)
            size_analysis = analyze_size_curves(filtered_mrr_df)
            
            # Growth Analysis Sheet
            growth_df = pd.DataFrame(growth_trends['growth_rates'])
            growth_df.to_excel(writer, sheet_name='Growth_Analysis', index=False)
            
            # Size Analysis Sheet
            size_dist_df = pd.DataFrame(size_analysis['size_distribution'].items(), 
                                      columns=['Size', 'Distribution %'])
            size_dist_df.to_excel(writer, sheet_name='Size_Analysis', index=False)
            
            # Planning Assumptions Sheet
            create_planning_assumptions_sheet(writer, final_mrr_df)
            
            # Apply Indian comma formatting for numeric columns
            for sheet in writer.sheets.values():
                for col in range(65, 91):  # A to Z
                    sheet.set_column(f'{chr(col)}:Z', 15, number_format)
            
        logging.info(f"Successfully saved Excel file to {output_path}")
    except Exception as e:
        logging.error(f"Error saving Excel file: {str(e)}")
        raise

def create_planning_assumptions_sheet(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
    """Create planning assumptions sheet with metadata."""
    current_date = datetime.now()
    target_date = current_date + pd.DateOffset(months=CONFIG['LEAD_TIME_MONTHS'])
    store_multiplier, season_factor, new_stores = calculate_forward_planning_factors(target_date)
    
    planning_data = {
        'Metric': [
            'Planning Date',
            'Expected Stock Arrival',
            'Current Store Count',
            'Projected Store Count',
            'Store Growth Multiplier',
            'Seasonal Factor',
            'Months Stock',
            'Safety Factor',
            'Total Styles Planned',
            'Total SKUs Planned',
            'Average MRR',
            'Total Requirement',
            'Target Month',
            'Growth Notes'
        ],
        'Value': [
            current_date.strftime('%Y-%m-%d'),
            target_date.strftime('%Y-%m-%d'),
            CONFIG['CURRENT_STORE_COUNT'],
            int(CONFIG['CURRENT_STORE_COUNT'] * store_multiplier),
            store_multiplier,
            season_factor,
            CONFIG['MONTHS_STOCK'],
            CONFIG['SAFETY_FACTOR'],
            df['STYLE'].nunique(),
            len(df),
            df['BEST_MRR'].mean().round(2),
            df['REQ'].sum().round(0),
            target_date.strftime('%b %Y'),
            f"Planning for {target_date.strftime('%b %Y')} with projected store count growing from {CONFIG['CURRENT_STORE_COUNT']} to {int(CONFIG['CURRENT_STORE_COUNT'] * store_multiplier)}"
        ]
    }
    
    assumptions_df = pd.DataFrame(planning_data)
    assumptions_df.to_excel(writer, sheet_name='Planning_Assumptions', index=False)

# ------------------- MAIN SCRIPT -------------------

def main():
    try:
        # Load sales data
        logging.info("Loading sales data...")
        sales_df = load_data_safely(input_sales_path, DTYPE_SPECS)

        # Calculate MRR
        logging.info("Calculating MRR...")
        final_mrr_df, month_defs = calculate_mrr_all_stores(sales_df)
        
        # Load SKU Master & clean duplicates
        logging.info("Loading SKU master data...")
        sku_master_df = load_data_safely(sku_master_path, DTYPE_SPECS)
        sku_master_df = sku_master_df.loc[:, ~sku_master_df.columns.duplicated()]

        # Ensure all needed columns exist in SKU master
        columns_to_merge = ['SKU', 'STYLE', 'COLOUR', 'SIZE']
        for c in columns_to_merge:
            if c not in sku_master_df.columns:
                sku_master_df[c] = pd.NA

        # Merge SKU info
        logging.info("Merging SKU master data...")
        final_mrr_df = final_mrr_df.merge(sku_master_df[columns_to_merge], on='SKU', how='left')

        # 3-month avg MRR
        last_3 = list(month_defs.keys())[-3:]
        for m in last_3:
            col = f"MRR_{m}"
            if col not in final_mrr_df.columns:
                final_mrr_df[col] = 0
        final_mrr_df['AVG_MRR_3M'] = final_mrr_df[[f"MRR_{m}" for m in last_3]].mean(axis=1).round(2)

        # DRR per month (vectorized)
        for m in last_3:
            month_col = f"MRR_{m}"
            drr_col = f"DRR_{m}"
            final_mrr_df[drr_col] = np.where(final_mrr_df[month_col] > 0,
                                          final_mrr_df['REQ'] / final_mrr_df[month_col],
                                          0)

        # Best DRR
        drr_cols = [f"DRR_{m}" for m in last_3]
        final_mrr_df['BEST_DRR'] = final_mrr_df[drr_cols].max(axis=1).round(2)

        # Order columns
        projection_months = ['JAN', 'FEB', 'MAR', 'APR']
        projection_cols = []
        for month in projection_months:
            projection_cols.extend([f'{month}_Sales_Proj', f'{month}_New_Alloc', f'{month}_Total'])
        projection_cols.extend(['Total_Sales_Proj', 'Total_New_Alloc', 'Grand_Total'])
        
        ordered_columns = (
            ['SKU', 'STYLE', 'CODE', 'STYLE*CODE', 'STYLE COLOUR', 'COLOUR', 'SIZE', 'SIZE MAP', 'SIZE NUM'] +
            [f"MRR_{m}" for m in month_defs.keys()] +
            [f"MRR_{list(month_defs.keys())[-1]}_FINAL", 'AVG_MRR_3M', 'BEST_MRR', 'BEST_DRR', 'REQ'] +
            projection_cols
        )
        for c in ordered_columns:
            if c not in final_mrr_df.columns:
                final_mrr_df[c] = pd.NA
        final_mrr_df = final_mrr_df[ordered_columns]

        # Create pivots
        logging.info("Creating pivot tables...")
        pivot = pd.pivot_table(
            final_mrr_df,
            index=['STYLE', 'CODE', 'STYLE*CODE'],
            columns='SIZE MAP',
            values='REQ',
            aggfunc='sum',
            fill_value=0,
            margins=True,
            margins_name='Grand Total'
        )

        pivot_style_colour = pd.pivot_table(
            final_mrr_df,
            index=['STYLE', 'STYLE COLOUR'],
            values=['REQ', 'AVG_MRR_3M', 'BEST_MRR', 'BEST_DRR'],
            aggfunc={'REQ':'sum', 'AVG_MRR_3M':'mean', 'BEST_MRR':'mean', 'BEST_DRR':'mean'},
            fill_value=0,
            margins=True,
            margins_name='Grand Total'
        )

        # Handle excluded styles
        logging.info("Processing excluded styles...")
        try:
            exclude_styles_df = load_data_safely(exclude_styles_path)
            exclude_styles_list = exclude_styles_df['STYLE'].astype(str).str.strip().str.upper().tolist()
        except Exception as e:
            logging.warning(f"Could not load excluded styles: {str(e)}")
            exclude_styles_list = []

        filtered_mrr_df = final_mrr_df[
            ~final_mrr_df['STYLE'].astype(str).str.strip().str.upper().isin(exclude_styles_list)
        ].copy()

        pivot_filtered = pd.pivot_table(
            filtered_mrr_df,
            index=['STYLE', 'CODE', 'STYLE*CODE'],
            columns='SIZE MAP',
            values='REQ',
            aggfunc='sum',
            fill_value=0,
            margins=True,
            margins_name='Grand Total'
        )

        # Select and calculate required columns
        logging.info("Preparing simplified output...")
        
        # Get required MRR columns
        mrr_columns = ['MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP']
        
        # Create the simplified dataframe
        simplified_df = final_mrr_df[['SKU', 'STYLE', 'COLOUR', 'SIZE']].copy()
        
        # Add individual month MRRs
        for month in mrr_columns:
            col = f'MRR_{month}'
            if col in final_mrr_df.columns:
                simplified_df[f'{month.title()} MRR'] = final_mrr_df[col]
            else:
                simplified_df[f'{month.title()} MRR'] = 0
                
        # Add Best MRR at the end
        simplified_df['BEST MRR'] = final_mrr_df['BEST_MRR']
        
        # Calculate Jan projection
        simplified_df['Jan Projection'] = simplified_df['BEST MRR'] * 3 * 3 * 1.3
        
        # Save to Excel
        logging.info("Saving simplified output...")
        simplified_df.to_excel(output_excel_path, index=False, sheet_name='MRR Analysis')
        
        logging.info(f"✅ Output saved to: {output_excel_path}")
        
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()


