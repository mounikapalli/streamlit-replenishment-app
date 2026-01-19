import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori
from mlxtend.frequent_patterns import association_rules
import polars as pl
import streamlit as st
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

def load_transaction_data(sales_data_path):
    """Load and prepare transaction data"""
    try:
        # Read sales data using polars for better performance
        df = pl.read_excel(sales_data_path)
        
        # Convert to pandas for association analysis
        sales_df = df.to_pandas()
        
        # Ensure required columns exist
        required_cols = ['BILL_NO', 'SKU', 'STYLE', 'BILL_DATE']
        missing_cols = [col for col in required_cols if col not in sales_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        # List of freebie SKUs to exclude
        freebie_skus = [
            'UAA201ASCFSE', 'UAGY01BLK699', 'UAC101BLKFSE', 'UAC101BTEFSE',
            'UAC101CNGFSE', 'UAC101LTGFSE', 'UAC101LTNFSE', 'UAC101NVYFSE',
            'MAKRAFTBAGBIG', 'MAKRAFTBAGSML', 'MABOATPB3990', 'MAAIRPODS4999',
            'MAPOWBANK3999', 'MAAIRPODS3599', 'MATROLLEY9999', 'MATUMOFW299',
            'MAMESHBLK067'
        ]
        
        # Filter out freebie SKUs
        original_count = len(sales_df)
        sales_df = sales_df[~sales_df['SKU'].isin(freebie_skus)]
        filtered_count = len(sales_df)
        
        # Show info about filtered records
        st.info(f"Removed {original_count - filtered_count} freebie transactions from analysis")
            
        return sales_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def create_transaction_matrix(sales_df, group_by='STYLE'):
    """Create transaction matrix for association analysis"""
    # Group transactions
    transaction_matrix = (sales_df
        .groupby(['BILL_NO', group_by])
        .size()
        .unstack(fill_value=0)
        .astype(bool)
        .astype(int))
    
    return transaction_matrix

def perform_association_analysis(transaction_matrix, min_support=0.01, min_confidence=0.3):
    """Perform association rule mining"""
    # Generate frequent itemsets
    frequent_itemsets = apriori(transaction_matrix, 
                              min_support=min_support, 
                              use_colnames=True)
    
    # Generate association rules
    rules = association_rules(frequent_itemsets, 
                            metric="confidence", 
                            min_threshold=min_confidence)
    
    # Calculate lift ratio
    rules["lift_ratio"] = rules["lift"].apply(lambda x: "Strong" if x > 1 else "Weak")
    
    return rules, frequent_itemsets

def analyze_category_associations(sales_df, sku_master_df):
    """Analyze associations between product categories"""
    # First, check available columns in sku_master_df
    st.write("Available columns in SKU master:", sku_master_df.columns.tolist())
    
    # Find category column - it might be named differently
    category_columns = [col for col in sku_master_df.columns 
                      if any(cat in col.upper() for cat in ['CATEGORY', 'CAT', 'PROD_CAT'])]
    
    if not category_columns:
        st.error("No category column found in SKU master. Please ensure SKU master has a category column.")
        return None
        
    category_column = category_columns[0]
    st.info(f"Using column '{category_column}' for category analysis")
    
    # Merge sales with SKU master
    merged_df = sales_df.merge(
        sku_master_df[['SKU', category_column]], 
        on='SKU', 
        how='left'
    )
    
    if merged_df[category_column].isna().any():
        st.warning(f"Some SKUs are missing {category_column} information")
    
    # Create category-level transaction matrix 
    category_matrix = create_transaction_matrix(merged_df, group_by=category_column)
    
    # Perform association analysis at category level
    category_rules, category_itemsets = perform_association_analysis(
        category_matrix,
        min_support=0.02,  # Higher support for categories
        min_confidence=0.4
    )
    
    return category_rules, category_itemsets

def create_visualization(rules):
    """Create visualization for association rules"""
    # Scatter plot of support vs confidence
    fig = px.scatter(
        rules,
        x="support",
        y="confidence",
        size="lift",
        color="lift_ratio",
        title="Association Rules - Support vs Confidence",
        labels={
            "support": "Support",
            "confidence": "Confidence",
            "lift": "Lift"
        }
    )
    
    return fig

def analyze_seasonal_patterns(sales_df, rules):
    """Analyze how associations change by season"""
    sales_df['Month'] = pd.to_datetime(sales_df['BILL_DATE']).dt.month
    
    # Define seasons
    season_map = {
        12: 'Winter', 1: 'Winter', 2: 'Winter',
        3: 'Spring', 4: 'Spring', 5: 'Spring',
        6: 'Summer', 7: 'Summer', 8: 'Summer',
        9: 'Fall', 10: 'Fall', 11: 'Fall'
    }
    
    sales_df['Season'] = sales_df['Month'].map(season_map)
    
    # Analyze associations by season
    seasonal_patterns = {}
    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        season_data = sales_df[sales_df['Season'] == season]
        if not season_data.empty:
            season_matrix = create_transaction_matrix(season_data)
            season_rules, _ = perform_association_analysis(
                season_matrix,
                min_support=0.01,
                min_confidence=0.3
            )
            seasonal_patterns[season] = season_rules
            
    return seasonal_patterns

def main():
    st.title("Retail Association Analysis")
    
    st.sidebar.header("Analysis Parameters")
    min_support = st.sidebar.slider("Minimum Support", 0.01, 0.1, 0.01, 0.01)
    min_confidence = st.sidebar.slider("Minimum Confidence", 0.1, 1.0, 0.3, 0.1)
    
    # File upload
    sales_file = st.file_uploader("Upload Sales Data (Excel)", type=['xlsx'])
    sku_master_file = st.file_uploader("Upload SKU Master (Excel)", type=['xlsx'])
    
    if sales_file and sku_master_file:
        # Load data
        sales_df = load_transaction_data(sales_file)
        sku_master_df = pd.read_excel(sku_master_file)
        
        if sales_df is not None:
            st.subheader("1. Transaction Analysis")
            
            # Create transaction matrix
            transaction_matrix = create_transaction_matrix(sales_df)
            
            # Perform association analysis
            rules, itemsets = perform_association_analysis(
                transaction_matrix,
                min_support=min_support,
                min_confidence=min_confidence
            )
            
            # Display results
            st.write("Top Association Rules:")
            st.dataframe(rules.sort_values('lift', ascending=False).head(10))
            
            # Visualization
            st.plotly_chart(create_visualization(rules))
            
            # Category Analysis
            st.subheader("2. Category Level Analysis")
            category_result = analyze_category_associations(
                sales_df,
                sku_master_df
            )
            
            if category_result is not None:
                category_rules, category_itemsets = category_result
                st.write("Top Category Associations:")
                st.dataframe(category_rules.sort_values('lift', ascending=False).head(10))
            else:
                st.error("Could not perform category analysis. Please check the SKU master data.")
            
            # Seasonal Analysis
            st.subheader("3. Seasonal Pattern Analysis")
            seasonal_patterns = analyze_seasonal_patterns(sales_df, rules)
            
            # Display seasonal insights
            for season, season_rules in seasonal_patterns.items():
                st.write(f"\n{season} Associations:")
                st.dataframe(season_rules.sort_values('lift', ascending=False).head(5))
            
            # Download Results
            st.subheader("Download Analysis Results")
            
            # Create Excel file with results
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                rules.to_excel(writer, sheet_name='Association_Rules', index=False)
                if category_result is not None:
                    category_rules.to_excel(writer, sheet_name='Category_Rules', index=False)
                
                # Add seasonal patterns
                for season, season_rules in seasonal_patterns.items():
                    season_rules.to_excel(writer, sheet_name=f'{season}_Rules', index=False)
            
            output.seek(0)
            st.download_button(
                label="Download Analysis Results",
                data=output,
                file_name="association_analysis_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()