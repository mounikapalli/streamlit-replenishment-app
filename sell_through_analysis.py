import pandas as pd
import numpy as np
import polars as pl
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def load_data(received_path, sales_path, rtv_path, sku_master_path, style_master_path):
    """Load all required data files"""
    try:
        # Use polars for faster data loading
        received_df = pl.read_excel(received_path).to_pandas()
        sales_df = pl.read_excel(sales_path).to_pandas()
        rtv_df = pl.read_excel(rtv_path).to_pandas()
        sku_master = pl.read_excel(sku_master_path).to_pandas()
        style_master = pl.read_excel(style_master_path).to_pandas()
        
        return received_df, sales_df, rtv_df, sku_master, style_master
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return None

def preprocess_data(df, date_column):
    """Preprocess dataframes to ensure consistent format"""
    try:
        # Convert date columns
        df[date_column] = pd.to_datetime(df[date_column])
        return df
    except Exception as e:
        print(f"Error preprocessing data: {str(e)}")
        return df

def calculate_sku_sell_through(received_df, sales_df, rtv_df):
    """Calculate sell-through at SKU level"""
    try:
        # Aggregate quantities by SKU
        received_qty = received_df.groupby('SKU')['QTY'].sum().reset_index()
        sales_qty = sales_df.groupby('SKU')['QTY'].sum().reset_index()
        rtv_qty = rtv_df.groupby('SKU')['QTY'].sum().reset_index()
        
        # Merge all quantities
        sell_through = received_qty.merge(sales_qty, on='SKU', how='left', suffixes=('_received', '_sold'))
        sell_through = sell_through.merge(rtv_qty, on='SKU', how='left', suffixes=('', '_rtv'))
        
        # Fill NaN values with 0
        sell_through = sell_through.fillna(0)
        
        # Calculate sell-through percentage
        sell_through['Net_Qty'] = sell_through['QTY_received'] - sell_through['QTY_rtv']
        sell_through['Sell_Through_Pct'] = np.where(
            sell_through['Net_Qty'] > 0,
            (sell_through['QTY_sold'] / sell_through['Net_Qty']) * 100,
            0
        )
        
        return sell_through
        
    except Exception as e:
        print(f"Error calculating SKU sell-through: {str(e)}")
        return None

def calculate_style_sell_through(sku_sell_through, sku_master):
    """Calculate sell-through at Style level"""
    try:
        # Merge SKU sell-through with SKU master to get style information
        style_data = sku_sell_through.merge(sku_master[['SKU', 'STYLE']], on='SKU', how='left')
        
        # Aggregate by style
        style_sell_through = style_data.groupby('STYLE').agg({
            'QTY_received': 'sum',
            'QTY_sold': 'sum',
            'QTY_rtv': 'sum',
            'Net_Qty': 'sum'
        }).reset_index()
        
        # Calculate style level sell-through
        style_sell_through['Sell_Through_Pct'] = np.where(
            style_sell_through['Net_Qty'] > 0,
            (style_sell_through['QTY_sold'] / style_sell_through['Net_Qty']) * 100,
            0
        )
        
        return style_sell_through
        
    except Exception as e:
        print(f"Error calculating style sell-through: {str(e)}")
        return None

def add_insights(sell_through_df):
    """Add performance insights based on sell-through percentage"""
    try:
        conditions = [
            (sell_through_df['Sell_Through_Pct'] >= 80),
            (sell_through_df['Sell_Through_Pct'] >= 60) & (sell_through_df['Sell_Through_Pct'] < 80),
            (sell_through_df['Sell_Through_Pct'] >= 40) & (sell_through_df['Sell_Through_Pct'] < 60),
            (sell_through_df['Sell_Through_Pct'] < 40)
        ]
        
        choices = ['High Performer', 'Good Performer', 'Average Performer', 'Slow Mover']
        
        sell_through_df['Performance_Category'] = np.select(conditions, choices, default='Unknown')
        return sell_through_df
        
    except Exception as e:
        print(f"Error adding insights: {str(e)}")
        return sell_through_df

def export_results(sku_sell_through, style_sell_through, output_path):
    """Export results to Excel with multiple sheets"""
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Sort by sell-through percentage descending
            sku_sell_through.sort_values('Sell_Through_Pct', ascending=False).to_excel(
                writer, sheet_name='SKU_Sell_Through', index=False
            )
            style_sell_through.sort_values('Sell_Through_Pct', ascending=False).to_excel(
                writer, sheet_name='Style_Sell_Through', index=False
            )
            
            # Create summary pivot
            summary = pd.DataFrame({
                'Performance_Category': ['High Performer', 'Good Performer', 'Average Performer', 'Slow Mover'],
                'SKU_Count': [
                    len(sku_sell_through[sku_sell_through['Performance_Category'] == 'High Performer']),
                    len(sku_sell_through[sku_sell_through['Performance_Category'] == 'Good Performer']),
                    len(sku_sell_through[sku_sell_through['Performance_Category'] == 'Average Performer']),
                    len(sku_sell_through[sku_sell_through['Performance_Category'] == 'Slow Mover'])
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
            
        print(f"Results exported to {output_path}")
        
    except Exception as e:
        print(f"Error exporting results: {str(e)}")

def main():
    # File paths - update these with your actual file paths
    received_path = "path_to_received_data.xlsx"
    sales_path = "path_to_sales_data.xlsx"
    rtv_path = "path_to_rtv_data.xlsx"
    sku_master_path = "path_to_sku_master.xlsx"
    style_master_path = "path_to_style_master.xlsx"
    output_path = "sell_through_analysis_results.xlsx"
    
    # Load data
    print("Loading data...")
    data = load_data(received_path, sales_path, rtv_path, sku_master_path, style_master_path)
    if data is None:
        return
        
    received_df, sales_df, rtv_df, sku_master, style_master = data
    
    # Calculate SKU level sell-through
    print("Calculating SKU level sell-through...")
    sku_sell_through = calculate_sku_sell_through(received_df, sales_df, rtv_df)
    if sku_sell_through is not None:
        sku_sell_through = add_insights(sku_sell_through)
    
    # Calculate Style level sell-through
    print("Calculating Style level sell-through...")
    style_sell_through = calculate_style_sell_through(sku_sell_through, sku_master)
    if style_sell_through is not None:
        style_sell_through = add_insights(style_sell_through)
    
    # Export results
    print("Exporting results...")
    export_results(sku_sell_through, style_sell_through, output_path)

if __name__ == "__main__":
    main()