import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import io

st.set_page_config(
    page_title="Shopify Product Analyzer",
    page_icon="📊",
    layout="wide"
)

def load_and_process_data(file):
    """Load and process the Shopify CSV data."""
    df = pd.read_csv(file)
    
    # Group by Handle to get product-level statistics
    product_stats = []
    for handle in df['Handle'].unique():
        product_data = df[df['Handle'] == handle]
        
        stats = {
            'Handle': handle,
            'Title': product_data['Title'].iloc[0],
            'Variants': len(product_data[product_data['Variant Price'].notna()]),
            'Images': len(product_data[product_data['Image Position'].notna()]),
            'Min Price': product_data['Variant Price'].min(),
            'Max Price': product_data['Variant Price'].max(),
            'Tags': product_data['Tags'].iloc[0],
            'Brand': product_data['Brand (product.metafields.custom.brand)'].iloc[0] if not pd.isna(product_data['Brand (product.metafields.custom.brand)'].iloc[0]) else 'No Brand'
        }
        product_stats.append(stats)
    
    return df, pd.DataFrame(product_stats)

def get_unique_tags(tags_series):
    """Extract unique tags from the Tags column."""
    all_tags = []
    for tags in tags_series.dropna():
        if isinstance(tags, str):
            all_tags.extend([tag.strip() for tag in tags.split(',')])
    return sorted(set(all_tags))

def analyze_tags(product_stats):
    """Analyze tags and create tag statistics."""
    tag_stats = defaultdict(lambda: {
        'product_count': 0,
        'total_variants': 0,
        'avg_price': 0.0,
        'products': []
    })
    
    for _, row in product_stats.iterrows():
        if pd.isna(row['Tags']):
            continue
            
        tags = [tag.strip() for tag in str(row['Tags']).split(',')]
        for tag in tags:
            tag_stats[tag]['product_count'] += 1
            tag_stats[tag]['total_variants'] += row['Variants']
            tag_stats[tag]['avg_price'] += row['Min Price']
            tag_stats[tag]['products'].append(row['Handle'])
    
    # Calculate averages
    for tag in tag_stats:
        tag_stats[tag]['avg_price'] /= tag_stats[tag]['product_count']
    
    return pd.DataFrame([
        {
            'Tag': tag,
            'Product Count': stats['product_count'],
            'Total Variants': stats['total_variants'],
            'Average Price': stats['avg_price'],
            'Products': ', '.join(stats['products'])
        }
        for tag, stats in tag_stats.items()
    ])

def find_blank_images(df, blank_url="https://kalash.gallery/wp-content/uploads/2023/03/blank.png"):
    """Find products and variants with blank images."""
    blank_images = []
    
    for handle in df['Handle'].unique():
        product_data = df[df['Handle'] == handle]
        
        # Check Image Src and Variant Image columns
        blank_in_main = product_data['Image Src'] == blank_url
        blank_in_variant = product_data['Variant Image'] == blank_url
        
        if blank_in_main.any() or blank_in_variant.any():
            blank_images.append({
                'Handle': handle,
                'Title': product_data['Title'].iloc[0],
                'Blank Main Images': blank_in_main.sum(),
                'Blank Variant Images': blank_in_variant.sum(),
                'Total Variants': len(product_data[product_data['Variant Price'].notna()]),
                'Affected Rows': len(product_data[blank_in_main | blank_in_variant])
            })
    
    return pd.DataFrame(blank_images)

def main():
    st.title("Shopify Product Data Analyzer")
    
    uploaded_file = st.file_uploader("Upload Shopify Products CSV", type=['csv'])
    
    if uploaded_file:
        df, product_stats = load_and_process_data(uploaded_file)
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "Product Overview", 
            "Tag Analysis", 
            "Blank Images",
            "Product Options"
        ])
        
        with tab1:
            # Overall Statistics
            st.header("Overall Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Products", len(product_stats))
            with col2:
                st.metric("Total Variants", product_stats['Variants'].sum())
            with col3:
                st.metric("Total Images", product_stats['Images'].sum())
            with col4:
                st.metric("Avg Price", f"${product_stats['Min Price'].mean():.2f}")
            
            # Filters and product details from original script
            st.header("Filters")
            col1, col2 = st.columns(2)
            
            with col1:
                price_range = st.slider(
                    "Price Range",
                    min_value=float(product_stats['Min Price'].min()),
                    max_value=float(product_stats['Max Price'].max()),
                    value=(float(product_stats['Min Price'].min()), float(product_stats['Max Price'].max()))
                )
            
            with col2:
                all_tags = get_unique_tags(product_stats['Tags'])
                selected_tags = st.multiselect("Filter by Tags", all_tags)
            
            # Apply filters
            filtered_stats = product_stats.copy()
            filtered_stats = filtered_stats[
                (filtered_stats['Min Price'] >= price_range[0]) &
                (filtered_stats['Max Price'] <= price_range[1])
            ]
            
            if selected_tags:
                filtered_stats = filtered_stats[
                    filtered_stats['Tags'].apply(lambda x: any(tag in str(x) for tag in selected_tags))
                ]
            
            st.dataframe(filtered_stats, hide_index=True)
            
            # Visualizations
            st.header("Visualizations")
            col1, col2 = st.columns(2)
            
            with col1:
                fig_price = px.histogram(
                    filtered_stats,
                    x='Min Price',
                    nbins=20,
                    title='Price Distribution'
                )
                st.plotly_chart(fig_price, use_container_width=True)
            
            with col2:
                variant_counts = filtered_stats['Variants'].value_counts().reset_index()
                variant_counts.columns = ['Variant Count', 'Number of Products']
                fig_variants = px.bar(
                    variant_counts,
                    x='Variant Count',
                    y='Number of Products',
                    title='Number of Products by Variant Count'
                )
                st.plotly_chart(fig_variants, use_container_width=True)
        
        with tab2:
            st.header("Tag Analysis")
            
            tag_stats = analyze_tags(product_stats)
            
            # Tag Statistics
            st.subheader("Tag Statistics")
            st.dataframe(
                tag_stats,
                column_config={
                    'Tag': 'Tag Name',
                    'Product Count': st.column_config.NumberColumn('Number of Products'),
                    'Total Variants': st.column_config.NumberColumn('Total Variants'),
                    'Average Price': st.column_config.NumberColumn('Average Price', format='$%.2f'),
                    'Products': 'Product Handles'
                },
                hide_index=True
            )
            
            # Tag Visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                fig_tag_products = px.bar(
                    tag_stats.sort_values('Product Count', ascending=True).tail(10),
                    x='Product Count',
                    y='Tag',
                    title='Top 10 Tags by Product Count',
                    orientation='h'
                )
                st.plotly_chart(fig_tag_products, use_container_width=True)
            
            with col2:
                fig_tag_variants = px.bar(
                    tag_stats.sort_values('Total Variants', ascending=True).tail(10),
                    x='Total Variants',
                    y='Tag',
                    title='Top 10 Tags by Total Variants',
                    orientation='h'
                )
                st.plotly_chart(fig_tag_variants, use_container_width=True)
            
            # Export Tag Statistics
            tag_stats_csv = tag_stats.to_csv(index=False)
            st.download_button(
                label="Download Tag Statistics CSV",
                data=tag_stats_csv,
                file_name="tag_statistics.csv",
                mime="text/csv"
            )
        
        with tab3:
            st.header("Blank Images Analysis")
            
            blank_images_df = find_blank_images(df)
            
            if not blank_images_df.empty:
                st.subheader("Products with Blank Images")
                st.dataframe(
                    blank_images_df,
                    column_config={
                        'Handle': 'Product Handle',
                        'Title': 'Product Title',
                        'Blank Main Images': st.column_config.NumberColumn('Blank Main Images'),
                        'Blank Variant Images': st.column_config.NumberColumn('Blank Variant Images'),
                        'Total Variants': st.column_config.NumberColumn('Total Variants'),
                        'Affected Rows': st.column_config.NumberColumn('Affected Rows')
                    },
                    hide_index=True
                )
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Products with Blank Images", len(blank_images_df))
                with col2:
                    st.metric("Total Blank Main Images", blank_images_df['Blank Main Images'].sum())
                with col3:
                    st.metric("Total Blank Variant Images", blank_images_df['Blank Variant Images'].sum())
                
                # Export Blank Images Data
                blank_images_csv = blank_images_df.to_csv(index=False)
                st.download_button(
                    label="Download Blank Images Report",
                    data=blank_images_csv,
                    file_name="blank_images_report.csv",
                    mime="text/csv"
                )
            else:
                st.info("No blank images found in the data.")
        
        with tab4:
            st.header("Product Options Analysis")
            
            # Get unique option names
            option_names = []
            for i in range(1, 4):
                option_col = f'Option{i} Name'
                if option_col in df.columns:
                    unique_options = df[option_col].dropna().unique()
                    option_names.extend(unique_options)
            option_names = list(set(option_names))
            
            if option_names:
                for option_name in option_names:
                    option_values = []
                    for i in range(1, 4):
                        mask = df[f'Option{i} Name'] == option_name
                        values = df[mask][f'Option{i} Value'].dropna()
                        option_values.extend(values)
                    
                    if option_values:
                        value_counts = pd.Series(option_values).value_counts()
                        
                        st.subheader(f"{option_name} Distribution")
                        fig = px.pie(
                            names=value_counts.index,
                            values=value_counts.values,
                            title=f"Distribution of {option_name}"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No product options found in the data.")

if __name__ == "__main__":
    main()