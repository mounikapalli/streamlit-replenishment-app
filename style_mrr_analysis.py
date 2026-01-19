import pandas as pd
from pathlib import Path

# File path for sales data
SALES_FILE = r"D:\DATA TILL DATE\Desktop\EBO FOLDER\EBO SALES FOLDER\EBO SALES DATA.xlsx"

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
        print(f"Error loading data: {str(e)}")
        return None

def create_mrr_analysis(df):
    """Create monthly sales (MRR) analysis for each style"""
    try:
        # Filter for April to September 2025
        start_date = pd.Timestamp('2025-04-01')
        end_date = pd.Timestamp('2025-09-30')
        mask = (df['BILL_DATE'] >= start_date) & (df['BILL_DATE'] <= end_date)
        df_filtered = df[mask].copy()
        
        # Add month name for grouping
        df_filtered['Month'] = df_filtered['BILL_DATE'].dt.strftime('%B')
        
        # Create pivot table with monthly quantities
        mrr_pivot = pd.pivot_table(
            df_filtered,
            values='BILL_QUANTITY',
            index='STYLE',
            columns='Month',
            aggfunc='sum',
            fill_value=0
        )
        
        # Ensure all months are present in correct order
        desired_months = ['April', 'May', 'June', 'July', 'August', 'September']
        for month in desired_months:
            if month not in mrr_pivot.columns:
                mrr_pivot[month] = 0
        
        # Reorder columns
        mrr_pivot = mrr_pivot[desired_months]
        
        # Calculate best MRR (highest monthly quantity)
        mrr_pivot['Best MRR'] = mrr_pivot[desired_months].max(axis=1)
        
        # Sort by Best MRR
        mrr_pivot = mrr_pivot.sort_values('Best MRR', ascending=False)
        
        return mrr_pivot
        
    except Exception as e:
        print(f"Error creating MRR analysis: {str(e)}")
        return None

def export_to_excel(mrr_pivot):
    """Export MRR analysis to Excel"""
    try:
        # Create Excel writer
        output_file = r'D:\DATA TILL DATE\Desktop\Style_MRR_Analysis_2025.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write MRR analysis
            mrr_pivot.to_excel(writer, sheet_name='Style MRR Analysis')
            
            # Format sheet
            worksheet = writer.sheets['Style MRR Analysis']
            
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
    df = load_sales_data()
    if df is None:
        return
    
    # Create MRR analysis
    print("Creating MRR analysis...")
    mrr_pivot = create_mrr_analysis(df)
    
    if mrr_pivot is None:
        return
    
    # Export results
    print("Exporting results...")
    export_to_excel(mrr_pivot)
    
    print("Analysis completed!")

if __name__ == "__main__":
    main()