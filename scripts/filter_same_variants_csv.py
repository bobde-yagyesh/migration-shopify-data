import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(
    page_title="Shopify Product Optimizer",
    page_icon="🔄",
    layout="wide"
)

st.title("Shopify Product Optimizer")

def get_option_combination(row):
    """
    Get the combination of all option values for a row.
    Returns tuple of (option values) which uniquely identifies a variant.
    """
    options = []
    for i in range(1, 5):  # Support up to 4 options
        value_col = f'Option{i} Value'
        if value_col in row and pd.notna(row[value_col]):
            options.append(str(row[value_col]).strip())
    return tuple(options)

def find_duplicates(df):
    """Find duplicate variants based on handle and option combinations."""
    duplicate_info = []
    
    # Process each product separately
    for handle in df['Handle'].unique():
        product_df = df[df['Handle'] == handle].copy()
        
        # Skip image rows (they're not variants)
        variant_rows = product_df[product_df['Image Position'].isna()].copy()
        
        if not variant_rows.empty:
            # Create a combination key for each variant
            variant_rows['option_key'] = variant_rows.apply(get_option_combination, axis=1)
            
            # Find duplicates
            for option_key, group in variant_rows.groupby('option_key'):
                if len(group) > 1:
                    # This is a duplicate variant
                    duplicate_info.append({
                        'Handle': handle,
                        'Options': ' / '.join(option_key),
                        'Line Numbers': ', '.join(map(str, group.index + 2)),  # +2 for Excel-style line numbers
                        'Duplicate Count': len(group),
                        'Original Line': str(group.index[0] + 2)
                    })
    
    return duplicate_info

def optimize_products(df):
    """Remove duplicate variants while preserving product structure."""
    optimized_rows = []
    duplicate_info = []
    
    # Process each product separately
    for handle in df['Handle'].unique():
        product_df = df[df['Handle'] == handle].copy()
        
        # Keep all image rows
        image_rows = product_df[product_df['Image Position'].notna()].copy()
        optimized_rows.append(image_rows)
        
        # Process variant rows
        variant_rows = product_df[product_df['Image Position'].isna()].copy()
        
        if not variant_rows.empty:
            # Create a combination key for each variant
            variant_rows['option_key'] = variant_rows.apply(get_option_combination, axis=1)
            
            # Find duplicates before removing them
            for option_key, group in variant_rows.groupby('option_key'):
                if len(group) > 1:
                    duplicate_info.append({
                        'Handle': handle,
                        'Options': ' / '.join(option_key),
                        'Line Numbers': ', '.join(map(str, group.index + 2)),
                        'Duplicate Count': len(group),
                        'Original Line': str(group.index[0] + 2)
                    })
            
            # Keep only first occurrence of each variant combination
            variant_rows = variant_rows.drop_duplicates(subset='option_key', keep='first')
            variant_rows = variant_rows.drop('option_key', axis=1)
            optimized_rows.append(variant_rows)
    
    # Combine all rows back together
    result_df = pd.concat(optimized_rows, ignore_index=True)
    
    return result_df, duplicate_info

def show_duplicate_analysis(duplicate_info):
    """Show detailed analysis of duplicates found."""
    if duplicate_info:
        st.subheader("Duplicate Variants Found")
        
        # Create DataFrame from duplicate info
        dup_df = pd.DataFrame(duplicate_info)
        
        # Show summary metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Products with Duplicates", len(dup_df['Handle'].unique()))
        with col2:
            total_dupes = dup_df['Duplicate Count'].sum() - len(dup_df)  # Subtract original variants
            st.metric("Total Duplicate Variants", total_dupes)
        
        # Show detailed breakdown
        st.markdown("### Detailed Duplicate Analysis")
        st.markdown("Each row shows a variant combination that appears multiple times. The 'Line Numbers' column shows all occurrences, and the 'Original Line' shows which one will be kept.")
        
        st.dataframe(
            dup_df,
            column_config={
                'Handle': 'Product Handle',
                'Options': 'Option Combination',
                'Line Numbers': 'All Occurrences (Line Numbers)',
                'Original Line': 'Line to Keep',
                'Duplicate Count': 'Times Found'
            },
            hide_index=True
        )

def main():
    st.write("""
    This tool helps fix Shopify product CSV files with duplicate variants. 
    It identifies duplicates by comparing the complete combination of option values for each product.
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
            
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Duplicate Analysis", "Optimization"])
            
            with tab1:
                st.header("Find Duplicate Variants")
                
                if st.button("Analyze for Duplicates"):
                    duplicate_info = find_duplicates(df)
                    
                    if duplicate_info:
                        show_duplicate_analysis(duplicate_info)
                    else:
                        st.success("No duplicate variants found!")
                    
                    # Show input data preview
                    with st.expander("View Input Data", expanded=False):
                        st.dataframe(df, height=400)
            
            with tab2:
                st.header("Remove Duplicates")
                
                if st.button("Optimize Products"):
                    optimized_df, duplicate_info = optimize_products(df)
                    
                    if duplicate_info:
                        st.warning("Duplicate variants were found and removed.")
                        show_duplicate_analysis(duplicate_info)
                    else:
                        st.success("No duplicate variants found!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Original Rows", len(df))
                    with col2:
                        st.metric("Optimized Rows", len(optimized_df))
                    
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