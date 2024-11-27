import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Shopify Product Price Analysis",
    page_icon="💰",
    layout="wide"
)

st.title("Shopify Product Price Analysis")
st.write("Upload your Shopify products CSV file to analyze variant compare prices.")

def analyze_variant_prices(df):
    """Analyze variant compare prices in the Shopify products dataframe."""
    st.subheader("Variant Compare Price Analysis")
    
    # Create columns for statistics
    col1, col2, col3 = st.columns(3)
    
    # Get total unique products and variants
    total_products = len(df['Handle'].unique())
    total_variants = len(df[df['Variant Price'].notna()])
    
    # Initialize counters for products
    products_without_compare_price = set()
    products_with_missing_some_compare_price = set()
    total_missing_compare_prices = 0
    
    # Analyze each product's variants
    price_analysis = []
    for handle in df['Handle'].unique():
        product_variants = df[df['Handle'] == handle]
        total_product_variants = len(product_variants[product_variants['Variant Price'].notna()])
        
        if total_product_variants == 0:
            continue
            
        # Count variants with missing or zero compare price
        missing_compare_price = product_variants[
            (product_variants['Variant Compare At Price'].isna()) | 
            (product_variants['Variant Compare At Price'] == '') |
            (product_variants['Variant Compare At Price'] == 0) |
            (product_variants['Variant Compare At Price'].astype(str) == 'nan')
        ]
        missing_count = len(missing_compare_price)
        total_missing_compare_prices += missing_count
        
        if missing_count == total_product_variants:
            products_without_compare_price.add(handle)
        elif missing_count > 0:
            products_with_missing_some_compare_price.add(handle)
            
        # Get variant information
        variant_info = []
        for _, variant in product_variants[product_variants['Variant Price'].notna()].iterrows():
            variant_details = {
                'Price': variant.get('Variant Price', 'N/A'),
                'Compare Price': variant.get('Variant Compare At Price', 'N/A')
            }
            
            # Add options if they exist
            for i in range(1, 4):  # Shopify supports up to 3 options
                option_name = f'Option{i} Name'
                option_value = f'Option{i} Value'
                if option_name in variant and option_value in variant:
                    if not pd.isna(variant[option_name]):
                        variant_details[variant[option_name]] = variant[option_value]
            
            variant_info.append(variant_details)
            
        price_analysis.append({
            'Handle': handle,
            'Title': product_variants['Title'].iloc[0],
            'Total Variants': total_product_variants,
            'Variants Missing Compare Price': missing_count,
            'Percentage Missing': round(missing_count / total_product_variants * 100 if total_product_variants > 0 else 0, 2),
            'Variant Details': variant_info
        })
    
    # Display summary statistics
    with col1:
        st.metric(
            "Total Products", 
            total_products,
            f"{total_variants} total variants"
        )
    
    with col2:
        st.metric(
            "Products with NO Compare Prices", 
            len(products_without_compare_price),
            f"{len(products_without_compare_price)/total_products*100:.1f}% of total"
        )
    
    with col3:
        st.metric(
            "Products with SOME Missing Compare Prices",
            len(products_with_missing_some_compare_price),
            f"{len(products_with_missing_some_compare_price)/total_products*100:.1f}% of total"
        )
    
    # Create and display detailed breakdown
    st.subheader("Detailed Price Analysis")
    
    # Add sorting functionality
    sort_by = st.selectbox(
        "Sort by:",
        ['Percentage Missing', 'Variants Missing Compare Price', 'Total Variants', 'Handle'],
        index=0
    )
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        show_filter = st.radio(
            "Show products:",
            ['All', 'Only Missing Compare Prices', 'Only Partial Missing Compare Prices'],
            horizontal=True
        )
    
    with col2:
        min_variants = st.number_input(
            "Minimum number of variants:",
            min_value=1,
            value=1
        )
    
    # Filter and sort the analysis
    filtered_analysis = price_analysis.copy()
    
    # Apply variant filter
    filtered_analysis = [p for p in filtered_analysis if p['Total Variants'] >= min_variants]
    
    # Apply missing prices filter
    if show_filter == 'Only Missing Compare Prices':
        filtered_analysis = [p for p in filtered_analysis if p['Percentage Missing'] == 100]
    elif show_filter == 'Only Partial Missing Compare Prices':
        filtered_analysis = [p for p in filtered_analysis if 0 < p['Percentage Missing'] < 100]
    
    # Sort the analysis
    filtered_analysis.sort(
        key=lambda x: x[sort_by] if sort_by != 'Handle' else x[sort_by].lower(),
        reverse=sort_by != 'Handle'
    )
    
    # Display each product's analysis
    for product in filtered_analysis:
        with st.expander(f"{product['Title']} ({product['Handle']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Total Variants:** {product['Total Variants']}")
                st.write(f"**Missing Compare Prices:** {product['Variants Missing Compare Price']}")
                st.write(f"**Percentage Missing:** {product['Percentage Missing']}%")
            
            # Display variant details in a table
            st.write("**Variant Details:**")
            variant_df = pd.DataFrame(product['Variant Details'])
            st.dataframe(variant_df, height=150)
    
    # Export functionality
    if st.button("Export Analysis to CSV"):
        # Create a flattened version of the analysis for export
        export_rows = []
        for product in filtered_analysis:
            for variant in product['Variant Details']:
                row = {
                    'Handle': product['Handle'],
                    'Title': product['Title'],
                    'Total Variants': product['Total Variants'],
                    'Missing Compare Prices': product['Variants Missing Compare Price'],
                    'Percentage Missing': product['Percentage Missing'],
                    'Variant Price': variant['Price'],
                    'Compare Price': variant['Compare Price']
                }
                # Add options
                for key, value in variant.items():
                    if key not in ['Price', 'Compare Price']:
                        row[f'Option: {key}'] = value
                export_rows.append(row)
        
        export_df = pd.DataFrame(export_rows)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download Price Analysis CSV",
            data=csv,
            file_name=f'price_analysis_{timestamp}.csv',
            mime='text/csv'
        )

def main():
    uploaded_file = st.file_uploader("Choose Shopify CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            st.info("Processing file...")
            df = pd.read_csv(uploaded_file)
            
            with st.expander("View Input Data Preview", expanded=True):
                st.dataframe(df, height=400)
            
            # Analyze the data
            analyze_variant_prices(df)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file is in the correct Shopify products format.")

if __name__ == "__main__":
    main()