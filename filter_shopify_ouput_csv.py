import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Shopify Product Filter Tool",
    page_icon="🔍",
    layout="wide"
)

def filter_products(df, filters):
    """Filter products based on specified criteria."""
    filtered_df = df.copy()
    product_handles = df['Handle'].unique()
    filtered_handles = set(product_handles)
    
    # Filter by variant images
    if filters.get('variant_image_filter') == 'With Variant Images':
        handles_with_variant_images = set()
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            if product_rows['Variant Image'].notna().any():
                handles_with_variant_images.add(handle)
        filtered_handles &= handles_with_variant_images
    elif filters.get('variant_image_filter') == 'Without Variant Images':
        handles_without_variant_images = set()
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            if not product_rows['Variant Image'].notna().any():
                handles_without_variant_images.add(handle)
        filtered_handles &= handles_without_variant_images

    # Filter by zero price
    if filters.get('price_filter') == 'Zero Price Products':
        handles_with_zero_price = set()
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            prices = pd.to_numeric(product_rows['Variant Price'], errors='coerce')
            if prices.eq(0).any() or prices.isna().all():
                handles_with_zero_price.add(handle)
        filtered_handles &= handles_with_zero_price
    elif filters.get('price_filter') == 'Non-Zero Price Products':
        handles_with_nonzero_price = set()
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            prices = pd.to_numeric(product_rows['Variant Price'], errors='coerce')
            if (prices > 0).any():
                handles_with_nonzero_price.add(handle)
        filtered_handles &= handles_with_nonzero_price
    # Filter by price range (only if not filtering by zero/non-zero)
    elif filters.get('price_filter') == 'Price Range' and (filters.get('min_price') or filters.get('max_price')):
        handles_in_price_range = set()
        min_price = float(filters.get('min_price', 0))
        max_price = float(filters.get('max_price', float('inf')))
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            prices = pd.to_numeric(product_rows['Variant Price'], errors='coerce').dropna()
            if len(prices) > 0 and (min_price <= prices).any() and (prices <= max_price).any():
                handles_in_price_range.add(handle)
        filtered_handles &= handles_in_price_range
    
    # Filter by number of variants
    if filters.get('min_variants') or filters.get('max_variants'):
        handles_in_variant_range = set()
        min_variants = int(filters.get('min_variants', 0))
        max_variants = int(filters.get('max_variants', float('inf')))
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            variant_count = len(product_rows[product_rows['Variant Price'].notna()])
            if min_variants <= variant_count <= max_variants:
                handles_in_variant_range.add(handle)
        filtered_handles &= handles_in_variant_range

    # Filter by specific tags
    if filters.get('tags'):
        handles_with_tags = set()
        tag_list = [tag.strip() for tag in filters['tags'].split(',')]
        for handle in product_handles:
            product_rows = df[df['Handle'] == handle]
            product_tags = str(product_rows['Tags'].iloc[0]) if not pd.isna(product_rows['Tags'].iloc[0]) else ''
            if any(tag in product_tags for tag in tag_list):
                handles_with_tags.add(handle)
        filtered_handles &= handles_with_tags
    
    # Limit number of products
    if filters.get('product_limit'):
        filtered_handles = set(list(filtered_handles)[:int(filters['product_limit'])])
    
    return filtered_df[filtered_df['Handle'].isin(filtered_handles)]

def show_filter_sidebar():
    """Display and collect filter options from sidebar."""
    st.sidebar.header("Filter Options")
    
    filters = {}
    
    # Variant Image Filter
    filters['variant_image_filter'] = st.sidebar.radio(
        "Filter by Variant Images",
        ['All Products', 'With Variant Images', 'Without Variant Images']
    )
    
    # Price Filter Options
    filters['price_filter'] = st.sidebar.radio(
        "Price Filter Type",
        ['All Prices', 'Zero Price Products', 'Non-Zero Price Products', 'Price Range']
    )
    
    # Show price range inputs only if Price Range is selected
    if filters['price_filter'] == 'Price Range':
        st.sidebar.subheader("Price Range")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            filters['min_price'] = st.number_input("Min Price", min_value=0.0, step=1.0)
        with col2:
            filters['max_price'] = st.number_input("Max Price", min_value=0.0, step=1.0)
    
    # Number of Variants Filter
    st.sidebar.subheader("Number of Variants")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        filters['min_variants'] = st.number_input("Min Variants", min_value=0, step=1)
    with col2:
        filters['max_variants'] = st.number_input("Max Variants", min_value=0, step=1)
    
    # Tag Filter
    filters['tags'] = st.sidebar.text_input(
        "Filter by Tags (comma-separated)",
        help="Enter tags to filter products. Multiple tags should be separated by commas."
    )
    
    # Product Limit
    filters['product_limit'] = st.sidebar.number_input(
        "Limit Number of Products", 
        min_value=0,
        step=1,
        help="Set to 0 for no limit"
    )
    
    return filters

def show_statistics(df):
    """Display statistics about the data."""
    st.subheader("Product Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate statistics
    unique_products = len(df['Handle'].unique())
    variant_counts = df.groupby('Handle').apply(lambda x: len(x[x['Variant Price'].notna()]))
    products_with_variants = sum(variant_counts > 1)
    products_with_images = df.groupby('Handle').apply(lambda x: x['Variant Image'].notna().any()).sum()
    
    # Calculate zero price products
    zero_price_products = df.groupby('Handle').apply(
        lambda x: pd.to_numeric(x['Variant Price'], errors='coerce').eq(0).any() or 
                 pd.to_numeric(x['Variant Price'], errors='coerce').isna().all()
    ).sum()
    
    with col1:
        st.metric("Total Products", unique_products)
    with col2:
        st.metric("Products with Variants", products_with_variants)
    with col3:
        st.metric("Products with Variant Images", int(products_with_images))
    with col4:
        st.metric("Zero Price Products", int(zero_price_products))
    
    # Product Breakdown
    st.subheader("Product Breakdown")
    product_breakdown = []
    for handle in df['Handle'].unique():
        product_rows = df[df['Handle'] == handle]
        variant_rows = len(product_rows[product_rows['Variant Price'].notna()])
        variant_images = product_rows['Variant Image'].notna().sum()
        
        # Safely calculate average price
        prices = pd.to_numeric(product_rows['Variant Price'], errors='coerce')
        avg_price = prices.mean() if not prices.empty else 0
        has_zero_price = prices.eq(0).any() or prices.isna().all()
        
        product_breakdown.append({
            'Handle': handle,
            'Title': product_rows['Title'].iloc[0] if 'Title' in product_rows else 'N/A',
            'Variants': variant_rows,
            'Variant Images': variant_images,
            'Average Price': avg_price,
            'Has Zero Price': 'Yes' if has_zero_price else 'No',
            'Tags': product_rows['Tags'].iloc[0] if 'Tags' in product_rows else '',
        })
    
    breakdown_df = pd.DataFrame(product_breakdown)
    st.dataframe(
        breakdown_df,
        column_config={
            'Handle': 'Product Handle',
            'Title': 'Product Title',
            'Variants': 'Number of Variants',
            'Variant Images': 'Number of Variant Images',
            'Average Price': st.column_config.NumberColumn(
                'Average Price',
                format="$%.2f"
            ),
            'Has Zero Price': 'Has Zero Price',
            'Tags': 'Tags'
        },
        height=400
    )

def main():
    st.title("Shopify Product Filter Tool")
    st.write("Upload your Shopify format CSV file to filter and analyze products.")
    
    uploaded_file = st.file_uploader("Choose Shopify CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Load data
            df = pd.read_csv(uploaded_file)
            st.session_state['original_df'] = df
            
            # Show original data preview
            with st.expander("View Original Data Preview", expanded=False):
                st.dataframe(df, height=400)
            
            # Get filters
            filters = show_filter_sidebar()
            
            # Filter data
            filtered_df = filter_products(df, filters)
            
            # Show statistics for filtered data
            show_statistics(filtered_df)
            
            # Show filtered data preview
            with st.expander("View Filtered Data Preview", expanded=True):
                st.dataframe(filtered_df, height=400)
            
            # Download options
            col1, col2 = st.columns(2)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            with col1:
                st.download_button(
                    label="Download Filtered Data",
                    data=filtered_df.to_csv(index=False),
                    file_name=f'filtered_products_{timestamp}.csv',
                    mime='text/csv'
                )
            
            # Show filter summary
            if len(df['Handle'].unique()) != len(filtered_df['Handle'].unique()):
                st.info(f"""
                    **Filter Summary:**
                    - Original Products: {len(df['Handle'].unique())}
                    - Filtered Products: {len(filtered_df['Handle'].unique())}
                    - Applied Filters:
                        * Image Filter: {filters['variant_image_filter']}
                        * Price Range: {f"${filters['min_price']} - ${filters['max_price']}" if filters['min_price'] or filters['max_price'] else 'No limit'}
                        * Variant Range: {f"{filters['min_variants']} - {filters['max_variants']}" if filters['min_variants'] or filters['max_variants'] else 'No limit'}
                        * Tags: {filters['tags'] if filters['tags'] else 'None'}
                        * Product Limit: {filters['product_limit'] if filters['product_limit'] else 'No limit'}
                """)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file is in the correct Shopify format.")

if __name__ == "__main__":
    main()