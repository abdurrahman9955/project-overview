# src/kpi_calculations.py

import pandas as pd

def calculate_copq_kpis(copq_data_sections):
    """
    Calculates various COPQ KPIs based on the processed COPQ data sections.
    
    Args:
        copq_data_sections (dict): A dictionary containing DataFrames/Series for
                                   'basic_copq', 'breakdown_copq', 'monthly_copq_tracking',
                                   and 'defect_categories'.
                                   
    Returns:
        dict: A dictionary of calculated COPQ KPIs and augmented DataFrames.
    """
    calculated_kpis = {}
    
    # Ensure relevant data sections are available
    basic_copq = copq_data_sections.get('basic_copq')
    breakdown_copq = copq_data_sections.get('breakdown_copq')
    monthly_copq_tracking = copq_data_sections.get('monthly_copq_tracking')
    defect_categories = copq_data_sections.get('defect_categories')

    if basic_copq is not None and not basic_copq.empty:
        # 1. Total COPQ (£) - From the 'TOTAL COPQ' section, or sum from breakdown
        # Based on the provided data, we can get this directly from basic_copq or breakdown_copq
        # Let's derive it from the breakdown data for consistency, or monthly if available
        # Preferring monthly_copq_tracking for total COPQ if available as it's a series.
        if monthly_copq_tracking is not None and not monthly_copq_tracking.empty:
            calculated_kpis['Total COPQ (£)'] = monthly_copq_tracking['COPQ (£)'].sum()
        elif breakdown_copq is not None and not breakdown_copq.empty:
            # If monthly is not available, try to get from breakdown table's 'Total' row
            total_row = breakdown_copq[breakdown_copq['Category'].str.strip() == 'Total']
            if not total_row.empty:
                calculated_kpis['Total COPQ (£)'] = total_row['Cost (£)'].iloc[0]
            else:
                 calculated_kpis['Total COPQ (£)'] = None # Could not find total COPQ

        # 2. Defect Rate (PPM) - Directly from basic_copq
        calculated_kpis['Defect Rate (PPM)'] = basic_copq.get('Defect Rate (PPM)', None)
        
        # We need Revenue to calculate percentages of revenue. It's not explicitly in COPQ data.
        # For now, let's assume a dummy revenue or make a note that this needs external input.
        # Client mentioned "Scrap, Rework, and Warranty Costs as % of Revenue".
        # In `COPQ_Dummy_Data`, there's a line "COPQ as % of Revenue" at the end.
        # Also, the breakdown table has "% of Revenue". Let's use the breakdown table's percentages.
        if breakdown_copq is not None and not breakdown_copq.empty:
            scrap_row = breakdown_copq[breakdown_copq['Category'].str.strip() == 'Scrap']
            rework_row = breakdown_copq[breakdown_copq['Category'].str.strip() == 'Rework']
            warranty_row = breakdown_copq[breakdown_copq['Category'].str.strip() == 'Warranty']
            
            calculated_kpis['Scrap Cost as % of Revenue'] = scrap_row['% of Revenue'].iloc[0] if not scrap_row.empty else None
            calculated_kpis['Rework Cost as % of Revenue'] = rework_row['% of Revenue'].iloc[0] if not rework_row.empty else None
            calculated_kpis['Warranty Cost as % of Revenue'] = warranty_row['% of Revenue'].iloc[0] if not warranty_row.empty else None
        else:
            calculated_kpis['Scrap Cost as % of Revenue'] = None
            calculated_kpis['Rework Cost as % of Revenue'] = None
            calculated_kpis['Warranty Cost as % of Revenue'] = None
    else:
        # If basic_copq is not available, set all KPIs to None
        calculated_kpis['Total COPQ (£)'] = None
        calculated_kpis['Defect Rate (PPM)'] = None
        calculated_kpis['Scrap Cost as % of Revenue'] = None
        calculated_kpis['Rework Cost as % of Revenue'] = None
        calculated_kpis['Warranty Cost as % of Revenue'] = None


    # Augment DataFrames if needed for visualization or further analysis
    augmented_data = {
        'monthly_copq_tracking': monthly_copq_tracking.copy() if monthly_copq_tracking is not None else None,
        'copq_breakdown': breakdown_copq.copy() if breakdown_copq is not None else None,
        'defect_categories': defect_categories.copy() if defect_categories is not None else None
    }

    # Example of how Scrap Cost formula could be implemented if we had granular data
    # Scrap Cost = Units Scrapped × (Material + Labor + Overhead Cost)
    # The dummy data provides Total Scrap Cost directly, so we'll just use that from the breakdown.
    # If a more granular 'Units Scrapped' and per-unit costs were in a DataFrame:
    # df['Scrap Cost'] = df['Units Scrapped'] * (df['Material Cost'] + df['Labor Cost'] + df['Overhead Cost'])

    return calculated_kpis, augmented_data

def calculate_oee_kpis(oee_data_sections):
    """
    Calculates various OEE KPIs based on the processed OEE data sections.
    
    Args:
        oee_data_sections (dict): A dictionary containing DataFrames for
                                  'monthly_oee', 'teep_detailed', 'downtime_cost',
                                  and 'maintenance_costs'.
                                  
    Returns:
        dict: A dictionary of calculated OEE KPIs and augmented DataFrames.
    """
    calculated_kpis = {}
    
    monthly_oee_df = oee_data_sections.get('monthly_oee')
    teep_detailed_df = oee_data_sections.get('teep_detailed')
    downtime_cost_df = oee_data_sections.get('downtime_cost')

    if monthly_oee_df is not None and not monthly_oee_df.empty:
        # 1. OEE (%) = Availability × Performance × Quality
        # The monthly_oee table already provides this, so we take the latest or average.
        # Let's calculate the average OEE for the period in the data
        calculated_kpis['Average OEE (%)'] = monthly_oee_df['OEE (%)'].mean()
    else:
        calculated_kpis['Average OEE (%)'] = None

    if teep_detailed_df is not None and not teep_detailed_df.empty:
        # 2. TEEP (%) = Utilization × OEE
        # The teep_detailed table already provides this calculated, or we re-calculate.
        # We re-calculated it during parsing, so just take the average here.
        calculated_kpis['Average TEEP (%)'] = teep_detailed_df['TEEP (%)'].mean()
    else:
        calculated_kpis['Average TEEP (%)'] = None

    if downtime_cost_df is not None and not downtime_cost_df.empty:
        # 3. Downtime Cost per Minute (£)
        # The downtime_cost table provides 'Cost/Min (£)' directly
        calculated_kpis['Average Downtime Cost per Minute (£)'] = downtime_cost_df['Cost/Min (£)'].mean()
    else:
        calculated_kpis['Average Downtime Cost per Minute (£)'] = None

    # Augment DataFrames if needed. The OEE and TEEP calculations are largely
    # present in the loaded tables, but we might add columns for visualization later.
    augmented_data = {
        'monthly_oee_trends': monthly_oee_df.copy() if monthly_oee_df is not None else None,
        'downtime_cost_analysis': downtime_cost_df.copy() if downtime_cost_df is not None else None
    }
   
    return calculated_kpis, augmented_data

def calculate_mfg_cost_kpis(mfg_cost_data_sections):
    """
    Calculates various Manufacturing Cost per Unit KPIs.
    
    Args:
        mfg_cost_data_sections (dict): A dictionary containing DataFrames for
                                       'production_data', 'total_manufacturing_cost',
                                       'efficiency_indicators', and 'cost_variance'.
                                       
    Returns:
        dict: A dictionary of calculated Manufacturing Cost per Unit KPIs and augmented DataFrames.
    """
    calculated_kpis = {}
    
    production_data = mfg_cost_data_sections.get('production_data')
    total_mfg_cost_df = mfg_cost_data_sections.get('total_manufacturing_cost')
    efficiency_indicators_df = mfg_cost_data_sections.get('efficiency_indicators')
    cost_variance_df = mfg_cost_data_sections.get('cost_variance')

    # 1. Total Cost per Unit (£) = (Materials + Labor + Overhead) / Units Produced
    # We can get Manufacturing Cost per Unit directly from the `total_manufacturing_cost` table
    # Let's take the average or the latest value.
    if total_mfg_cost_df is not None and not total_mfg_cost_df.empty:
        calculated_kpis['Average Total Cost per Unit (£)'] = total_mfg_cost_df['Manufacturing Cost per Unit (£)'].mean()
    else:
        calculated_kpis['Average Total Cost per Unit (£)'] = None
    
    # 2. Labor Efficiency (%)
    if efficiency_indicators_df is not None and not efficiency_indicators_df.empty:
        calculated_kpis['Average Labor Efficiency (%)'] = efficiency_indicators_df['Labor Efficiency (%)'].mean() * 100 # Convert back to %
    else:
        calculated_kpis['Average Labor Efficiency (%)'] = None

    # 3. Material Yield (%)
    if efficiency_indicators_df is not None and not efficiency_indicators_df.empty:
        calculated_kpis['Average Material Yield (%)'] = efficiency_indicators_df['Material Yield (%)'].mean() * 100 # Convert back to %
    else:
        calculated_kpis['Average Material Yield (%)'] = None

    # 4. Cost Variance = Actual Cost – Budgeted Cost (We have this directly in cost_variance_df)
    # We can provide the latest variance or total variance here. Let's take the latest month's variance.
    if cost_variance_df is not None and not cost_variance_df.empty:
        latest_variance_row = cost_variance_df.iloc[-1] # Get the last row for the latest month
        calculated_kpis['Latest Cost Variance (£)'] = latest_variance_row.get('Variance (£)', None)
        calculated_kpis['Latest Cost Variance (%)'] = latest_variance_row.get('Variance (%)', None) * 100 # Convert back to %
    else:
        calculated_kpis['Latest Cost Variance (£)'] = None
        calculated_kpis['Latest Cost Variance (%)'] = None

    # Augment DataFrames for trends and breakdowns
    augmented_data = {
        'total_mfg_cost_trends': total_mfg_cost_df.copy() if total_mfg_cost_df is not None else None,
        'efficiency_trends': efficiency_indicators_df.copy() if efficiency_indicators_df is not None else None,
        'cost_variance_analysis': cost_variance_df.copy() if cost_variance_df is not None else None
    }
    
    return calculated_kpis, augmented_data

# Example usage (for testing purposes)
if __name__ == "__main__":
    from data_processor import load_and_process_copq_data, load_and_process_oee_data, load_and_process_mfg_cost_data
    import os

    current_dir = os.path.dirname(__file__)
    data_dir = os.path.join(current_dir, '..', 'data')

    copq_file = os.path.join(data_dir, 'COPQ_Dummy_Data.csv')
    oee_file = os.path.join(data_dir, 'OEE_Dummy_Data.csv')
    mfg_cost_file = os.path.join(data_dir, 'Manufacturing_Cost_per_Unit_Calculator.csv')

    print("--- Calculating COPQ KPIs ---")
    copq_raw_data = load_and_process_copq_data(copq_file)
    if copq_raw_data:
        copq_kpis, copq_augmented_data = calculate_copq_kpis(copq_raw_data)
        print("Calculated COPQ KPIs:", copq_kpis)
        if copq_augmented_data['monthly_copq_tracking'] is not None:
            print("\nAugmented Monthly COPQ Tracking Data Head:\n", copq_augmented_data['monthly_copq_tracking'].head())
        if copq_augmented_data['copq_breakdown'] is not None:
            print("\nAugmented COPQ Breakdown Data Head:\n", copq_augmented_data['copq_breakdown'].head())
    else:
        print("COPQ data not loaded, cannot calculate KPIs.")

    print("\n--- Calculating OEE KPIs ---")
    oee_raw_data = load_and_process_oee_data(oee_file)
    if oee_raw_data:
        oee_kpis, oee_augmented_data = calculate_oee_kpis(oee_raw_data)
        print("Calculated OEE KPIs:", oee_kpis)
        if oee_augmented_data['monthly_oee_trends'] is not None:
            print("\nAugmented Monthly OEE Trends Data Head:\n", oee_augmented_data['monthly_oee_trends'].head())
    else:
        print("OEE data not loaded, cannot calculate KPIs.")

    print("\n--- Calculating Manufacturing Cost KPIs ---")
    mfg_cost_raw_data = load_and_process_mfg_cost_data(mfg_cost_file)
    if mfg_cost_raw_data:
        mfg_cost_kpis, mfg_cost_augmented_data = calculate_mfg_cost_kpis(mfg_cost_raw_data)
        print("Calculated Manufacturing Cost KPIs:", mfg_cost_kpis)
        if mfg_cost_augmented_data['total_mfg_cost_trends'] is not None:
            print("\nAugmented Total Manufacturing Cost Trends Data Head:\n", mfg_cost_augmented_data['total_mfg_cost_trends'].head())
    else:
        print("Manufacturing Cost data not loaded, cannot calculate KPIs.")