import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
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

def get_option_values(children_df, option_name):
    col_name = f'meta:attribute_pa_{option_name}'
    values = []
    for _, row in children_df.iterrows():
        if col_name in row and not pd.isna(row[col_name]):
            vals = [v.strip() for v in str(row[col_name]).split('|') if v.strip()]
            values.extend(vals)
    return sorted(list(set(values)))

def create_base_row(parent_row):
    return {
        'Handle': str(parent_row['ID']),
        'Title': parent_row['post_title'],
        'Body (HTML)': parent_row['post_excerpt'] if not pd.isna(parent_row['post_excerpt']) else '',
        'Published': str(parent_row['post_status'] == 'publish').lower(),
        'Variant Price': parent_row['regular_price'] if not pd.isna(parent_row['regular_price']) else '',
        'Variant Compare At Price': parent_row['sale_price'] if not pd.isna(parent_row['sale_price']) else ''
    }

def create_variant_rows(parent_row, children_df):
    size_values = get_option_values(children_df, 'sizes')
    texture_values = get_option_values(children_df, 'texture')
    thickness_values = get_option_values(children_df, 'thickness')
    
    images = parse_images(parent_row['images'])
    if not images:
        images = [{'url': '', 'alt': ''}]
    
    rows = []
    base_row = create_base_row(parent_row)
    
    first_row = base_row.copy()
    if images[0]['url']:
        first_row['Image Src'] = images[0]['url']
        first_row['Image Alt Text'] = images[0]['alt']
        first_row['Image Position'] = 1
    
    option_count = 1
    if size_values:
        first_row[f'Option{option_count} Name'] = 'Size'
        first_row[f'Option{option_count} Value'] = size_values[0]
        option_count += 1
        
    if texture_values:
        first_row[f'Option{option_count} Name'] = 'Texture'
        first_row[f'Option{option_count} Value'] = texture_values[0]
        option_count += 1
        
    if thickness_values:
        first_row[f'Option{option_count} Name'] = 'Thickness'
        first_row[f'Option{option_count} Value'] = thickness_values[0]
    
    rows.append(first_row)
    
    for idx, img in enumerate(images[1:], 2):
        img_row = {
            'Handle': str(parent_row['ID']),
            'Image Src': img['url'],
            'Image Alt Text': img['alt'], 
            'Image Position': idx
        }
        rows.append(img_row)
    
    if size_values or texture_values or thickness_values:
        options = []
        option_names = []
        
        if size_values:
            options.append(size_values)
            option_names.append('Size')
        if texture_values:
            options.append(texture_values)
            option_names.append('Texture')
        if thickness_values:
            options.append(thickness_values)
            option_names.append('Thickness')
            
        for combination in product(*options):
            if combination == tuple([v[0] for v in options]):
                continue
                
            variant_row = base_row.copy()
            
            for i, (name, value) in enumerate(zip(option_names, combination), 1):
                variant_row[f'Option{i} Name'] = name
                variant_row[f'Option{i} Value'] = value
                    
            rows.append(variant_row)
            
    return rows

def convert_wordpress_to_shopify(df):
    parent_products = df[pd.isna(df['post_parent'])]
    
    output_rows = []
    progress_bar = st.progress(0)
    total_products = len(parent_products)
    
    for idx, (_, parent_row) in enumerate(parent_products.iterrows()):
        children = df[df['post_parent'] == parent_row['ID']]
        product_rows = create_variant_rows(parent_row, children)
        output_rows.extend(product_rows)
        
        # Update progress bar
        progress = (idx + 1) / total_products
        progress_bar.progress(progress)
    
    output_df = pd.DataFrame(output_rows)
    progress_bar.empty()
    
    return output_df

def main():
    uploaded_file = st.file_uploader("Choose WordPress CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            st.info("Processing uploaded file...")
            df = pd.read_csv(uploaded_file)
            
            # Show input data preview
            st.subheader("Input Data Preview")
            st.dataframe(df.head())
            
            if st.button("Convert to Shopify Format"):
                output_df = convert_wordpress_to_shopify(df)
                
                # Show statistics
                st.subheader("Conversion Statistics")
                col1, col2, col3 = st.columns(3)
                
                # Count unique handles (products)
                unique_products = len(output_df['Handle'].unique())
                total_rows = len(output_df)
                avg_variants = total_rows / unique_products if unique_products > 0 else 0
                
                with col1:
                    st.metric("Total Unique Products", unique_products)
                with col2:
                    st.metric("Total Rows (incl. variants)", total_rows)
                with col3:
                    st.metric("Average Rows per Product", f"{avg_variants:.1f}")
                
                # Show output preview
                # Add detailed product breakdown
                with st.expander("View Detailed Product Breakdown"):
                    # Get counts of variants and images per product
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
                            'Total Rows': len(product_rows)
                        })
                    
                    breakdown_df = pd.DataFrame(product_breakdown)
                    st.dataframe(
                        breakdown_df,
                        column_config={
                            'Handle': 'Product Handle',
                            'Title': 'Product Title',
                            'Variants': 'Number of Variants',
                            'Images': 'Number of Images',
                            'Total Rows': 'Total Rows'
                        },
                        height=400
                    )
                
                # Show output preview
                st.subheader("Output Preview")
                st.dataframe(output_df.head())
                
                # Create download button
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f'wordpress-to-shopify_{timestamp}.csv'
                
                csv = output_df.to_csv(index=False)
                st.download_button(
                    label="Download Converted CSV",
                    data=csv,
                    file_name=output_filename,
                    mime='text/csv'
                )
                
                st.success(f"Conversion completed! Click the button above to download.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please make sure your CSV file has the correct format and required columns.")

if __name__ == "__main__":
    main()