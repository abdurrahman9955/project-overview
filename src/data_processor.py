# src/data_processor.py

import pandas as pd
import os
# --- NEW: Import KPI calculation functions for testing purposes ---
from kpi_calculations import calculate_copq_kpis, calculate_oee_kpis, calculate_mfg_cost_kpis

def load_and_process_copq_data(file_path):
    """
    Loads and processes the COPQ data from a CSV file.
    Performs initial cleaning and prepares relevant sections.
    """
    try:
        raw_data = pd.read_csv(file_path, header=None, keep_default_na=False)
        data_sections = {}

        # --- Helper to find a section's precise start based on a primary and secondary keyword ---
        # This version is more flexible about whitespace and uses 'in' for secondary
        def find_section_start_flexible(primary_keyword, secondary_keyword=None, primary_col=0, secondary_col=None, df_raw=raw_data):
            for i, row in df_raw.iterrows():
                primary_cell_value = str(row[primary_col]).strip().lower() if primary_col < len(row) else ''
                primary_match = primary_keyword.lower() in primary_cell_value
                
                if primary_match:
                    if secondary_keyword:
                        if secondary_col is not None and secondary_col < len(row):
                            secondary_cell_value = str(row[secondary_col]).strip().lower()
                            secondary_match = secondary_keyword.lower() in secondary_cell_value
                            if secondary_match:
                                return i
                        else: # Search secondary keyword anywhere in the row (excluding primary_col)
                            if any(secondary_keyword.lower() in str(cell).strip().lower() for j, cell in enumerate(row) if j != primary_col and str(cell).strip()):
                                return i
                    else:
                        return i
            return -1

        # --- Section 1: BASIC PRODUCTION DATA - MONTHLY (Key-Value Pairs) ---
        start_idx = find_section_start_flexible('Total Units Produced', df_raw=raw_data)
        if start_idx != -1:
            basic_kpis = {}
            # Directly assign values based on their known relative positions
            basic_kpis['Total Units Produced'] = pd.to_numeric(raw_data.iloc[start_idx, 1], errors='coerce')
            basic_kpis['Defective Units'] = pd.to_numeric(raw_data.iloc[start_idx + 1, 1], errors='coerce')
            
            defect_rate_percent_str = str(raw_data.iloc[start_idx + 2, 1]).strip().replace('%', '')
            basic_kpis['Defect Rate (%)'] = pd.to_numeric(defect_rate_percent_str, errors='coerce') / 100
            
            basic_kpis['Defect Rate (PPM)'] = pd.to_numeric(raw_data.iloc[start_idx + 3, 1], errors='coerce')
            data_sections['basic_copq'] = pd.Series(basic_kpis)
        else:
            print("Warning: 'BASIC PRODUCTION DATA - MONTHLY' section not found in COPQ file.")

        # --- Section 2: COST OF QUALITY BREAKDOWN (Table) ---
        start_table_row = find_section_start_flexible('Category', df_raw=raw_data)
        if start_table_row != -1:
            df_breakdown_copq = raw_data.iloc[start_table_row + 1 : start_table_row + 5, :4].copy()
            df_breakdown_copq.columns = ['Category', 'Cost (£)', '% of Total COPQ', '% of Revenue']
            
            for col in ['Cost (£)']:
                df_breakdown_copq[col] = pd.to_numeric(df_breakdown_copq[col], errors='coerce')
            for col in ['% of Total COPQ', '% of Revenue']:
                df_breakdown_copq[col] = df_breakdown_copq[col].astype(str).str.replace('%', '', regex=False).astype(float) / 100
            data_sections['breakdown_copq'] = df_breakdown_copq
        else:
            print("Warning: 'COST OF QUALITY BREAKDOWN' section not found in COPQ file.")

        # --- Section 3: MONTHLY COPQ TRACKING (Table) ---
        # Find the header row by looking for "Month" in col 0 and "COPQ" (more lenient) in col 3
        start_table_row = -1
        for i, row in raw_data.iterrows():
            if str(row[0]).strip().lower() == 'month' and \
               len(row) > 3 and \
               'copq' in str(row[3]).strip().lower(): # Check for 'copq' more generally
                start_table_row = i
                break

        if start_table_row != -1:
            df_monthly_copq = raw_data.iloc[start_table_row + 1 : start_table_row + 7, :5].copy()
            # Explicitly set column names, using the correct 'COPQ (£)'
            df_monthly_copq.columns = ['Month', 'Total Units', 'Defective Units', 'COPQ (£)', 'COPQ % of Revenue']
            
            df_monthly_copq['Month'] = df_monthly_copq['Month'].astype(str).str.strip()
            df_monthly_copq['Month'] = pd.to_datetime(df_monthly_copq['Month'], format='%B', errors='coerce')
            df_monthly_copq = df_monthly_copq.dropna(subset=['Month']) # Ensures only valid dates proceed

            for col in ['Total Units', 'Defective Units', 'COPQ (£)']:
                df_monthly_copq[col] = pd.to_numeric(df_monthly_copq[col], errors='coerce')
            df_monthly_copq['COPQ % of Revenue'] = df_monthly_copq['COPQ % of Revenue'].astype(str).str.replace('%', '', regex=False).astype(float) / 100
            data_sections['monthly_copq_tracking'] = df_monthly_copq
        else:
            print("Warning: 'MONTHLY COPQ TRACKING' section not found in COPQ file. Check its exact header, especially 'COPQ (£)' or similar.")

        # --- Section 4: DEFECT CATEGORIES BREAKDOWN (Table) ---
        start_table_row = find_section_start_flexible('Defect Type', df_raw=raw_data)
        if start_table_row != -1:
            df_defect_categories = raw_data.iloc[start_table_row + 1 : start_table_row + 6, :4].copy()
            df_defect_categories.columns = ['Defect Type', 'Number of Occurrences', '% of Total Defects', 'Associated Cost (£)']
            
            for col in ['Number of Occurrences', 'Associated Cost (£)']:
                df_defect_categories[col] = pd.to_numeric(df_defect_categories[col], errors='coerce')
            df_defect_categories['% of Total Defects'] = df_defect_categories['% of Total Defects'].astype(str).str.replace('%', '', regex=False).astype(float) / 100
            data_sections['defect_categories'] = df_defect_categories
        else:
            print("Warning: 'DEFECT CATEGORIES BREAKDOWN' section not found in COPQ file.")

        return data_sections

    except FileNotFoundError:
        print(f"Error: COPQ file not found at {file_path}. Ensure it's named 'COPQ_Dummy_Data.csv' and is in the 'data' folder.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing COPQ data: {e}. This might indicate a problem with the file's structure beyond typical parsing issues.")
        return None

def load_and_process_oee_data(file_path):
    """
    Loads and processes the OEE data from a CSV file.
    Extracts different tables and cleans data types.
    """
    try:
        raw_data = pd.read_csv(file_path, header=None, keep_default_na=False)
        data_sections = {}

        # --- Helper to find a section's precise start based on a primary and secondary keyword ---
        def find_section_start_flexible_oee(primary_keyword, secondary_keyword=None, primary_col=0, secondary_col=None, df_raw=raw_data):
            for i, row in df_raw.iterrows():
                primary_cell_value = str(row[primary_col]).strip().lower() if primary_col < len(row) else ''
                primary_match = primary_keyword.lower() in primary_cell_value
                
                if primary_match:
                    if secondary_keyword:
                        if secondary_col is not None and secondary_col < len(row):
                            secondary_cell_value = str(row[secondary_col]).strip().lower()
                            secondary_match = secondary_keyword.lower() in secondary_cell_value
                            if secondary_match:
                                return i
                        else:
                            if any(secondary_keyword.lower() in str(cell).strip().lower() for j, cell in enumerate(row) if j != primary_col and str(cell).strip()):
                                return i
                    else:
                        return i
            return -1

        # --- Section 1: MONTHLY OEE & TEEP SUMMARY (Table) ---
        # Look for header row "Month" in col 0 and "OEE (%)" in col 4
        start_table_row = -1
        for i, row in raw_data.iterrows():
            if str(row[0]).strip().lower() == 'month' and \
               len(row) > 4 and \
               str(row[4]).strip().lower() == 'oee (%)':
                start_table_row = i
                break

        if start_table_row != -1:
            df_monthly_oee = raw_data.iloc[start_table_row + 1 : start_table_row + 6, :6].copy()
            df_monthly_oee.columns = ['Month', 'Availability (%)', 'Performance (%)', 'Quality (%)', 'OEE (%)', 'TEEP (%)']
            
            df_monthly_oee['Month'] = df_monthly_oee['Month'].astype(str).str.strip()
            df_monthly_oee['Month'] = pd.to_datetime(df_monthly_oee['Month'], format='%B', errors='coerce')
            df_monthly_oee = df_monthly_oee.dropna(subset=['Month'])

            for col in ['Availability (%)', 'Performance (%)', 'Quality (%)', 'OEE (%)', 'TEEP (%)']:
                df_monthly_oee[col] = df_monthly_oee[col].astype(str).str.replace('%', '', regex=False).astype(float) / 100
                df_monthly_oee[col] = pd.to_numeric(df_monthly_oee[col], errors='coerce')
            data_sections['monthly_oee'] = df_monthly_oee
        else:
            print("Warning: 'MONTHLY OEE & TEEP SUMMARY' section not found in OEE file. Check its exact header, especially 'OEE (%)'.")

        # --- Section 2: TEEP CALCULATION (DETAILED) (Table) ---
        start_table_row = -1
        for i, row in raw_data.iterrows():
            if str(row[0]).strip().lower() == 'month' and \
               len(row) > 1 and \
               str(row[1]).strip().lower() == 'scheduled shifts':
                start_table_row = i
                break

        if start_table_row != -1:
            df_teep_detailed = raw_data.iloc[start_table_row + 1 : start_table_row + 6, :6].copy()
            df_teep_detailed.columns = ['Month', 'Scheduled Shifts', 'Actual Shifts', 'Utilization (%)', 'OEE (%)', 'TEEP (%)']
            
            df_teep_detailed['Month'] = df_teep_detailed['Month'].astype(str).str.strip()
            df_teep_detailed['Month'] = pd.to_datetime(df_teep_detailed['Month'], format='%B', errors='coerce')
            df_teep_detailed = df_teep_detailed.dropna(subset=['Month'])

            for col in ['Scheduled Shifts', 'Actual Shifts']:
                df_teep_detailed[col] = pd.to_numeric(df_teep_detailed[col], errors='coerce')
            
            for col in ['Utilization (%)', 'OEE (%)']:
                df_teep_detailed[col] = df_teep_detailed[col].astype(str).str.replace('%', '', regex=False).astype(float) / 100
                df_teep_detailed[col] = pd.to_numeric(df_teep_detailed[col], errors='coerce')

            df_teep_detailed['TEEP (%)'] = (df_teep_detailed['Utilization (%)'] / 100) * (df_teep_detailed['OEE (%)'] / 100) * 100
            df_teep_detailed['TEEP (%)'] = pd.to_numeric(df_teep_detailed['TEEP (%)'], errors='coerce')
            data_sections['teep_detailed'] = df_teep_detailed
        else:
            print("Warning: 'TEEP CALCULATION (DETAILED)' section not found in OEE file. Check its exact header.")

        # --- Section 3: DOWNTIME COST ANALYSIS (Table) ---
        start_table_row = -1
        for i, row in raw_data.iterrows():
            if str(row[0]).strip().lower() == 'month' and \
               len(row) > 1 and \
               str(row[1]).strip().lower() == 'downtime (min)':
                start_table_row = i
                break

        if start_table_row != -1:
            df_downtime_cost = raw_data.iloc[start_table_row + 1 : start_table_row + 6, :5].copy()
            df_downtime_cost.columns = ['Month', 'Downtime (min)', 'Cost/Min (£)', 'Total Cost (£)', 'Root Cause (Top 3)']
            
            df_downtime_cost['Month'] = df_downtime_cost['Month'].astype(str).str.strip()
            df_downtime_cost['Month'] = pd.to_datetime(df_downtime_cost['Month'], format='%B', errors='coerce')
            df_downtime_cost = df_downtime_cost.dropna(subset=['Month'])

            for col in ['Downtime (min)', 'Cost/Min (£)', 'Total Cost (£)']:
                df_downtime_cost[col] = pd.to_numeric(df_downtime_cost[col], errors='coerce')
            data_sections['downtime_cost'] = df_downtime_cost
        else:
            print("Warning: 'DOWNTIME COST ANALYSIS' section not found in OEE file. Check its exact header.")

        # --- Section 4: MAINTENANCE COSTS BREAKDOWN (Table) ---
        start_table_row = -1
        for i, row in raw_data.iterrows():
            if str(row[0]).strip().lower() == 'month' and \
               len(row) > 1 and \
               str(row[1]).strip().lower() == 'preventive (£)':
                start_table_row = i
                break

        if start_table_row != -1:
            df_maintenance_costs = raw_data.iloc[start_table_row + 1 : start_table_row + 6, :6].copy()
            df_maintenance_costs.columns = ['Month', 'Preventive (£)', 'Corrective (£)', 'Downtime Cost (£)', 'Total (£)', '% of Revenue']
            
            df_maintenance_costs['Month'] = df_maintenance_costs['Month'].astype(str).str.strip()
            df_maintenance_costs['Month'] = pd.to_datetime(df_maintenance_costs['Month'], format='%B', errors='coerce')
            df_maintenance_costs = df_maintenance_costs.dropna(subset=['Month'])

            for col in ['Preventive (£)', 'Corrective (£)', 'Downtime Cost (£)', 'Total (£)']:
                df_maintenance_costs[col] = pd.to_numeric(df_maintenance_costs[col], errors='coerce')
            
            df_maintenance_costs['% of Revenue'] = df_maintenance_costs['% of Revenue'].astype(str).str.replace('%', '', regex=False).astype(float) / 100
            df_maintenance_costs['% of Revenue'] = pd.to_numeric(df_maintenance_costs['% of Revenue'], errors='coerce')

            data_sections['maintenance_costs'] = df_maintenance_costs
        else:
            print("Warning: 'MAINTENANCE COSTS BREAKDOWN' section not found in OEE file. Check its exact header.")

        return data_sections
    except FileNotFoundError:
        print(f"Error: OEE file not found at {file_path}. Ensure it's named 'OEE_Dummy_Data.csv' and is in the 'data' folder.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing OEE data: {e}. This might indicate a problem with the file's structure beyond typical parsing issues.")
        return None

def load_and_process_mfg_cost_data(file_path):
    """
    Loads and processes the Manufacturing Cost per Unit data from a CSV file.
    Extracts different tables and cleans data types.
    """
    try:
        raw_data = pd.read_csv(file_path, header=None, keep_default_na=False)
        data_sections = {}

        def find_section_start_mfg(keyword_part, df_raw, col_idx=0):
            matches = df_raw[df_raw[col_idx].astype(str).str.contains(keyword_part, na=False, case=False)]
            if not matches.empty:
                return matches.index[0]
            return -1

        # MONTHLY PRODUCTION DATA
        start_row_idx = find_section_start_mfg('MONTHLY PRODUCTION DATA', raw_data)
        if start_row_idx != -1:
            months_header_row = raw_data.iloc[start_row_idx + 1]
            total_units_produced_row = raw_data.iloc[start_row_idx + 2]
            
            months = [m.strip() for m in months_header_row.iloc[1:6].tolist() if str(m).strip()]
            values = [pd.to_numeric(v, errors='coerce') for v in total_units_produced_row.iloc[1:6].tolist()]
            
            df_production = pd.DataFrame([values], columns=months)
            df_production.index = ['Total Units Produced']
            df_production = df_production.T
            df_production.index.name = 'Month'
            df_production.index = pd.to_datetime(df_production.index, format='%B')
            df_production['Total Units Produced'] = pd.to_numeric(df_production['Total Units Produced'], errors='coerce')
            data_sections['production_data'] = df_production
        else:
            print("Warning: 'MONTHLY PRODUCTION DATA' section not found in Mfg Cost file.")

        # TOTAL MANUFACTURING COST
        start_row_idx = find_section_start_mfg('TOTAL MANUFACTURING COST', raw_data)
        if start_row_idx != -1:
            cost_categories = [
                'Total Direct Material Cost (£)', 'Total Direct Labor Cost (£)',
                'Total Manufacturing Overhead (£)', 'Total Manufacturing Cost (£)',
                'Manufacturing Cost per Unit (£)'
            ]
            months = ['January', 'February', 'March', 'April', 'May']
            
            df_total_cost = pd.DataFrame(index=months, columns=cost_categories)
            
            for category in cost_categories:
                row_found = raw_data[raw_data[0].astype(str).str.strip() == category].index
                if not row_found.empty:
                    row_idx = row_found[0]
                    values = pd.to_numeric(raw_data.iloc[row_idx, 1:6], errors='coerce').tolist()
                    df_total_cost.loc[months, category] = values
            
            df_total_cost.index.name = 'Month'
            df_total_cost.index = pd.to_datetime(df_total_cost.index, format='%B')
            data_sections['total_manufacturing_cost'] = df_total_cost
        else:
            print("Warning: 'TOTAL MANUFACTURING COST' section not found in Mfg Cost file.")


        # COST EFFICIENCY INDICATORS
        start_row_idx = find_section_start_mfg('COST EFFICIENCY INDICATORS', raw_data)
        if start_row_idx != -1:
            efficiency_kpis = ['Material Yield (%)', 'Labor Efficiency (%)', 'Capacity Utilization (%)']
            months = ['January', 'February', 'March', 'April', 'May']

            df_efficiency = pd.DataFrame(index=months, columns=efficiency_kpis)

            for kpi_name in efficiency_kpis:
                row_found = raw_data[raw_data[0].astype(str).str.strip() == kpi_name].index
                if not row_found.empty:
                    row_idx = row_found[0]
                    values = raw_data.iloc[row_idx, 1:6].astype(str).str.replace('%', '', regex=False).astype(float).tolist()
                    df_efficiency.loc[months, kpi_name] = [v / 100 for v in values]
            
            df_efficiency.index.name = 'Month'
            df_efficiency.index = pd.to_datetime(df_efficiency.index, format='%B')
            data_sections['efficiency_indicators'] = df_efficiency
        else:
            print("Warning: 'COST EFFICIENCY INDICATORS' section not found in Mfg Cost file.")


        # COST VARIANCE ANALYSIS
        start_row_idx = find_section_start_mfg('COST VARIANCE ANALYSIS', raw_data)
        if start_row_idx != -1:
            df_variance = raw_data.iloc[start_row_idx + 1 : start_row_idx + 7, :5].copy() # Header + 5 data rows
            df_variance.columns = ['Month_KPI', 'Actual', 'Budget', 'Variance (£)', 'Variance (%)']
            df_variance = df_variance[1:].reset_index(drop=True)
            
            for col in ['Actual', 'Budget', 'Variance (£)']:
                df_variance[col] = pd.to_numeric(df_variance[col], errors='coerce')
            df_variance['Variance (%)'] = df_variance['Variance (%)'].astype(str).str.replace('%', '', regex=False).astype(float) / 100
            
            data_sections['cost_variance'] = df_variance
        else:
            print("Warning: 'COST VARIANCE ANALYSIS' section not found in Mfg Cost file.")

        return data_sections

    except FileNotFoundError:
        print(f"Error: Manufacturing Cost file not found at {file_path}. Ensure it's named 'Manufacturing_Cost_per_Unit_Calculator.csv' and is in the 'data' folder.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing Manufacturing Cost data: {e}. Review the CSV content for unexpected characters or layout changes in the specified sections.")
        return None


# Example usage (for testing purposes, will not be part of the final app execution flow)
if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    data_dir = os.path.join(current_dir, '..', 'data')

    copq_file = os.path.join(data_dir, 'COPQ_Dummy_Data.csv')
    oee_file = os.path.join(data_dir, 'OEE_Dummy_Data.csv')
    mfg_cost_file = os.path.join(data_dir, 'Manufacturing_Cost_per_Unit_Calculator.csv')

    # --- ALL DATA LOADING FIRST ---
    print("--- Loading All Data ---")
    copq_raw_data = load_and_process_copq_data(copq_file)
    oee_raw_data = load_and_process_oee_data(oee_file)
    mfg_cost_raw_data = load_and_process_mfg_cost_data(mfg_cost_file)
    print("--- Data Loading Complete ---")

    # --- THEN ALL KPI CALCULATIONS ---

    print("\n--- Processing COPQ Data (and Calculating KPIs) ---")
    if copq_raw_data:
        copq_kpis, copq_augmented_data = calculate_copq_kpis(copq_raw_data)
        print("\nBasic COPQ Data:\n", copq_raw_data.get('basic_copq')) # Using raw_data for initial print
        print("\nCOPQ Breakdown Data:\n", copq_raw_data.get('breakdown_copq').head() if 'breakdown_copq' in copq_raw_data and copq_raw_data.get('breakdown_copq') is not None else None)
        print("\nMonthly COPQ Tracking Data:\n", copq_raw_data.get('monthly_copq_tracking').head() if 'monthly_copq_tracking' in copq_raw_data and copq_raw_data.get('monthly_copq_tracking') is not None else None)
        print("\nDefect Categories Data:\n", copq_raw_data.get('defect_categories').head() if 'defect_categories' in copq_raw_data and copq_raw_data.get('defect_categories') is not None else None)
        
        if copq_kpis:
            print("\nCalculated COPQ KPIs:", copq_kpis)
            if 'monthly_copq_tracking' in copq_augmented_data and copq_augmented_data['monthly_copq_tracking'] is not None:
                print("\nAugmented Monthly COPQ Tracking Data Head (from KPIs):", copq_augmented_data['monthly_copq_tracking'].head())
            if 'copq_breakdown' in copq_augmented_data and copq_augmented_data['copq_breakdown'] is not None:
                print("\nAugmented COPQ Breakdown Data Head (from KPIs):", copq_augmented_data['copq_breakdown'].head())
        else:
            print("COPQ KPIs calculation skipped due to missing data.")
    else:
        print("COPQ data loading failed, cannot process KPIs.")


    print("\n--- Processing OEE Data (and Calculating KPIs) ---")
    if oee_raw_data:
        oee_kpis, oee_augmented_data = calculate_oee_kpis(oee_raw_data)
        print("\nMonthly OEE Data Head:\n", oee_raw_data.get('monthly_oee').head() if oee_raw_data.get('monthly_oee') is not None else None)
        print("\nTEEP Detailed Data Head:\n", oee_raw_data.get('teep_detailed').head() if oee_raw_data.get('teep_detailed') is not None else None)
        print("\nDowntime Cost Data Head:\n", oee_raw_data.get('downtime_cost').head() if oee_raw_data.get('downtime_cost') is not None else None)
        print("\nMaintenance Costs Data Head:\n", oee_raw_data.get('maintenance_costs').head() if oee_raw_data.get('maintenance_costs') is not None else None)

        if oee_kpis:
            print("\nCalculated OEE KPIs:", oee_kpis)
            if 'monthly_oee_trends' in oee_augmented_data and oee_augmented_data['monthly_oee_trends'] is not None:
                print("\nAugmented Monthly OEE Trends Data Head (from KPIs):", oee_augmented_data['monthly_oee_trends'].head())
        else:
            print("OEE KPIs calculation skipped due to missing data.")
    else:
        print("OEE data loading failed, cannot process KPIs.")

    print("\n--- Processing Manufacturing Cost Data (and Calculating KPIs) ---")
    if mfg_cost_raw_data:
        mfg_cost_kpis, mfg_cost_augmented_data = calculate_mfg_cost_kpis(mfg_cost_raw_data)
        print("\nProduction Data Head:\n", mfg_cost_raw_data.get('production_data').head() if mfg_cost_raw_data.get('production_data') is not None else None)
        print("\nTotal Manufacturing Cost Head:\n", mfg_cost_raw_data.get('total_manufacturing_cost').head() if mfg_cost_raw_data.get('total_manufacturing_cost') is not None else None)
        print("\nEfficiency Indicators:\n", mfg_cost_raw_data.get('efficiency_indicators').head() if mfg_cost_raw_data.get('efficiency_indicators') is not None else None)
        print("\nCost Variance:\n", mfg_cost_raw_data.get('cost_variance').head() if mfg_cost_raw_data.get('cost_variance') is not None else None)

        if mfg_cost_kpis:
            print("\nCalculated Manufacturing Cost KPIs:", mfg_cost_kpis)
            if 'total_mfg_cost_trends' in mfg_cost_augmented_data and mfg_cost_augmented_data['total_mfg_cost_trends'] is not None:
                print("\nAugmented Total Manufacturing Cost Trends Data Head (from KPIs):", mfg_cost_augmented_data['total_mfg_cost_trends'].head())
        else:
            print("Manufacturing Cost KPIs calculation skipped due to missing data.")
    else:
        print("Manufacturing Cost data loading failed, cannot process KPIs.")
