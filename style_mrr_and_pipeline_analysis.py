import pandas as pd
from pathlib import Path

# File paths
SALES_FILE = r"D:\DATA TILL DATE\Desktop\EBO FOLDER\EBO SALES FOLDER\EBO SALES DATA.xlsx"
PIPELINE_FILE = r"D:\DATA TILL DATE\Downloads\Pipeline of styles till dec.xlsx"

def load_sales_data():
    """Load and prepare sales data for analysis"""
    try:
        # Read the Excel file
        df = pd.read_excel(SALES_FILE)
        
        # Convert date column to datetime if not already
        if 'BILL_DATE' in df.columns:
            df['BILL_DATE'] = pd.to_datetime(df['BILL_DATE'])
        elif 'DATE' in df.columns:
            df['BILL_DATE'] = pd.to_datetime(df['DATE'])
        else:
            raise ValueError("No date column found in the data")
            
        return df
        
    except Exception as e:
        print(f"Error loading sales data: {str(e)}")
        return None

def load_pipeline_data():
    """Load pipeline data"""
    try:
        # Read the pipeline Excel file
        df = pd.read_excel(PIPELINE_FILE)
        return df
    except Exception as e:
        print(f"Error loading pipeline data: {str(e)}")
        return None

def create_mrr_analysis(df):
    """Create monthly sales (MRR) analysis for each style including Oct, Nov, Dec"""
    try:
        # Filter for April to December 2025
        start_date = pd.Timestamp('2025-04-01')
        end_date = pd.Timestamp('2025-12-31')
        mask = (df['BILL_DATE'] >= start_date) & (df['BILL_DATE'] <= end_date)
        df_filtered = df[mask].copy()
        
        # Add month name and month number for grouping
        df_filtered['Month_Name'] = df_filtered['BILL_DATE'].dt.strftime('%B')
        df_filtered['Month_Num'] = df_filtered['BILL_DATE'].dt.month
        
        # Create pivot table with monthly quantities
        mrr_pivot = pd.pivot_table(
            df_filtered,
            values='BILL_QUANTITY',
            index='STYLE',
            columns='Month_Name',
            aggfunc='sum',
            fill_value=0
        )
        
        # Ensure all months are present in correct order
        desired_months = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        for month in desired_months:
            if month not in mrr_pivot.columns:
                mrr_pivot[month] = 0
        
        # Reorder columns
        mrr_pivot = mrr_pivot[desired_months]
        
        # Calculate best MRR (highest monthly quantity)
        mrr_pivot['Best_MRR'] = mrr_pivot[desired_months].max(axis=1)
        
        # Add month-wise analysis info
        for i, style in enumerate(mrr_pivot.index):
            style_data = df_filtered[df_filtered['STYLE'] == style]
            for month in desired_months:
                month_data = style_data[style_data['Month_Name'] == month]
                if len(month_data) > 0:
                    # Keep the quantity sum we already have from pivot
                    pass
        
        return mrr_pivot
        
    except Exception as e:
        print(f"Error creating MRR analysis: {str(e)}")
        return None

def create_pipeline_pivot(df):
    """Create pivot table for pipeline data with Oct to May months"""
    try:
        # Make a copy
        df_copy = df.copy()
        
        # Clean and standardize month names
        df_copy['Month_Name'] = df_copy['Month'].str.strip().str.upper()
        
        # Map full month names to abbreviations if needed
        month_mapping = {
            'JANUARY': 'JAN',
            'FEBRUARY': 'FEB',
            'MARCH': 'MAR',
            'APRIL': 'APR',
            'MAY': 'MAY',
            'JUNE': 'JUN',
            'JULY': 'JUL',
            'AUGUST': 'AUG',
            'SEPTEMBER': 'SEP',
            'OCTOBER': 'OCT',
            'NOVEMBER': 'NOV',
            'DECEMBER': 'DEC'
        }
        
        df_copy['Month_Name'] = df_copy['Month_Name'].map(lambda x: month_mapping.get(x, x))
        
        # Drop rows with missing EBO PICKUP values or invalid months
        df_copy = df_copy.dropna(subset=['EBO PICKUP'])
        df_copy = df_copy[~df_copy['Month_Name'].isin(['NAN', 'DEL MONTH AS PER MANF PLAN'])]
        
        # Create pivot table for EBO PICKUP
        pipeline_pivot = pd.pivot_table(
            df_copy,
            values='EBO PICKUP',
            index='Style',
            columns='Month_Name',
            aggfunc='sum',
            fill_value=0
        )
        
        # Define the months in order (Oct to May)
        desired_months = ['OCT', 'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY']
        
        # Ensure all months are present
        for month in desired_months:
            if month not in pipeline_pivot.columns:
                pipeline_pivot[month] = 0
        
        # Reorder columns to Oct-May sequence, keeping only available months
        available_months = [m for m in desired_months if m in pipeline_pivot.columns]
        pipeline_pivot = pipeline_pivot[available_months]
        
        # Add total pipeline column
        pipeline_pivot['Total_Pipeline'] = pipeline_pivot[available_months].sum(axis=1)
        
        return pipeline_pivot
        
    except Exception as e:
        print(f"Error creating pipeline pivot: {str(e)}")
        return None

def merge_analysis(mrr_pivot, pipeline_pivot):
    """Merge MRR and pipeline analysis"""
    try:
        # Reset index to make Style a column for merging
        mrr_df = mrr_pivot.reset_index()
        pipeline_df = pipeline_pivot.reset_index()
        
        # Rename Style column in pipeline data to match sales data
        pipeline_df = pipeline_df.rename(columns={'Style': 'STYLE'})
        
        # Merge the dataframes on STYLE
        merged_df = pd.merge(mrr_df, pipeline_df, on='STYLE', how='outer', suffixes=('_Sales', ''))
        
        # Fill NaN values with 0
        merged_df = merged_df.fillna(0)
        
        # Sort by Best_MRR
        merged_df = merged_df.sort_values('Best_MRR', ascending=False)
        
        return merged_df
        
    except Exception as e:
        print(f"Error merging analysis: {str(e)}")
        return None

def export_to_excel(merged_df):
    """Export merged analysis to Excel"""
    try:
        # Create Excel writer
        output_file = r'D:\DATA TILL DATE\Desktop\Style_MRR_and_Pipeline_Analysis_2025.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write merged analysis
            merged_df.to_excel(writer, sheet_name='Style Analysis', index=False)
            
            # Format sheet
            worksheet = writer.sheets['Style Analysis']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        print(f"Analysis exported to {output_file}")
        
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")

def main():
    # Load sales data
    print("Loading sales data...")
    sales_df = load_sales_data()
    if sales_df is None:
        return
    
    # Create MRR analysis
    print("Creating MRR analysis...")
    mrr_pivot = create_mrr_analysis(sales_df)
    if mrr_pivot is None:
        return
    
    # Load pipeline data
    print("Loading pipeline data...")
    pipeline_df = load_pipeline_data()
    if pipeline_df is None:
        return
    
    # Create pipeline pivot
    print("Creating pipeline analysis...")
    pipeline_pivot = create_pipeline_pivot(pipeline_df)
    if pipeline_pivot is None:
        return
    
    # Merge analyses
    print("Merging analyses...")
    merged_analysis = merge_analysis(mrr_pivot, pipeline_pivot)
    if merged_analysis is None:
        return
    
    # Export results
    print("Exporting results...")
    export_to_excel(merged_analysis)
    
    print("Analysis completed!")

if __name__ == "__main__":
    main()