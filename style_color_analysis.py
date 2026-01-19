import pandas as pd
from pathlib import Path

# File paths
SALES_FILE = r"D:\DATA TILL DATE\Desktop\EBO FOLDER\EBO SALES FOLDER\EBO SALES DATA.xlsx"
APPROVED_COLORS_FILE = r"D:\DATA TILL DATE\Downloads\Colour list for jan.xlsx"

def load_approved_colors():
    """Load approved color list"""
    try:
        # Read the Excel file with approved colors
        df = pd.read_excel(APPROVED_COLORS_FILE)
        
        # Get the color codes as a list
        if 'COLOR CODE' in df.columns:
            return df['COLOR CODE'].unique().tolist()
        else:
            # Try alternative column names
            color_columns = [col for col in df.columns if 'COLOR' in col.upper()]
            if color_columns:
                return df[color_columns[0]].unique().tolist()
            else:
                raise ValueError("No color code column found in the approved colors file")
            
    except Exception as e:
        print(f"Error loading approved colors: {str(e)}")
        return None

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

def create_approved_color_analysis(df, approved_colors):
    """Create style-color analysis with only approved colors arranged by sales quantity"""
    try:
        # Filter data to include only approved colors
        df_approved = df[df['COLOR CODE'].isin(approved_colors)].copy()
        
        # Group by style and color to get total quantities
        style_color_totals = df_approved.groupby(['STYLE', 'COLOR CODE'])['BILL_QUANTITY'].sum().reset_index()
        
        # Create a list to store formatted data
        result_data = []
        
        # Process each style
        for style in style_color_totals['STYLE'].unique():
            # Get data for this style
            style_data = style_color_totals[style_color_totals['STYLE'] == style].copy()
            
            # Sort colors by quantity for this style
            style_data = style_data.sort_values('BILL_QUANTITY', ascending=False)
            
            # Create row for this style
            row = {'STYLE': style}
            
            # Add approved colors and their quantities
            for i, (_, color_row) in enumerate(style_data.iterrows(), 1):
                row[f'Color {i}'] = color_row['COLOR CODE']
                row[f'Qty {i}'] = color_row['BILL_QUANTITY']
            
            # Add total quantity for sorting
            row['Total Quantity'] = style_data['BILL_QUANTITY'].sum()
            
            result_data.append(row)
        
        # Convert to DataFrame
        result_df = pd.DataFrame(result_data)
        
        # Sort by total quantity
        result_df = result_df.sort_values('Total Quantity', ascending=False)
        
        return result_df
        
    except Exception as e:
        print(f"Error creating approved color analysis: {str(e)}")
        return None

def create_style_color_analysis(df):
    """Create style-color analysis with all colors arranged by sales quantity"""
    try:
        # Group by style and color to get total quantities
        style_color_totals = df.groupby(['STYLE', 'COLOR CODE'])['BILL_QUANTITY'].sum().reset_index()
        
        # Create a list to store formatted data
        result_data = []
        
        # Process each style
        for style in style_color_totals['STYLE'].unique():
            # Get data for this style
            style_data = style_color_totals[style_color_totals['STYLE'] == style].copy()
            
            # Sort colors by quantity for this style
            style_data = style_data.sort_values('BILL_QUANTITY', ascending=False)
            
            # Create row for this style
            row = {'STYLE': style}
            
            # Add all colors and their quantities
            for i, (_, color_row) in enumerate(style_data.iterrows(), 1):
                row[f'Color {i}'] = color_row['COLOR CODE']
                row[f'Qty {i}'] = color_row['BILL_QUANTITY']
            
            # Add total quantity for sorting
            row['Total Quantity'] = style_data['BILL_QUANTITY'].sum()
            
            result_data.append(row)
        
        # Convert to DataFrame
        result_df = pd.DataFrame(result_data)
        
        # Sort by total quantity
        result_df = result_df.sort_values('Total Quantity', ascending=False)
        
        return result_df
        
    except Exception as e:
        print(f"Error creating style-color analysis: {str(e)}")
        return None

def export_to_excel(all_colors_df, approved_colors_df):
    """Export analyses to Excel"""
    try:
        # Create Excel writer
        output_file = r'D:\DATA TILL DATE\Desktop\Style_Color_Analysis_All.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write all colors analysis
            all_colors_df.to_excel(writer, sheet_name='All Colors Analysis', index=False)
            
            # Write approved colors analysis
            approved_colors_df.to_excel(writer, sheet_name='Approved Colors Analysis', index=False)
            
            # Format sheets
            for sheet_name in ['All Colors Analysis', 'Approved Colors Analysis']:
                worksheet = writer.sheets[sheet_name]
            
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

def create_style_monthly_quantity_analysis(df, start_month=6, end_month=10):
    """Create style-level monthly quantity analysis from June to October for demand planning"""
    try:
        # Filter data for the specified months (assuming current year)
        df['Month'] = df['BILL_DATE'].dt.month
        df['Year'] = df['BILL_DATE'].dt.year
        
        # Get the most recent year with data
        max_year = df['Year'].max()
        
        # Filter for specified months in the latest year
        month_filter = (df['Month'] >= start_month) & (df['Month'] <= end_month) & (df['Year'] == max_year)
        df_filtered = df[month_filter].copy()
        
        if df_filtered.empty:
            print(f"No data found for months {start_month}-{end_month} in year {max_year}")
            return None
        
        # Calculate monthly quantities for demand planning
        monthly_style_qty = df_filtered.groupby(['STYLE', 'Month'])['BILL_QUANTITY'].sum().reset_index()
        
        # Pivot to get months as columns
        pivot_qty = monthly_style_qty.pivot(index='STYLE', columns='Month', values='BILL_QUANTITY').fillna(0)
        
        # Calculate demand planning metrics
        pivot_qty['Total_Quantity'] = pivot_qty.sum(axis=1)
        pivot_qty['Peak_Month'] = pivot_qty.iloc[:, :-1].idxmax(axis=1)
        pivot_qty['Peak_Month_Qty'] = pivot_qty.iloc[:, :-2].max(axis=1)
        pivot_qty['Avg_Monthly_Demand'] = pivot_qty['Total_Quantity'] / 5  # 5 months
        pivot_qty['Demand_Volatility'] = pivot_qty.iloc[:, :-4].std(axis=1)  # Standard deviation as volatility measure
        
        # Sort by total quantity for demand planning priority
        pivot_qty = pivot_qty.sort_values('Total_Quantity', ascending=False)
        
        # Reset index to make STYLE a column
        result_df = pivot_qty.reset_index()
        
        # Rename month columns
        month_names = {6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October'}
        for month_num in range(start_month, end_month + 1):
            if month_num in result_df.columns:
                result_df = result_df.rename(columns={month_num: month_names.get(month_num, f'Month_{month_num}')})
        
        return result_df
        
    except Exception as e:
        print(f"Error creating style monthly quantity analysis: {str(e)}")
        return None

def create_color_level_analysis(df, approved_colors):
    """Create color-level analysis with approved colors focused on quantity for demand planning"""
    try:
        # Filter for approved colors
        df_approved = df[df['COLOR CODE'].isin(approved_colors)].copy()
        
        # Calculate metrics by color - focus on quantity for demand planning
        color_analysis = df_approved.groupby('COLOR CODE').agg({
            'BILL_QUANTITY': ['sum', 'mean', 'std'],
            'NET_AMOUNT': 'sum',
            'BILL_NO': 'nunique',  # Number of unique bills
            'STYLE': 'nunique'     # Number of unique styles
        }).reset_index()
        
        # Flatten column names
        color_analysis.columns = ['Color_Code', 'Total_Quantity', 'Avg_Qty_Per_Order', 'Qty_Volatility', 
                                'Total_Revenue', 'Unique_Bills', 'Unique_Styles']
        
        # Calculate additional demand planning metrics
        color_analysis['Avg_Revenue_Per_Unit'] = color_analysis['Total_Revenue'] / color_analysis['Total_Quantity']
        color_analysis['Demand_Intensity'] = color_analysis['Total_Quantity'] / color_analysis['Unique_Bills']  # Avg qty per transaction
        
        # Sort by total quantity for demand planning priority
        color_analysis = color_analysis.sort_values('Total_Quantity', ascending=False)
        
        return color_analysis
        
    except Exception as e:
        print(f"Error creating color-level analysis: {str(e)}")
        return None

def create_size_level_analysis(df):
    """Create size-level analysis focused on quantity for production planning"""
    try:
        # Calculate metrics by size - focus on quantity for production planning
        size_analysis = df.groupby('SIZE').agg({
            'BILL_QUANTITY': ['sum', 'mean', 'std'],
            'NET_AMOUNT': 'sum',
            'BILL_NO': 'nunique',  # Number of unique bills
            'STYLE': 'nunique',    # Number of unique styles
            'COLOR CODE': 'nunique' # Number of unique colors
        }).reset_index()
        
        # Flatten column names
        size_analysis.columns = ['Size', 'Total_Quantity', 'Avg_Qty_Per_Order', 'Qty_Volatility',
                               'Total_Revenue', 'Unique_Bills', 'Unique_Styles', 'Unique_Colors']
        
        # Calculate additional production planning metrics
        size_analysis['Avg_Revenue_Per_Unit'] = size_analysis['Total_Revenue'] / size_analysis['Total_Quantity']
        size_analysis['Production_Priority'] = size_analysis['Total_Quantity'] / size_analysis['Unique_Styles']  # Qty per style
        
        # Sort by total quantity for production planning priority
        size_analysis = size_analysis.sort_values('Total_Quantity', ascending=False)
        
        return size_analysis
        
    except Exception as e:
        print(f"Error creating size-level analysis: {str(e)}")
        return None

def create_best_quantity_styles_analysis(df):
    """Create analysis of best quantity performing styles for demand planning"""
    try:
        # Calculate total quantity and demand metrics by style
        style_qty = df.groupby('STYLE').agg({
            'BILL_QUANTITY': ['sum', 'mean', 'std', 'count'],
            'NET_AMOUNT': 'sum',
            'BILL_NO': 'nunique',
            'COLOR CODE': 'nunique'
        }).reset_index()
        
        # Flatten column names
        style_qty.columns = ['Style', 'Total_Quantity', 'Avg_Qty_Per_Order', 'Qty_Volatility', 'Order_Frequency',
                           'Total_Revenue', 'Unique_Bills', 'Unique_Colors']
        
        # Calculate demand planning metrics
        style_qty['Avg_Revenue_Per_Unit'] = style_qty['Total_Revenue'] / style_qty['Total_Quantity']
        style_qty['Demand_Consistency'] = style_qty['Total_Quantity'] / style_qty['Qty_Volatility'].fillna(1)  # Higher is more consistent
        style_qty['Market_Penetration'] = style_qty['Unique_Bills'] / style_qty['Order_Frequency']  # Bills per order occurrence
        
        # Sort by total quantity for demand planning priority
        style_qty = style_qty.sort_values('Total_Quantity', ascending=False)
        
        return style_qty
        
    except Exception as e:
        print(f"Error creating best quantity styles analysis: {str(e)}")
        return None

def create_style_color_matrix(df, approved_colors=None):
    """Create a matrix with styles as rows and alternating color-quantity columns"""
    try:
        # Filter for approved colors if provided
        if approved_colors is not None:
            df_filtered = df[df['COLOR CODE'].isin(approved_colors)].copy()
        else:
            df_filtered = df.copy()
        
        # Group by style and color to get total quantities
        style_color_qty = df_filtered.groupby(['STYLE', 'COLOR CODE'])['BILL_QUANTITY'].sum().reset_index()
        
        # Get top colors by total quantity
        color_totals = style_color_qty.groupby('COLOR CODE')['BILL_QUANTITY'].sum().sort_values(ascending=False)
        top_colors = color_totals.index.tolist()
        
        # Create result data
        result_data = []
        
        for style in style_color_qty['STYLE'].unique():
            style_data = style_color_qty[style_color_qty['STYLE'] == style].copy()
            style_data = style_data.set_index('COLOR CODE')['BILL_QUANTITY']
            
            row = {'STYLE': style}
            
            # Add color and quantity pairs for top colors
            for i, color in enumerate(top_colors, 1):
                qty = style_data.get(color, 0)
                if qty > 0:  # Only include colors that have sales
                    row[f'Color {i}'] = color
                    row[f'Qty {i}'] = qty
            
            # Calculate total
            row['Total'] = style_data.sum()
            result_data.append(row)
        
        # Convert to DataFrame
        result_df = pd.DataFrame(result_data)
        
        # Sort by total quantity
        result_df = result_df.sort_values('Total', ascending=False)
        
        return result_df
        
    except Exception as e:
        print(f"Error creating style-color matrix: {str(e)}")
        return None

def create_style_size_matrix(df):
    """Create a matrix with styles as rows and sizes as columns with sales quantities"""
    try:
        # Group by style and size to get total quantities
        style_size_qty = df.groupby(['STYLE', 'SIZE'])['BILL_QUANTITY'].sum().reset_index()
        
        # Pivot to create matrix: styles as rows, sizes as columns
        pivot_df = style_size_qty.pivot(index='STYLE', columns='SIZE', values='BILL_QUANTITY').fillna(0)
        
        # Sort columns by total quantity (most popular sizes first)
        col_totals = pivot_df.sum(axis=0).sort_values(ascending=False)
        pivot_df = pivot_df[col_totals.index]
        
        # Add total row quantity
        pivot_df['Total'] = pivot_df.sum(axis=1)
        
        # Sort rows by total quantity
        pivot_df = pivot_df.sort_values('Total', ascending=False)
        
        # Reset index to make STYLE a column
        result_df = pivot_df.reset_index()
        
        return result_df
        
    except Exception as e:
        print(f"Error creating style-size matrix: {str(e)}")
        return None

def export_comprehensive_analysis(monthly_qty_df, best_qty_df, color_analysis_df, size_analysis_df, 
                                 style_color_matrix_df, style_color_approved_df, style_size_matrix_df):
    """Export comprehensive quantity-based analysis to Excel for demand and production planning"""
    try:
        # Create Excel writer
        output_file = r'D:\DATA TILL DATE\Desktop\Quantity_Based_Demand_Planning_Analysis.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write style-color matrix (all colors)
            if style_color_matrix_df is not None:
                style_color_matrix_df.to_excel(writer, sheet_name='Style-Color Matrix (All)', index=False)
            
            # Write style-color matrix (approved colors only)
            if style_color_approved_df is not None:
                style_color_approved_df.to_excel(writer, sheet_name='Style-Color Matrix (Approved)', index=False)
            
            # Write style-size matrix
            if style_size_matrix_df is not None:
                style_size_matrix_df.to_excel(writer, sheet_name='Style-Size Matrix', index=False)
            
            # Write monthly quantity analysis
            if monthly_qty_df is not None:
                monthly_qty_df.to_excel(writer, sheet_name='Style Monthly Qty Jun-Oct', index=False)
            
            # Write best quantity styles analysis
            if best_qty_df is not None:
                best_qty_df.to_excel(writer, sheet_name='Best Quantity Styles Overall', index=False)
            
            # Write color analysis
            if color_analysis_df is not None:
                color_analysis_df.to_excel(writer, sheet_name='Color Level Qty Analysis', index=False)
            
            # Write size analysis
            if size_analysis_df is not None:
                size_analysis_df.to_excel(writer, sheet_name='Size Level Qty Analysis', index=False)
            
            # Auto-adjust column widths for all sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        print(f"Quantity-based demand planning analysis exported to {output_file}")
        
    except Exception as e:
        print(f"Error exporting quantity-based analysis: {str(e)}")

def main():
    # Load sales data
    print("Loading sales data...")
    sales_df = load_sales_data()
    if sales_df is None:
        return
    
    # Load approved colors
    print("Loading approved colors...")
    approved_colors = load_approved_colors()
    if approved_colors is None:
        print("Warning: Could not load approved colors, proceeding with all colors for color analysis")
        approved_colors = sales_df['COLOR CODE'].unique().tolist()
    
    print(f"Data loaded successfully. Total records: {len(sales_df)}")
    print(f"Date range: {sales_df['BILL_DATE'].min()} to {sales_df['BILL_DATE'].max()}")
    
    # 1. Create style-level monthly quantity analysis (June to October) for demand planning
    print("\n1. Creating style-level monthly quantity analysis for demand planning (June to October)...")
    monthly_qty_analysis = create_style_monthly_quantity_analysis(sales_df, 6, 10)
    if monthly_qty_analysis is not None:
        print(f"   ✓ Monthly quantity analysis completed for {len(monthly_qty_analysis)} styles")
    
    # 2. Create best quantity styles analysis (overall) for demand planning
    print("\n2. Creating best quantity styles analysis for demand planning...")
    best_qty_analysis = create_best_quantity_styles_analysis(sales_df)
    if best_qty_analysis is not None:
        print(f"   ✓ Best quantity analysis completed for {len(best_qty_analysis)} styles")
    
    # 3. Create color-level quantity analysis (with approved colors) for demand planning
    print("\n3. Creating color-level quantity analysis for demand planning...")
    color_analysis = create_color_level_analysis(sales_df, approved_colors)
    if color_analysis is not None:
        print(f"   ✓ Color quantity analysis completed for {len(color_analysis)} colors")
    
    # 4. Create size-level quantity analysis for production planning
    print("\n4. Creating size-level quantity analysis for production planning...")
    size_analysis = create_size_level_analysis(sales_df)
    if size_analysis is not None:
        print(f"   ✓ Size quantity analysis completed for {len(size_analysis)} sizes")
    
    # 5. Create style-color matrix with all colors
    print("\n5. Creating style-color matrix with all colors...")
    style_color_matrix_all = create_style_color_matrix(sales_df, approved_colors=None)
    if style_color_matrix_all is not None:
        print(f"   ✓ Style-color matrix (all colors) completed for {len(style_color_matrix_all)} styles")
    
    # 6. Create style-color matrix with approved colors only
    print("\n6. Creating style-color matrix with approved colors only...")
    style_color_matrix_approved = create_style_color_matrix(sales_df, approved_colors)
    if style_color_matrix_approved is not None:
        print(f"   ✓ Style-color matrix (approved colors) completed for {len(style_color_matrix_approved)} styles")
    
    # 7. Create style-size matrix (styles as rows, sizes as columns)
    print("\n7. Creating style-size matrix (styles x sizes)...")
    style_size_matrix = create_style_size_matrix(sales_df)
    if style_size_matrix is not None:
        print(f"   ✓ Style-size matrix completed for {len(style_size_matrix)} styles")
    
    # Export all results
    print("\n8. Exporting quantity-based demand and production planning analysis...")
    export_comprehensive_analysis(monthly_qty_analysis, best_qty_analysis, color_analysis, size_analysis,
                                 style_color_matrix_all, style_color_matrix_approved, style_size_matrix)
    
    # Print summary focused on quantities for demand/production planning
    print("\n" + "="*80)
    print("QUANTITY-BASED DEMAND & PRODUCTION PLANNING ANALYSIS SUMMARY")
    print("="*80)
    
    if monthly_qty_analysis is not None and not monthly_qty_analysis.empty:
        print(f"\nTop 5 Styles by Monthly Quantity Demand (June-October):")
        for i, row in monthly_qty_analysis.head().iterrows():
            avg_demand = row['Avg_Monthly_Demand']
            volatility = row['Demand_Volatility']
            print(f"  {i+1}. {row['STYLE']}: {row['Total_Quantity']:,.0f} units total, "
                  f"{avg_demand:.0f}/month avg, volatility: {volatility:.1f}")
    
    if best_qty_analysis is not None and not best_qty_analysis.empty:
        print(f"\nTop 5 Styles by Overall Quantity Demand:")
        for i, row in best_qty_analysis.head().iterrows():
            consistency = row['Demand_Consistency']
            print(f"  {i+1}. {row['Style']}: {row['Total_Quantity']:,.0f} units, "
                  f"consistency score: {consistency:.1f}")
    
    if color_analysis is not None and not color_analysis.empty:
        print(f"\nTop 5 Colors by Quantity Demand:")
        for i, row in color_analysis.head().iterrows():
            intensity = row['Demand_Intensity']
            print(f"  {i+1}. {row['Color_Code']}: {row['Total_Quantity']:,.0f} units, "
                  f"demand intensity: {intensity:.1f} units/transaction")
    
    if size_analysis is not None and not size_analysis.empty:
        print(f"\nTop 5 Sizes by Production Volume:")
        for i, row in size_analysis.head().iterrows():
            priority = row['Production_Priority']
            print(f"  {i+1}. {row['Size']}: {row['Total_Quantity']:,.0f} units, "
                  f"production priority: {priority:.1f} units/style")
    
    if style_color_matrix_all is not None and not style_color_matrix_all.empty:
        print(f"\nStyle-Color Matrix (All Colors) created with {len(style_color_matrix_all)} styles")
    
    if style_color_matrix_approved is not None and not style_color_matrix_approved.empty:
        print(f"\nStyle-Color Matrix (Approved Colors) created with {len(style_color_matrix_approved)} styles")
    
    if style_size_matrix is not None and not style_size_matrix.empty:
        print(f"\nStyle-Size Matrix created with {len(style_size_matrix)} styles and {len(style_size_matrix.columns)-2} sizes")
    
    print("\nQuantity-based demand and production planning analysis completed!")
    print("Results saved to: D:\\DATA TILL DATE\\Desktop\\Quantity_Based_Demand_Planning_Analysis.xlsx")
    print("\nKey Metrics Explained:")
    print("- Demand Volatility: Standard deviation of monthly quantities (lower = more predictable)")
    print("- Demand Intensity: Average units per transaction (higher = bulk purchasing)")
    print("- Production Priority: Average units per style (higher = focus production)")
    print("- Demand Consistency: Ratio of total quantity to volatility (higher = stable demand)")
    print("\nMatrix Sheets:")
    print("- Style-Color Matrix (All): Styles with all available colors and quantities")
    print("- Style-Color Matrix (Approved): Styles with approved colors only and quantities")
    print("- Style-Size Matrix: Styles as rows, sizes as columns with sales quantities")

if __name__ == "__main__":
    main()