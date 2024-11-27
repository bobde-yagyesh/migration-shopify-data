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
            if len(parts) >= 2:
                tag = parts[1].strip()
                if tag:
                    tags.append(tag)
        else:
            if parts:
                tag = parts[-1].strip()
                if tag:
                    tags.append(tag)
    
    return ', '.join(sorted(set(tags)))

def get_attribute_columns(df):
    """Get all meta:attribute_pa columns except brand that have values in children."""
    meta_cols = [col for col in df.columns if col.startswith('meta:attribute_pa_') and col != 'meta:attribute_pa_brand']
    valid_attrs = []
    
    for col in meta_cols:
        # Check if children have values for this attribute
        children_df = df[~pd.isna(df['post_parent'])]
        if not children_df.empty and col in children_df.columns:
            if children_df[col].notna().any():
                valid_attrs.append(col.replace('meta:attribute_pa_', ''))
    
    return sorted(valid_attrs)

def get_option_values(children_df, option_name):
    """Get all unique values for an option from children rows."""
    col_name = f'meta:attribute_pa_{option_name}'
    values = set()
    for _, row in children_df.iterrows():
        if col_name in row and not pd.isna(row[col_name]):
            try:
                if isinstance(row[col_name], (int, float)):
                    values.add(str(int(row[col_name])))
                else:
                    vals = [v.strip() for v in str(row[col_name]).split('|') if v.strip()]
                    values.update(vals)
            except:
                if row[col_name]:
                    values.add(str(row[col_name]))
    return sorted(list(values))

def get_variant_image(variant_row, parent_images, attribute_values, previous_image=''):
    """
    Get the appropriate image URL for a variant with cascading fallback logic.
    Args:
        variant_row: The current variant row
        parent_images: List of parent product images
        attribute_values: List of attribute values for matching
        previous_image: Image URL from the previous variant row (default empty)
    """
    # First try to get variant's own image
    if not pd.isna(variant_row['images']):
        variant_images = parse_images(variant_row['images'])
        if variant_images:
            return variant_images[0]['url']
    
    # Then try to find matching parent image based on attributes
    for img in parent_images:
        img_url = img['url'].lower()
        for attr_val in attribute_values:
            if str(attr_val).lower() in img_url:
                return img['url']
    
    # If no match found, return previous image if available
    if previous_image:
        return previous_image
    
    # If all attempts fail, return empty string
    return ''

def get_brand_from_children(children_df, parent_row):
    """Get brand value from children rows."""
    if not children_df.empty:
        brand_values = children_df['meta:attribute_pa_brand'].dropna()
        if not brand_values.empty:
            return brand_values.iloc[0]
    return ''

def create_variant_rows(parent_row, children_df, attribute_cols, single_tag=None):
    """Create variant rows with comprehensive attribute processing."""
    brand_value = get_brand_from_children(children_df, parent_row)
    base_row = {
        'Handle': parent_row['post_title'],
        'Title': parent_row['post_title'],
        'Body (HTML)': parent_row['post_excerpt'] if not pd.isna(parent_row['post_excerpt']) else '',
        'Published': str(parent_row['post_status'] == 'publish').lower(),
        'Tags': single_tag if single_tag else extract_tags(parent_row.get('tax:product_cat', '')),
        'Brand (product.metafields.custom.brand)': brand_value
    }
    
    parent_images = parse_images(parent_row['images'])
    rows = []
    previous_variant_data = {
        'Variant Price': parent_row['regular_price'] if not pd.isna(parent_row['regular_price']) else '',
        'Variant Compare At Price': parent_row['sale_price'] if not pd.isna(parent_row['sale_price']) else '',
        'Variant Image': ''
    }
    
    # Get all attribute values
    attribute_values = {}
    for attr in attribute_cols:
        values = get_option_values(children_df, attr)
        if values:
            attribute_values[attr] = values
    
    # Create first row with parent data
    first_row = base_row.copy()
    if parent_images:
        first_row['Image Src'] = parent_images[0]['url']
        first_row['Image Alt Text'] = parent_images[0]['alt']
        first_row['Image Position'] = 1
    
    # If there are children, use first child's data, otherwise use parent's data
    if not children_df.empty:
        first_variant = children_df.iloc[0]
        first_row['Variant Price'] = first_variant['regular_price'] if not pd.isna(first_variant['regular_price']) else previous_variant_data['Variant Price']
        first_row['Variant Compare At Price'] = first_variant['sale_price'] if not pd.isna(first_variant['sale_price']) else previous_variant_data['Variant Compare At Price']
        
        variant_image = get_variant_image(first_variant, parent_images, [], '')
        if variant_image:
            first_row['Variant Image'] = variant_image
            
        # Update previous variant data
        previous_variant_data = {
            'Variant Price': first_row.get('Variant Price', ''),
            'Variant Compare At Price': first_row.get('Variant Compare At Price', ''),
            'Variant Image': first_row.get('Variant Image', '')
        }
        
        # Add options from first variant
        for idx, (attr_name, values) in enumerate(attribute_values.items(), 1):
            first_row[f'Option{idx} Name'] = attr_name.capitalize()
            first_row[f'Option{idx} Value'] = values[0]
    else:
        # Use parent data if no children
        first_row['Variant Price'] = previous_variant_data['Variant Price']
        first_row['Variant Compare At Price'] = previous_variant_data['Variant Compare At Price']
    
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
    
    # Create variant combinations only if we have children with attributes
    if attribute_values and not children_df.empty:
        attr_names = list(attribute_values.keys())
        attr_values = list(attribute_values.values())
        
        for variant_values in product(*attr_values):
            # Skip first combination as it's already handled
            if variant_values == tuple(v[0] for v in attr_values):
                continue
                
            variant_row = base_row.copy()
            
            # Find matching child row for pricing
            matching_child = None
            for _, child in children_df.iterrows():
                matches = True
                for attr_name, value in zip(attr_names, variant_values):
                    col_name = f'meta:attribute_pa_{attr_name}'
                    if col_name in child and not pd.isna(child[col_name]):
                        child_value = str(child[col_name])
                        if '|' in child_value:
                            child_values = [v.strip() for v in child_value.split('|')]
                        else:
                            child_values = [child_value]
                        if str(value) not in child_values:
                            matches = False
                            break
                if matches:
                    matching_child = child
                    break
            
            # If we have matching child data, use it
            if matching_child is not None:
                variant_row['Variant Price'] = matching_child['regular_price'] if not pd.isna(matching_child['regular_price']) else previous_variant_data['Variant Price']
                variant_row['Variant Compare At Price'] = matching_child['sale_price'] if not pd.isna(matching_child['sale_price']) else previous_variant_data['Variant Compare At Price']
                variant_image = get_variant_image(matching_child, parent_images, variant_values, previous_variant_data['Variant Image'])
                if variant_image:
                    variant_row['Variant Image'] = variant_image
            else:
                # If no matching child found, use previous variant's data
                variant_row['Variant Price'] = previous_variant_data['Variant Price']
                variant_row['Variant Compare At Price'] = previous_variant_data['Variant Compare At Price']
                variant_row['Variant Image'] = previous_variant_data['Variant Image']
            
            # Update previous variant data
            previous_variant_data = {
                'Variant Price': variant_row.get('Variant Price', ''),
                'Variant Compare At Price': variant_row.get('Variant Compare At Price', ''),
                'Variant Image': variant_row.get('Variant Image', '')
            }
            
            # Add option values
            for idx, (name, value) in enumerate(zip(attr_names, variant_values), 1):
                variant_row[f'Option{idx} Name'] = name.capitalize()
                variant_row[f'Option{idx} Value'] = value
            
            rows.append(variant_row)
    
    return rows

def convert_wordpress_to_shopify(df, single_tag_mode=False):
    """Main conversion function."""
    parent_products = df[pd.isna(df['post_parent'])]
    attribute_cols = get_attribute_columns(df)
    
    output_rows = []
    progress_bar = st.progress(0)
    total_products = len(parent_products)
    
    for idx, (_, parent_row) in enumerate(parent_products.iterrows()):
        children = df[df['post_parent'] == parent_row['ID']]
        product_rows = create_variant_rows(parent_row, children, attribute_cols)
        output_rows.extend(product_rows)
        progress = (idx + 1) / total_products
        progress_bar.progress(progress)
    
    output_df = pd.DataFrame(output_rows)
    progress_bar.empty()
    
    return output_df

def show_statistics(output_df):
    """Display statistics about the conversion."""
    st.subheader("Conversion Statistics")
    col1, col2, col3 = st.columns(3)
    
    unique_products = len(output_df['Handle'].unique())
    
    with col1:
        st.metric("Total Unique Products", unique_products)
    
    st.subheader("Detailed Product Breakdown")
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

def main():
    uploaded_file = st.file_uploader("Choose WordPress CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            st.info("Processing uploaded file...")
            df = pd.read_csv(uploaded_file)
            
            with st.expander("View Input Data Preview", expanded=True):
                st.dataframe(df, height=400)
            
            if st.button("Convert to Shopify Format"):
                output_df = convert_wordpress_to_shopify(df)
                st.session_state['output_df'] = output_df
                
                show_statistics(output_df)
                
                with st.expander("View Output Preview", expanded=True):
                    st.dataframe(output_df, height=400)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f'wordpress_to_shopify_{timestamp}.csv'
                
                csv = output_df.to_csv(index=False)
                st.download_button(
                    label="Download Converted CSV",
                    data=csv,
                    file_name=output_filename,
                    mime='text/csv'
                )
                
                st.success("Conversion completed!")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file has the correct format and required columns.")
    
    elif 'output_df' in st.session_state:
        st.subheader("Previous Conversion Output")
        show_statistics(st.session_state['output_df'])
        with st.expander("View Output Preview", expanded=True):
            st.dataframe(st.session_state['output_df'], height=400)


if __name__ == "__main__":
    main()