import pandas as pd 
import numpy as np
from datetime import datetime
import os
from itertools import product

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
    return list(set(values))

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
    # Get all option values from children
    size_values = get_option_values(children_df, 'sizes')
    texture_values = get_option_values(children_df, 'texture')
    thickness_values = get_option_values(children_df, 'thickness')
    
    # Parse images
    images = parse_images(parent_row['images'])
    if not images:
        images = [{'url': '', 'alt': ''}]
    
    rows = []
    base_row = create_base_row(parent_row)
    
    # Add first row with product details and first image
    first_row = base_row.copy()
    if images[0]['url']:
        first_row['Image Src'] = images[0]['url']
        first_row['Image Alt Text'] = images[0]['alt']
        first_row['Image Position'] = 1
    
    # Add option columns if they exist
    if size_values:
        first_row['Option1 Name'] = 'Size'
        first_row['Option1 Value'] = size_values[0]
    if texture_values:
        first_row['Option2 Name'] = 'Texture' 
        first_row['Option2 Value'] = texture_values[0]
    if thickness_values:
        first_row['Option3 Name'] = 'Thickness'
        first_row['Option3 Value'] = thickness_values[0]
    
    rows.append(first_row)
    
    # Add rows for additional images
    for idx, img in enumerate(images[1:], 2):
        img_row = {
            'Handle': str(parent_row['ID']),
            'Image Src': img['url'],
            'Image Alt Text': img['alt'], 
            'Image Position': idx
        }
        rows.append(img_row)
    
    # Create all variant combinations
    if size_values or texture_values or thickness_values:
        options = []
        if size_values:
            options.append(size_values)
        if texture_values:
            options.append(texture_values) 
        if thickness_values:
            options.append(thickness_values)
            
        for combination in product(*options):
            if combination == tuple([v[0] for v in options]):
                continue  # Skip first combination as it's in the first row
                
            variant_row = base_row.copy()
            for i, value in enumerate(combination):
                option_num = i + 1
                if i == 0 and size_values:
                    variant_row[f'Option{option_num} Name'] = 'Size'
                    variant_row[f'Option{option_num} Value'] = value
                elif i == 1 and texture_values:
                    variant_row[f'Option{option_num} Name'] = 'Texture'
                    variant_row[f'Option{option_num} Value'] = value
                elif i == 2 and thickness_values:
                    variant_row[f'Option{option_num} Name'] = 'Thickness'
                    variant_row[f'Option{option_num} Value'] = value
                    
            rows.append(variant_row)
            
    return rows

def convert_wordpress_to_shopify():
    # Read WordPress CSV
    df = pd.read_csv('data/wordpress.csv')
    
    # Get parent products (where post_parent is empty/NA)
    parent_products = df[pd.isna(df['post_parent'])]
    
    output_rows = []
    for _, parent_row in parent_products.iterrows():
        # Get children products for this parent
        children = df[df['post_parent'] == parent_row['ID']]
        
        # Create variant rows including images
        product_rows = create_variant_rows(parent_row, children)
        output_rows.extend(product_rows)
    
    # Convert to DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Create output folder if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'output/wordpress-{timestamp}.csv'
    output_df.to_csv(output_filename, index=False)
    print(f'Converted file saved as: {output_filename}')

if __name__ == "__main__":
    convert_wordpress_to_shopify()