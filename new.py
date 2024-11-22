import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from itertools import product
import io

st.set_page_config(
    page_title="WordPress to Shopify Converter",
    page_icon="🛍️",
    layout="wide"
)

st.title("WordPress to Shopify Product Converter")
st.write("Upload your WordPress products CSV file to convert it to Shopify format.")

def parse_images(image_str):
    if pd.isna(image_str):
        return []
    
    images = []
    for img in image_str.split('|'):
        img = img.strip()
        if not img:
            continue
            
        parts = img.split('!')
        url = parts[0].strip()
        alt_text = ''
        for part in parts[1:]:
            if part.strip().startswith('alt :'):
                alt_text = part.replace('alt :', '').strip()
                break
                
        images.append({'url': url, 'alt': alt_text})
    return images

def extract_tags(category_str, single_tag_mode=False):
    """Extract tags from the tax:product_cat column."""
    if pd.isna(category_str):
        return []
    
    tags = []
    for category in category_str.split('|'):
        parts = [p.strip() for p in category.split('>')]
        if single_tag_mode:
            # For single tag mode, get tag between 2nd and 3rd '>'
            if len(parts) >= 2:
                tag = parts[1].strip()
                if tag:
                    tags.append(tag)
        else:
            # For normal mode, get the last tag
            if parts:
                tag = parts[-1].strip()
                if tag:
                    tags.append(tag)
    
    return sorted(set(tags))

def get_attribute_columns(df):
    """Get all meta:attribute_pa columns that have children with values."""
    attribute_cols = []
    meta_cols = [col for col in df.columns if col.startswith('meta:attribute_pa_')]
    
    for col in meta_cols:
        children_df = df[~pd.isna(df['post_parent'])]
        if not children_df.empty and col in children_df.columns:
            if children_df[col].notna().any():
                attribute_cols.append(col.replace('meta:attribute_pa_', ''))
    
    return sorted(attribute_cols)

def get_option_values(children_df, option_name):
    col_name = f'meta:attribute_pa_{option_name}'
    values = []
    for _, row in children_df.iterrows():
        if col_name in row and not pd.isna(row[col_name]):
            vals = [v.strip() for v in str(row[col_name]).split('|') if v.strip()]
            values.extend(vals)
    return sorted(list(set(values)))

def create_base_row(parent_row, single_tag_mode=False):
    tags = extract_tags(parent_row.get('tax:product_cat', ''), single_tag_mode)
    return {
        'Handle': parent_row['post_title'],
        'Title': parent_row['post_title'],
        'Body (HTML)': parent_row['post_excerpt'] if not pd.isna(parent_row['post_excerpt']) else '',
        'Published': str(parent_row['post_status'] == 'publish').lower(),
        'Variant Price': parent_row['regular_price'] if not pd.isna(parent_row['regular_price']) else '',
        'Variant Compare At Price': parent_row['sale_price'] if not pd.isna(parent_row['sale_price']) else '',
        'Tags': ', '.join(tags)
    }

def create_variant_rows(parent_row, children_df, attribute_cols, single_tag=None, single_tag_mode=False):
    attribute_values = {}
    for attr in attribute_cols:
        values = get_option_values(children_df, attr)
        if values:
            attribute_values[attr] = values
    
    images = parse_images(parent_row['images'])
    if not images:
        images = [{'url': '', 'alt': ''}]
    
    rows = []
    base_row = create_base_row(parent_row, single_tag_mode)
    
    if single_tag is not None:
        base_row['Tags'] = single_tag
    
    first_row = base_row.copy()
    if images[0]['url']:
        first_row['Image Src'] = images[0]['url']
        first_row['Image Alt Text'] = images[0]['alt']
        first_row['Image Position'] = 1
    
    option_count = 1
    for attr_name, values in attribute_values.items():
        first_row[f'Option{option_count} Name'] = attr_name.capitalize()
        first_row[f'Option{option_count} Value'] = values[0]
        option_count += 1
    
    rows.append(first_row)
    
    for idx, img in enumerate(images[1:], 2):
        img_row = {
            'Handle': parent_row['post_title'],
            'Image Src': img['url'],
            'Image Alt Text': img['alt'],
            'Image Position': idx,
            'Tags': base_row['Tags']
        }
        rows.append(img_row)
    
    if attribute_values:
        options = list(attribute_values.values())
        option_names = [name.capitalize() for name in attribute_values.keys()]
        
        for combination in product(*options):
            if combination == tuple([v[0] for v in options]):
                continue
                
            variant_row = base_row.copy()
            
            for i, (name, value) in enumerate(zip(option_names, combination), 1):
                variant_row[f'Option{i} Name'] = name
                variant_row[f'Option{i} Value'] = value
                    
            rows.append(variant_row)
            
    return rows

def convert_wordpress_to_shopify(df, single_tag_mode=False):
    parent_products = df[pd.isna(df['post_parent'])]
    attribute_cols = get_attribute_columns(df)
    
    output_rows = []
    progress_bar = st.progress(0)
    
    if single_tag_mode:
        all_tags = set()
        for _, row in parent_products.iterrows():
            tags = extract_tags(row.get('tax:product_cat', ''), single_tag_mode=True)
            all_tags.update(tags)
        
        tag_product_map = {}
        for tag in all_tags:
            for _, row in parent_products.iterrows():
                product_tags = extract_tags(row.get('tax:product_cat', ''), single_tag_mode=True)
                if tag in product_tags:
                    tag_product_map[tag] = row
                    break
        
        total_items = len(tag_product_map)
        for idx, (tag, parent_row) in enumerate(tag_product_map.items()):
            children = df[df['post_parent'] == parent_row['ID']]
            product_rows = create_variant_rows(parent_row, children, attribute_cols, 
                                            single_tag=tag, single_tag_mode=True)
            output_rows.extend(product_rows)
            
            progress = (idx + 1) / total_items
            progress_bar.progress(progress)
    else:
        total_products = len(parent_products)
        for idx, (_, parent_row) in enumerate(parent_products.iterrows()):
            children = df[df['post_parent'] == parent_row['ID']]
            product_rows = create_variant_rows(parent_row, children, attribute_cols, 
                                            single_tag_mode=False)
            output_rows.extend(product_rows)
            
            progress = (idx + 1) / total_products
            progress_bar.progress(progress)
    
    output_df = pd.DataFrame(output_rows)
    progress_bar.empty()
    
    return output_df

def show_statistics(output_df, container):
    with container:
        st.subheader("Conversion Statistics")
        col1, col2, col3 = st.columns(3)
        
        unique_products = len(output_df['Handle'].unique())
        unique_tags = len(set(tag.strip() for tags in output_df['Tags'].dropna() for tag in tags.split(',')))
        total_rows = len(output_df)
        
        with col1:
            st.metric("Total Unique Products", unique_products)
        
        with st.expander("View Detailed Product Breakdown", expanded=True):
            product_breakdown = []
            for handle in output_df['Handle'].unique():
                product_rows = output_df[output_df['Handle'] == handle]
                variant_rows = product_rows[product_rows['Variant Price'].notna()].shape[0]
                image_rows = product_rows[product_rows['Image Position'].notna()].shape[0]
                
                product_breakdown.append({
                    'Handle': handle,
                    'Title': product_rows['Title'].iloc[0] if 'Title' in product_rows else 'N/A',
                    'Variants': variant_rows,
                    'Images': image_rows,
                    'Total Rows': len(product_rows),
                    'Tags': product_rows['Tags'].iloc[0] if 'Tags' in product_rows else ''
                })
            
            breakdown_df = pd.DataFrame(product_breakdown)
            st.dataframe(
                breakdown_df,
                column_config={
                    'Handle': 'Product Handle',
                    'Title': 'Product Title',
                    'Variants': 'Number of Variants',
                    'Images': 'Number of Images',
                    'Total Rows': 'Total Rows',
                    'Tags': 'Tags'
                },
                height=400
            )

def create_download_button(output_df, prefix):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'{prefix}_{timestamp}.csv'
    
    csv = output_df.to_csv(index=False)
    st.download_button(
        label=f"Download {prefix}",
        data=csv,
        file_name=output_filename,
        mime='text/csv'
    )

def main():
    uploaded_file = st.file_uploader("Choose WordPress CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            st.info("Processing uploaded file...")
            df = pd.read_csv(uploaded_file)
            
            with st.expander("View Input Data Preview", expanded=True):
                st.dataframe(df, height=400)
            
            tab1, tab2 = st.tabs(["All Products", "One Product Per Tag"])
            
            if st.button("Convert to Shopify Format"):
                with tab1:
                    st.subheader("All Products Output")
                    output_df = convert_wordpress_to_shopify(df, single_tag_mode=False)
                    show_statistics(output_df, tab1)
                    
                    with st.expander("View Output Preview", expanded=True):
                        st.dataframe(output_df, height=400)
                    
                    create_download_button(output_df, "all_products")
                    st.success("All products conversion completed!")
                
                with tab2:
                    st.subheader("One Product Per Tag Output")
                    single_tag_df = convert_wordpress_to_shopify(df, single_tag_mode=True)
                    show_statistics(single_tag_df, tab2)
                    
                    with st.expander("View Output Preview", expanded=True):
                        st.dataframe(single_tag_df, height=400)
                    
                    create_download_button(single_tag_df, "one_product_per_tag")
                    st.success("One product per tag conversion completed!")
                
                st.session_state['all_products_df'] = output_df
                st.session_state['single_tag_df'] = single_tag_df
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file has the correct format and required columns.")
    
    elif 'all_products_df' in st.session_state:
        tab1, tab2 = st.tabs(["All Products", "One Product Per Tag"])
        
        with tab1:
            st.subheader("Previous All Products Conversion")
            show_statistics(st.session_state['all_products_df'], tab1)
            with st.expander("View Output Preview", expanded=True):
                st.dataframe(st.session_state['all_products_df'], height=400)
        
        with tab2:
            st.subheader("Previous One Product Per Tag Conversion")
            show_statistics(st.session_state['single_tag_df'], tab2)
            with st.expander("View Output Preview", expanded=True):
                st.dataframe(st.session_state['single_tag_df'], height=400)

if __name__ == "__main__":
    main()