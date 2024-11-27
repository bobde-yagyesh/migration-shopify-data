import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Shopify Single Variant Product Analysis",
    page_icon="🔍",
    layout="wide"
)

st.title("Single Variant Product Analysis")
st.write("Upload your Shopify products CSV file to analyze products with only one variant.")

def analyze_single_variant_products(df):
    """Analyze products that have only one variant."""
    st.subheader("Single Variant Products Analysis")
    
    # Create columns for statistics
    col1, col2, col3 = st.columns(3)
    
    # Get products and their variant counts
    variant_counts = df[df['Variant Price'].notna()].groupby('Handle').size()
    single_variant_handles = variant_counts[variant_counts == 1].index
    
    # Get total unique products
    total_products = len(df['Handle'].unique())
    total_single_variant = len(single_variant_handles)
    
    # Analyze single variant products
    single_variant_analysis = []
    
    for handle in single_variant_handles:
        product_data = df[df['Handle'] == handle]
        variant_row = product_data[product_data['Variant Price'].notna()].iloc[0]
        
        # Get option information
        options = {}
        for i in range(1, 4):  # Shopify supports up to 3 options
            option_name = f'Option{i} Name'
            option_value = f'Option{i} Value'
            if option_name in variant_row and not pd.isna(variant_row[option_name]):
                options[variant_row[option_name]] = variant_row[option_value]
        
        analysis_row = {
            'Handle': handle,
            'Title': variant_row['Title'],
            'Variant Price': variant_row.get('Variant Price', 'N/A'),
            'Compare Price': variant_row.get('Variant Compare At Price', 'N/A'),
            'Has Options': len(options) > 0,
            'Number of Options': len(options),
            'Option Details': options,
            'Tags': variant_row.get('Tags', ''),
            'Brand': variant_row.get('Brand (product.metafields.custom.brand)', ''),
            'Total Images': len(product_data[product_data['Image Src'].notna()])
        }
        
        single_variant_analysis.append(analysis_row)
    
    # Display summary statistics
    with col1:
        st.metric(
            "Total Products", 
            total_products
        )
    
    with col2:
        st.metric(
            "Single Variant Products",
            total_single_variant,
            f"{(total_single_variant/total_products*100):.1f}% of total"
        )
    
    with col3:
        # Count products with options
        products_with_options = sum(1 for p in single_variant_analysis if p['Has Options'])
        st.metric(
            "Single Variants with Options",
            products_with_options,
            f"{(products_with_options/total_single_variant*100):.1f}% of single variants"
        )
    
    # Additional Statistics
    st.subheader("Single Variant Products Breakdown")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        option_filter = st.radio(
            "Show products:",
            ['All', 'With Options', 'Without Options'],
            horizontal=True
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by:",
            ['Handle', 'Title', 'Variant Price', 'Number of Options', 'Total Images']
        )
    
    # Filter and sort the analysis
    filtered_analysis = single_variant_analysis.copy()
    
    if option_filter == 'With Options':
        filtered_analysis = [p for p in filtered_analysis if p['Has Options']]
    elif option_filter == 'Without Options':
        filtered_analysis = [p for p in filtered_analysis if not p['Has Options']]
    
    # Sort the analysis
    filtered_analysis.sort(
        key=lambda x: (str(x[sort_by]).lower() if sort_by in ['Handle', 'Title'] 
                      else (float(str(x[sort_by]).replace('N/A', '0')) 
                           if sort_by == 'Variant Price' 
                           else x[sort_by]))
    )
    
    # Display detailed analysis
    for product in filtered_analysis:
        with st.expander(f"{product['Title']} ({product['Handle']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Basic Information:**")
                st.write(f"- Price: {product['Variant Price']}")
                st.write(f"- Compare Price: {product['Compare Price']}")
                st.write(f"- Number of Images: {product['Total Images']}")
                
            with col2:
                st.write("**Option Information:**")
                if product['Option Details']:
                    for option_name, option_value in product['Option Details'].items():
                        st.write(f"- {option_name}: {option_value}")
                else:
                    st.write("No options defined")
            
            if product['Tags']:
                st.write("**Tags:**", product['Tags'])
            if product['Brand']:
                st.write("**Brand:**", product['Brand'])
    
    # Export functionality
    if st.button("Export Analysis to CSV"):
        # Prepare data for export
        export_rows = []
        for product in filtered_analysis:
            row = {
                'Handle': product['Handle'],
                'Title': product['Title'],
                'Variant Price': product['Variant Price'],
                'Compare Price': product['Compare Price'],
                'Has Options': product['Has Options'],
                'Number of Options': product['Number of Options'],
                'Total Images': product['Total Images'],
                'Tags': product['Tags'],
                'Brand': product['Brand']
            }
            # Add options
            for i in range(3):  # Maximum 3 options in Shopify
                row[f'Option {i+1}'] = ' | '.join(
                    [f"{k}: {v}" for k, v in list(product['Option Details'].items())[i:i+1]]
                ) if i < len(product['Option Details']) else ''
            
            export_rows.append(row)
        
        export_df = pd.DataFrame(export_rows)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download Single Variant Analysis CSV",
            data=csv,
            file_name=f'single_variant_analysis_{timestamp}.csv',
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
            analyze_single_variant_products(df)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file is in the correct Shopify products format.")

if __name__ == "__main__":
    main()