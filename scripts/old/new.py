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
    """Parse image string into list of dictionaries containing URL and alt text."""
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

def get_all_attribute_values(df, attribute_name):
    """Get all unique values for a given attribute across parent and child products."""
    values = set()
    
    # Check only meta:attribute_pa_ columns
    meta_col = f'meta:attribute_pa_{attribute_name}'
    if meta_col in df.columns:
        # Get values from both parent and child rows
        all_values = df[meta_col].dropna()
        for val in all_values:
            # Handle both string and numeric values
            try:
                if isinstance(val, (int, float)):
                    # Handle numeric values
                    values.add(str(int(val))) # Convert float to int to string to remove decimals
                else:
                    # Handle string values that might have delimiters
                    for v in str(val).split('|'):
                        if v.strip():
                            values.add(v.strip())
            except:
                # If any conversion fails, just add the original value
                if val:
                    values.add(str(val))
    
    return sorted(list(values))

def get_valid_attributes(df):
    """Get attributes that have values, excluding brand."""
    # Only look for meta:attribute_pa_ columns
    meta_cols = [col for col in df.columns if col.startswith('meta:attribute_pa_') and col != 'meta:attribute_pa_brand']
    valid_attrs = []
    
    for col in meta_cols:
        attr_name = col.replace('meta:attribute_pa_', '')
        values = get_all_attribute_values(df, attr_name)
        if values:  # Include if there are any values
            valid_attrs.append(attr_name)
    
    return sorted(valid_attrs)

def get_variant_image(variant_row, parent_images, attribute_values):
    """Get the appropriate image URL for a variant."""
    if not pd.isna(variant_row['images']):
        # If variant has its own image, use it
        variant_images = parse_images(variant_row['images'])
        return variant_images[0]['url'] if variant_images else ''
    
    # If variant has no image, find matching parent image based on attributes
    for img in parent_images:
        img_url = img['url'].lower()
        for attr_val in attribute_values:
            if attr_val.lower() in img_url:
                return img['url']
    
    # If no match found, return empty string
    return ''

def get_brand_from_children(children_df, parent_row):
    """Get brand value from children rows."""
    # if len(parent_row['meta:attribute_pa_brand']) > 1:
    #     return parent_row['meta:attribute_pa_brand'] 
    if not children_df.empty:
        brand_values = children_df['meta:attribute_pa_brand'].dropna()
        if not brand_values.empty:
            return brand_values.iloc[0]
    return ''

def create_variant_rows(parent_row, children_df, valid_attrs, single_tag=None):
    """Create variant rows with comprehensive attribute processing."""
    # Base setup
    brand_value = get_brand_from_children(children_df, parent_row)
    base_row = {
        'Handle': parent_row['post_title'],
        'Title': parent_row['post_title'],
        'Body (HTML)': parent_row['post_excerpt'] if not pd.isna(parent_row['post_excerpt']) else '',
        'Published': str(parent_row['post_status'] == 'publish').lower(),
        'Tags': single_tag if single_tag else parent_row.get('tax:product_cat', ''),
        'Brand (product.metafields.custom.brand)': brand_value
    }
    
    parent_images = parse_images(parent_row['images'])
    rows = []
    
    # Collect all attribute values comprehensively
    attribute_values = {}
    for attr in valid_attrs:
        values = set()
        
        # Get values from parent
        parent_values = get_all_attribute_values(pd.DataFrame([parent_row]), attr)
        values.update(parent_values)
        
        # Get values from children
        if not children_df.empty:
            child_values = get_all_attribute_values(children_df, attr)
            values.update(child_values)
            
        if values:
            attribute_values[attr] = sorted(list(values))
    
    # Create first row with parent data
    first_row = base_row.copy()
    if parent_images:
        first_row['Image Src'] = parent_images[0]['url']
        first_row['Image Alt Text'] = parent_images[0]['alt']
        first_row['Image Position'] = 1
    
    # Add first variant data
    if not children_df.empty:
        first_variant = children_df.iloc[0]
        first_row['Variant Price'] = first_variant['regular_price'] if not pd.isna(first_variant['regular_price']) else ''
        first_row['Variant Compare At Price'] = first_variant['sale_price'] if not pd.isna(first_variant['sale_price']) else ''
        
        variant_image = get_variant_image(first_variant, parent_images, [])
        if variant_image:
            first_row['Variant Image'] = variant_image
        
        # Add options from first variant
        for idx, (attr_name, values) in enumerate(attribute_values.items(), 1):
            col_name = f'meta:attribute_pa_{attr_name}'
            if col_name in first_variant and not pd.isna(first_variant[col_name]):
                value = str(first_variant[col_name])
                if '|' in value:
                    value = value.split('|')[0].strip()
                first_row[f'Option{idx} Name'] = attr_name.capitalize()
                first_row[f'Option{idx} Value'] = value
    
    rows.append(first_row)
    
    # Add remaining parent images
    for idx, img in enumerate(parent_images[1:], 2):
        img_row = {
            'Handle': parent_row['post_title'],
            'Image Src': img['url'],
            'Image Alt Text': img['alt'],
            'Image Position': idx,
            'Tags': base_row['Tags'],
            'Brand (product.metafields.custom.brand)': brand_value
        }
        rows.append(img_row)
    
    # Create all possible variant combinations
    if attribute_values:
        attr_names = list(attribute_values.keys())
        attr_values = [attribute_values[name] for name in attr_names]
        
        for variant_values in product(*attr_values):
            # Skip first combination as it's already handled
            if variant_values == tuple(v[0] for v in attr_values):
                continue
                
            variant_row = base_row.copy()
            
            # Find matching child row
            matching_child = None
            for _, child in children_df.iterrows():
                matches = True
                for attr_name, value in zip(attr_names, variant_values):
                    col_name = f'meta:attribute_pa_{attr_name}'
                    if col_name in child and not pd.isna(child[col_name]):
                        child_value = str(child[col_name])
                        child_values = [v.strip() for v in child_value.split('|')] if '|' in child_value else [child_value]
                        if str(value) not in child_values:
                            matches = False
                            break
                if matches:
                    matching_child = child
                    break
            
            # Add variant-specific data
            if matching_child is not None:
                variant_row['Variant Price'] = matching_child['regular_price'] if not pd.isna(matching_child['regular_price']) else ''
                variant_row['Variant Compare At Price'] = matching_child['sale_price'] if not pd.isna(matching_child['sale_price']) else ''
                variant_image = get_variant_image(matching_child, parent_images, variant_values)
                if variant_image:
                    variant_row['Variant Image'] = variant_image
            
            # Add all option values
            for idx, (name, value) in enumerate(zip(attr_names, variant_values), 1):
                variant_row[f'Option{idx} Name'] = name.capitalize()
                variant_row[f'Option{idx} Value'] = str(value)
            
            rows.append(variant_row)
    
    return rows

def convert_wordpress_to_shopify(df, single_tag_mode=False):
    """Main conversion function."""
    parent_products = df[pd.isna(df['post_parent'])]
    valid_attrs = get_valid_attributes(df)  # This now excludes brand
    
    output_rows = []
    progress_bar = st.progress(0)
    
    if single_tag_mode:
        # Process one product per tag
        all_tags = set()
        for _, row in parent_products.iterrows():
            if not pd.isna(row.get('tax:product_cat')):
                tags = [t.strip() for t in row['tax:product_cat'].split('|')]
                all_tags.update(tags)
        
        total_tags = len(all_tags)
        for idx, tag in enumerate(sorted(all_tags)):
            for _, parent_row in parent_products.iterrows():
                if not pd.isna(parent_row.get('tax:product_cat')) and tag in parent_row['tax:product_cat']:
                    children = df[df['post_parent'] == parent_row['ID']]
                    product_rows = create_variant_rows(parent_row, children, valid_attrs, tag)
                    output_rows.extend(product_rows)
                    break
            
            progress = (idx + 1) / total_tags
            progress_bar.progress(progress)
    else:
        # Process all products
        total_products = len(parent_products)
        for idx, (_, parent_row) in enumerate(parent_products.iterrows()):
            children = df[df['post_parent'] == parent_row['ID']]
            product_rows = create_variant_rows(parent_row, children, valid_attrs)
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
                    'Tags': product_rows['Tags'].iloc[0] if 'Tags' in product_rows else '',
                    'Brand': product_rows['Brand (product.metafields.custom.brand)'].iloc[0] if 'Brand (product.metafields.custom.brand)' in product_rows else ''
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
                    'Tags': 'Tags',
                    'Brand': 'Brand'
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