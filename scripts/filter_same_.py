import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Shopify Option Optimizer",
    page_icon="🔄",
    layout="wide"
)

st.title("Shopify Option Optimizer")

def analyze_options(df, handle):
    """Analyze options for a specific product to identify constant values."""
    product_df = df[df['Handle'] == handle].copy()
    variant_rows = product_df[product_df['Image Position'].isna()]
    
    options_analysis = {}
    for i in range(1, 5):
        option_name = f'Option{i} Name'
        option_value = f'Option{i} Value'
        
        if option_name in variant_rows.columns and option_value in variant_rows.columns:
            unique_values = variant_rows[option_value].unique()
            if len(unique_values) == 1:  # Constant value across all variants
                options_analysis[option_name] = {
                    'is_constant': True,
                    'value': unique_values[0],
                    'original_position': i
                }
            else:
                options_analysis[option_name] = {
                    'is_constant': False,
                    'values': sorted(unique_values),
                    'original_position': i
                }
    
    return options_analysis

def optimize_product_structure(df):
    """Optimize the product structure by reorganizing options and removing duplicates."""
    optimized_rows = []
    
    # Process each product separately
    for handle in df['Handle'].unique():
        product_df = df[df['Handle'] == handle].copy()
        
        # Keep all image rows unchanged
        image_rows = product_df[product_df['Image Position'].notna()].copy()
        optimized_rows.append(image_rows)
        
        # Process variant rows
        variant_rows = product_df[product_df['Image Position'].isna()].copy()
        
        if not variant_rows.empty:
            # Analyze options
            options_analysis = analyze_options(df, handle)
            
            # Reorganize options (move non-constant options to front)
            variable_options = []
            constant_options = []
            
            for i in range(1, 5):
                option_name = f'Option{i} Name'
                if option_name in options_analysis:
                    if not options_analysis[option_name]['is_constant']:
                        variable_options.append((option_name, f'Option{i} Value'))
                    else:
                        constant_options.append((option_name, f'Option{i} Value'))
            
            # Create new variant rows with reorganized options
            new_variants = []
            seen_combinations = set()
            
            for _, row in variant_rows.iterrows():
                # Create option combination key
                combination = []
                for _, value_col in variable_options:
                    if pd.notna(row[value_col]):
                        combination.append(str(row[value_col]).strip())
                
                combination_key = tuple(combination)
                if combination_key not in seen_combinations:
                    seen_combinations.add(combination_key)
                    
                    new_row = row.copy()
                    
                    # Reorder options
                    for new_pos, (old_name, old_value) in enumerate(variable_options + constant_options, 1):
                        new_row[f'Option{new_pos} Name'] = row[old_name]
                        new_row[f'Option{new_pos} Value'] = row[old_value]
                    
                    # Clear unused option columns
                    for i in range(len(variable_options + constant_options) + 1, 5):
                        if f'Option{i} Name' in new_row:
                            new_row[f'Option{i} Name'] = ''
                        if f'Option{i} Value' in new_row:
                            new_row[f'Option{i} Value'] = ''
                    
                    new_variants.append(new_row)
            
            # Sort variants by option values
            sorted_variants = sorted(new_variants, key=lambda x: [
                str(x[f'Option{i} Value']) if pd.notna(x[f'Option{i} Value']) else ''
                for i in range(1, 5)
            ])
            
            optimized_rows.append(pd.DataFrame(sorted_variants))
    
    # Combine all rows back together
    result_df = pd.concat(optimized_rows, ignore_index=True)
    
    # Ensure all required columns are present
    standard_columns = ['Handle', 'Title', 'Body (HTML)', 'Published', 'Variant Price', 
                       'Variant Compare At Price', 'Tags', 'Image Src', 'Image Alt Text', 
                       'Image Position']
    option_columns = []
    for i in range(1, 5):
        option_columns.extend([f'Option{i} Name', f'Option{i} Value'])
    
    all_columns = standard_columns + option_columns
    for col in all_columns:
        if col not in result_df.columns:
            result_df[col] = ''
    
    # Reorder columns
    result_df = result_df[all_columns]
    
    return result_df

def show_optimization_analysis(df, optimized_df):
    """Show analysis of the optimization results."""
    st.subheader("Optimization Results")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Original Rows", len(df))
    with col2:
        st.metric("Optimized Rows", len(optimized_df))
    with col3:
        rows_removed = len(df) - len(optimized_df)
        st.metric("Rows Removed", rows_removed)
    
    # Show product-by-product analysis
    st.subheader("Product Analysis")
    analysis_data = []
    
    for handle in df['Handle'].unique():
        orig_count = len(df[df['Handle'] == handle])
        opt_count = len(optimized_df[optimized_df['Handle'] == handle])
        
        orig_variants = len(df[(df['Handle'] == handle) & (df['Image Position'].isna())])
        opt_variants = len(optimized_df[(optimized_df['Handle'] == handle) & 
                                      (optimized_df['Image Position'].isna())])
        
        analysis_data.append({
            'Handle': handle,
            'Original Rows': orig_count,
            'Optimized Rows': opt_count,
            'Original Variants': orig_variants,
            'Optimized Variants': opt_variants,
            'Duplicates Removed': orig_variants - opt_variants
        })
    
    st.dataframe(
        pd.DataFrame(analysis_data),
        column_config={
            'Handle': 'Product Handle',
            'Original Rows': 'Original Total Rows',
            'Optimized Rows': 'Optimized Total Rows',
            'Original Variants': 'Original Variants',
            'Optimized Variants': 'Optimized Variants',
            'Duplicates Removed': 'Duplicates Removed'
        },
        hide_index=True
    )

def main():
    st.write("""
    This tool optimizes Shopify product CSV files by:
    1. Removing duplicate variant combinations
    2. Reorganizing options (moving constants to the end)
    3. Sorting variants in a logical order
    """)
    
    uploaded_file = st.file_uploader("Choose Shopify Products CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Read CSV with all columns as strings initially
            df = pd.read_csv(uploaded_file, dtype=str)
            
            # Convert numeric columns where needed
            numeric_columns = ['Variant Price', 'Variant Compare At Price', 'Image Position']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
            
            tab1, tab2 = st.tabs(["Original Data", "Optimization"])
            
            with tab1:
                st.header("Original Data")
                st.dataframe(df, height=400)
            
            with tab2:
                st.header("Optimize Products")
                
                if st.button("Optimize Product Structure"):
                    optimized_df = optimize_product_structure(df)
                    
                    show_optimization_analysis(df, optimized_df)
                    
                    # Show preview of optimized data
                    with st.expander("View Optimized Data", expanded=True):
                        st.dataframe(optimized_df, height=400)
                    
                    # Create download button
                    csv = optimized_df.to_csv(index=False)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    st.download_button(
                        label="Download Optimized CSV",
                        data=csv,
                        file_name=f"optimized_products_{timestamp}.csv",
                        mime='text/csv'
                    )
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file has the correct Shopify product format.")

if __name__ == "__main__":
    main()