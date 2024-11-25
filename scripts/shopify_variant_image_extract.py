import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np

def load_and_analyze_csv(file):
    """Load the CSV and analyze variant images."""
    df = pd.read_csv(file)
    
    # Group by Handle to analyze products
    products_with_variants = {}
    current_handle = None
    current_product = None
    
    for idx, row in df.iterrows():
        handle = row['Handle']
        
        # Check if this is a new product
        if handle != current_handle:
            # Save previous product if it exists
            if current_product is not None:
                products_with_variants[current_handle] = current_product
            
            # Start new product
            current_handle = handle
            current_product = {
                'title': row.get('Title', ''),
                'variants_with_images': 0,
                'total_variants': 0,
                'rows': [],
                'has_variant_images': False
            }
        
        # Add row to current product
        current_product['rows'].append(row)
        
        # Check if this row is a variant (has Option1 Name)
        if 'Option1 Name' in row and not pd.isna(row['Option1 Name']):
            current_product['total_variants'] += 1
            
            # Check if variant has an image
            if 'Variant Image' in row and not pd.isna(row['Variant Image']):
                current_product['variants_with_images'] += 1
                current_product['has_variant_images'] = True
    
    # Save last product
    if current_product is not None:
        products_with_variants[current_handle] = current_product
    
    return products_with_variants

def create_product_summary(products_data):
    """Create a summary DataFrame of products."""
    summary_data = []
    
    for handle, data in products_data.items():
        summary_data.append({
            'Handle': handle,
            'Title': data['title'],
            'Total Variants': data['total_variants'],
            'Variants with Images': data['variants_with_images'],
            'Has Variant Images': data['has_variant_images']
        })
    
    return pd.DataFrame(summary_data)

def extract_products_with_variant_images(products_data):
    """Create a DataFrame containing only products with variant images."""
    rows = []
    
    for handle, data in products_data.items():
        if data['has_variant_images']:
            rows.extend(data['rows'])
    
    return pd.DataFrame(rows)

def main():
    st.set_page_config(page_title="Variant Image Analyzer", layout="wide")
    st.title("Shopify Product Variant Image Analyzer")
    
    uploaded_file = st.file_uploader("Upload Shopify format CSV file", type=['csv'])
    
    if uploaded_file is not None:
        # Load and analyze the data
        products_data = load_and_analyze_csv(uploaded_file)
        
        # Create summary
        summary_df = create_product_summary(products_data)
        
        # Display statistics
        st.subheader("Analysis Summary")
        col1, col2, col3 = st.columns(3)
        
        total_products = len(summary_df)
        products_with_images = summary_df['Has Variant Images'].sum()
        
        with col1:
            st.metric("Total Products", total_products)
        with col2:
            st.metric("Products with Variant Images", int(products_with_images))
        with col3:
            percentage = (products_with_images / total_products * 100) if total_products > 0 else 0
            st.metric("Percentage with Variant Images", f"{percentage:.1f}%")
        
        # Filter options
        st.subheader("Product List")
        show_option = st.radio(
            "Show products:",
            ["All Products", "Only Products with Variant Images", "Only Products without Variant Images"]
        )
        
        # Filter summary based on selection
        if show_option == "Only Products with Variant Images":
            filtered_summary = summary_df[summary_df['Has Variant Images']]
        elif show_option == "Only Products without Variant Images":
            filtered_summary = summary_df[~summary_df['Has Variant Images']]
        else:
            filtered_summary = summary_df
        
        # Display filtered summary
        st.dataframe(
            filtered_summary,
            column_config={
                'Handle': 'Product Handle',
                'Title': 'Product Title',
                'Total Variants': 'Total Variants',
                'Variants with Images': 'Variants with Images',
                'Has Variant Images': 'Has Variant Images'
            },
            height=400
        )
        
        # Export options
        st.subheader("Export Options")
        if st.button("Export Products with Variant Images"):
            products_df = extract_products_with_variant_images(products_data)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'products_with_variant_images_{timestamp}.csv'
            
            # Create download button
            csv = products_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=filename,
                mime='text/csv'
            )
            
            st.success(f"Found {len(products_df['Handle'].unique())} products with variant images")
            
            # Show preview of export data
            with st.expander("Preview Export Data"):
                st.dataframe(products_df, height=400)

if __name__ == "__main__":
    main()