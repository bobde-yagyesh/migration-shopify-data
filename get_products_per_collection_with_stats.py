import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter

st.set_page_config(
    page_title="Product Tag Analyzer",
    page_icon="🏷️",
    layout="wide"
)

st.title("Product Tag Analyzer")

def get_unique_tags(df):
    """Extract all unique tags from the Tags column."""
    all_tags = []
    for tags in df['Tags'].dropna():
        tags_list = [tag.strip() for tag in tags.split(',')]
        all_tags.extend(tags_list)
    return sorted(set(all_tags))

def count_products_per_tag(df):
    """Count how many unique products belong to each tag."""
    tag_counts = Counter()
    
    for idx, row in df.drop_duplicates(subset='Handle').iterrows():
        if pd.notna(row['Tags']):
            tags = [tag.strip() for tag in row['Tags'].split(',')]
            for tag in tags:
                tag_counts[tag] += 1
                
    return pd.DataFrame(
        {'Tag': list(tag_counts.keys()), 
         'Product Count': list(tag_counts.values())}
    ).sort_values('Product Count', ascending=False)

def filter_products_by_tags(df, selected_tags, match_all=False):
    """Filter products based on selected tags."""
    if not selected_tags:
        return df
    
    # Get unique products first
    unique_products = df.drop_duplicates(subset='Handle')
    
    if match_all:
        # Products must have all selected tags
        filtered_products = unique_products[
            unique_products['Tags'].apply(
                lambda x: all(tag in str(x) for tag in selected_tags)
            )
        ]
    else:
        # Products must have any of the selected tags
        filtered_products = unique_products[
            unique_products['Tags'].apply(
                lambda x: any(tag in str(x) for tag in selected_tags)
            )
        ]
    
    # Return all rows for the filtered products
    return df[df['Handle'].isin(filtered_products['Handle'])]

def main():
    uploaded_file = st.file_uploader("Choose Shopify Products CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Create tabs for different views
            tab1, tab2 = st.tabs(["Tag Analysis", "Product Search"])
            
            with tab1:
                st.header("Tag Analysis")
                
                # Get tag statistics
                tag_stats = count_products_per_tag(df)
                
                # Create columns for metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Products", len(df['Handle'].unique()))
                with col2:
                    st.metric("Total Tags", len(tag_stats))
                with col3:
                    avg_tags_per_product = df['Tags'].str.count(',').mean() + 1
                    st.metric("Avg Tags per Product", f"{avg_tags_per_product:.1f}")
                
                # Display tag statistics
                st.subheader("Products per Tag")
                
                # Create bar chart
                fig = px.bar(
                    tag_stats,
                    x='Tag',
                    y='Product Count',
                    title='Number of Products per Tag',
                    height=400
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display detailed tag statistics
                st.dataframe(
                    tag_stats,
                    column_config={
                        'Tag': 'Tag Name',
                        'Product Count': st.column_config.NumberColumn(
                            'Number of Products',
                            help='Number of unique products with this tag'
                        )
                    },
                    hide_index=True
                )
            
            with tab2:
                st.header("Product Search by Tags")
                
                # Get all unique tags
                unique_tags = get_unique_tags(df)
                
                # Create tag selection
                selected_tags = st.multiselect(
                    "Select Tags to Filter Products",
                    options=unique_tags
                )
                
                # Add match type selector
                match_type = st.radio(
                    "Match Type",
                    ["Match Any Selected Tag", "Match All Selected Tags"],
                    horizontal=True
                )
                
                match_all = match_type == "Match All Selected Tags"
                
                # Filter products based on selected tags
                if selected_tags:
                    filtered_df = filter_products_by_tags(df, selected_tags, match_all)
                    
                    st.metric(
                        "Filtered Products", 
                        len(filtered_df['Handle'].unique())
                    )
                    
                    # Show filtered products
                    st.subheader("Filtered Products")
                    
                    # Group by Handle and show key information
                    product_summary = filtered_df.groupby('Handle').agg({
                        'Title': 'first',
                        'Tags': 'first',
                        'Variant Price': lambda x: ', '.join(x.dropna().astype(str)),
                        'Option1 Value': lambda x: ', '.join(x.dropna().astype(str))
                    }).reset_index()
                    
                    st.dataframe(
                        product_summary,
                        column_config={
                            'Handle': 'Product Handle',
                            'Title': 'Product Title',
                            'Tags': 'Tags',
                            'Variant Price': 'Prices',
                            'Option1 Value': 'Variants'
                        },
                        hide_index=True
                    )
                else:
                    st.info("Please select one or more tags to filter products")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file has the correct format with required columns: Handle, Title, Tags")

if __name__ == "__main__":
    main()