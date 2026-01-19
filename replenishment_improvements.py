# REPLENISHMENT MODEL IMPROVEMENTS
# This file contains suggested enhancements for the retail replenishment model

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def enhanced_demand_forecasting(replen_calc):
    """
    Enhanced demand forecasting with multiple methods
    """
    # 1. SEASONAL ADJUSTMENTS
    current_month = pd.Timestamp.now().month
    seasonal_factors = {
        1: 0.8, 2: 0.9, 3: 1.1, 4: 1.0, 5: 1.0, 6: 1.0,  # Jan-Jun
        7: 0.9, 8: 0.9, 9: 1.1, 10: 1.2, 11: 1.3, 12: 1.4  # Jul-Dec
    }
    seasonal_factor = seasonal_factors.get(current_month, 1.0)
    
    # 2. ABC CLASSIFICATION
    replen_calc['SALES_VALUE'] = replen_calc['DAILY_SALES'] * replen_calc.get('UNIT_PRICE', 100)
    abc_thresholds = replen_calc['SALES_VALUE'].quantile([0.7, 0.9])
    replen_calc['ABC_CLASS'] = 'C'
    replen_calc.loc[replen_calc['SALES_VALUE'] >= abc_thresholds[0.7], 'ABC_CLASS'] = 'B'
    replen_calc.loc[replen_calc['SALES_VALUE'] >= abc_thresholds[0.9], 'ABC_CLASS'] = 'A'
    
    # 3. VELOCITY CLASSIFICATION
    velocity_thresholds = replen_calc['DAILY_SALES'].quantile([0.3, 0.7])
    replen_calc['VELOCITY_CLASS'] = 'Slow'
    replen_calc.loc[replen_calc['DAILY_SALES'] >= velocity_thresholds[0.3], 'VELOCITY_CLASS'] = 'Medium'
    replen_calc.loc[replen_calc['DAILY_SALES'] >= velocity_thresholds[0.7], 'VELOCITY_CLASS'] = 'Fast'
    
    # 4. ENHANCED FORECASTING
    replen_calc['SEASONAL_DEMAND'] = replen_calc['DAILY_SALES'] * seasonal_factor
    
    # Different forecasting for different categories
    conditions = [
        (replen_calc['ABC_CLASS'] == 'A') & (replen_calc['VELOCITY_CLASS'] == 'Fast'),
        (replen_calc['ABC_CLASS'] == 'A') & (replen_calc['VELOCITY_CLASS'] == 'Medium'),
        (replen_calc['ABC_CLASS'] == 'B') & (replen_calc['VELOCITY_CLASS'] != 'Slow'),
        replen_calc['VELOCITY_CLASS'] == 'Slow'
    ]
    
    choices = [
        replen_calc['SEASONAL_DEMAND'] * 1.5,  # A-Fast: 50% buffer
        replen_calc['SEASONAL_DEMAND'] * 1.3,  # A-Medium: 30% buffer
        replen_calc['SEASONAL_DEMAND'] * 1.2,  # B-items: 20% buffer
        replen_calc['SEASONAL_DEMAND'] * 0.8   # Slow items: 20% reduction
    ]
    
    replen_calc['ENHANCED_FORECAST'] = np.select(conditions, choices, default=replen_calc['SEASONAL_DEMAND'])
    
    return replen_calc

def dynamic_safety_stock(replen_calc, lead_time_days=7):
    """
    Calculate dynamic safety stock based on demand variability
    """
    # Calculate coefficient of variation (CV) for each SKU
    # Higher CV = more variable demand = higher safety stock needed
    
    # Simulate demand variability (in real scenario, use historical data)
    replen_calc['DEMAND_CV'] = np.random.uniform(0.1, 0.8, len(replen_calc))
    
    # Service level mapping
    service_levels = {
        'A': 0.98,  # 98% service level for A items
        'B': 0.95,  # 95% service level for B items
        'C': 0.90   # 90% service level for C items
    }
    
    # Z-scores for different service levels
    z_scores = {0.90: 1.28, 0.95: 1.65, 0.98: 2.05}
    
    replen_calc['SERVICE_LEVEL'] = replen_calc['ABC_CLASS'].map(service_levels)
    replen_calc['Z_SCORE'] = replen_calc['SERVICE_LEVEL'].map(z_scores)
    
    # Dynamic safety stock = Z-score × √(lead_time) × demand_std_dev
    replen_calc['DYNAMIC_SAFETY_STOCK'] = (
        replen_calc['Z_SCORE'] * 
        np.sqrt(lead_time_days) * 
        replen_calc['ENHANCED_FORECAST'] * 
        replen_calc['DEMAND_CV']
    )
    
    return replen_calc

def intelligent_allocation(replen_calc):
    """
    Intelligent allocation considering multiple factors
    """
    # 1. STORE PERFORMANCE SCORE
    store_metrics = replen_calc.groupby('STORE').agg({
        'DAILY_SALES': 'sum',
        'STOCK': 'sum',
        'PRIORITY_SCORE': 'first'
    }).reset_index()
    
    store_metrics['STOCK_TURN'] = np.where(
        store_metrics['STOCK'] > 0,
        store_metrics['DAILY_SALES'] / store_metrics['STOCK'],
        0
    )
    
    # Normalize metrics
    max_turn = store_metrics['STOCK_TURN'].max() if store_metrics['STOCK_TURN'].max() > 0 else 1
    store_metrics['TURN_SCORE'] = store_metrics['STOCK_TURN'] / max_turn
    
    # Combined store score
    store_metrics['STORE_SCORE'] = (
        0.4 * store_metrics['PRIORITY_SCORE'] + 
        0.6 * store_metrics['TURN_SCORE']
    )
    
    # Merge back to main data
    replen_calc = pd.merge(
        replen_calc,
        store_metrics[['STORE', 'STORE_SCORE']],
        on='STORE',
        how='left'
    )
    
    # 2. PRODUCT IMPORTANCE SCORE
    replen_calc['PRODUCT_SCORE'] = (
        0.3 * (replen_calc['ABC_CLASS'].map({'A': 1.0, 'B': 0.7, 'C': 0.4})) +
        0.4 * (replen_calc['VELOCITY_CLASS'].map({'Fast': 1.0, 'Medium': 0.6, 'Slow': 0.2})) +
        0.3 * (replen_calc['DAILY_SALES'] / replen_calc['DAILY_SALES'].max())
    )
    
    # 3. FINAL ALLOCATION PRIORITY
    replen_calc['ALLOCATION_PRIORITY'] = (
        replen_calc['STORE_SCORE'] * replen_calc['PRODUCT_SCORE']
    )
    
    return replen_calc

def size_set_optimization(replen_calc):
    """
    Optimize allocations to complete size sets
    """
    # Group by store, style, color to analyze size sets
    size_analysis = []
    
    for (store, style, color), group in replen_calc.groupby(['STORE', 'STYLE', 'COLOR']):
        sizes_available = set(group['SIZE'].unique())
        sizes_with_stock = set(group[group['STOCK'] > 0]['SIZE'].unique())
        sizes_with_demand = set(group[group['DAILY_SALES'] > 0]['SIZE'].unique())
        
        total_sizes = len(sizes_available)
        complete_sizes = len(sizes_with_stock.union(sizes_with_demand))
        
        # Prioritize completing size sets that are close to complete
        completion_rate = complete_sizes / total_sizes if total_sizes > 0 else 0
        
        size_analysis.append({
            'STORE': store,
            'STYLE': style,
            'COLOR': color,
            'COMPLETION_RATE': completion_rate,
            'MISSING_SIZES': total_sizes - complete_sizes,
            'SIZE_SET_PRIORITY': 1.0 if completion_rate >= 0.75 else 0.5
        })
    
    size_df = pd.DataFrame(size_analysis)
    
    # Merge size set priority back
    replen_calc = pd.merge(
        replen_calc,
        size_df[['STORE', 'STYLE', 'COLOR', 'SIZE_SET_PRIORITY']],
        on=['STORE', 'STYLE', 'COLOR'],
        how='left'
    )
    
    replen_calc['SIZE_SET_PRIORITY'] = replen_calc['SIZE_SET_PRIORITY'].fillna(0.3)
    
    return replen_calc

def business_rules_engine(replen_calc, moq=6):
    """
    Apply business rules and constraints
    """
    # 1. MINIMUM VIABLE QUANTITIES
    replen_calc['MIN_VIABLE_QTY'] = np.where(
        replen_calc['ABC_CLASS'] == 'A',
        moq * 2,  # A items: minimum 2 MOQ
        moq       # B,C items: minimum 1 MOQ
    )
    
    # 2. MAXIMUM ORDER LIMITS
    replen_calc['MAX_ORDER_QTY'] = np.where(
        replen_calc['VELOCITY_CLASS'] == 'Fast',
        moq * 8,   # Fast movers: up to 8 MOQ
        np.where(
            replen_calc['VELOCITY_CLASS'] == 'Medium',
            moq * 4,   # Medium movers: up to 4 MOQ
            moq * 2    # Slow movers: up to 2 MOQ
        )
    )
    
    # 3. PACK SIZE CONSTRAINTS
    pack_sizes = {'APPAREL': 6, 'ACCESSORIES': 12, 'FOOTWEAR': 4}
    replen_calc['PACK_SIZE'] = replen_calc.get('CATEGORY', 'APPAREL').map(pack_sizes).fillna(6)
    
    # 4. BUDGET CONSTRAINTS (optional)
    replen_calc['UNIT_COST'] = replen_calc.get('UNIT_PRICE', 100) * 0.6  # Assume 60% cost
    replen_calc['ORDER_VALUE'] = replen_calc['REPLEN_QTY'] * replen_calc['UNIT_COST']
    
    return replen_calc

def generate_improvement_recommendations():
    """
    Generate actionable recommendations for model improvements
    """
    improvements = {
        "Critical": [
            "Implement trend analysis using 3-6 months historical data",
            "Add promotional/markdown impact modeling", 
            "Include competitor pricing and market share data",
            "Implement machine learning for demand forecasting",
            "Add real-time inventory tracking integration"
        ],
        "High Impact": [
            "Dynamic lead time calculation based on supplier performance",
            "Store clustering for similar demand patterns",
            "Cross-selling and cannibalization effects",
            "Weather and external factor integration",
            "Automated exception reporting and alerts"
        ],
        "Medium Impact": [
            "Pack size optimization algorithms",
            "Transportation cost optimization",
            "Shelf space and planogram constraints",
            "Markdown timing optimization",
            "Size curve analysis and optimization"
        ],
        "Operational": [
            "Automated data quality checks",
            "Performance dashboards and KPIs",
            "Allocation approval workflows",
            "Exception handling procedures",
            "Regular model performance monitoring"
        ]
    }
    
    return improvements

if __name__ == "__main__":
    print("=== REPLENISHMENT MODEL IMPROVEMENT RECOMMENDATIONS ===")
    recommendations = generate_improvement_recommendations()
    
    for priority, items in recommendations.items():
        print(f"\n{priority} Priority:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")