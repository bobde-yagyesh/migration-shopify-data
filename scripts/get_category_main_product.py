import pandas as pd
import os

def create_category_samples(input_file, output_file='category_samples.csv'):
    """
    Create a CSV file with one parent product per unique tag from the input CSV.
    
    Args:
        input_file (str): Path to input Shopify CSV file
        output_file (str): Path to output CSV file
    """
    # Read CSV file with UTF-8 encoding
    df = pd.read_csv(input_file, encoding='utf-8')
    
    # Get parent products only (rows where Title matches Handle)
    parent_products = df[df['Title'] == df['Handle']].copy()
    
    # Initialize list to store one product per tag
    selected_products = []
    seen_tags = set()
    
    # Process each parent product
    for _, row in parent_products.iterrows():
        if pd.isna(row['Tags']):
            continue
            
        # Split tags and process each
        tags = [tag.strip() for tag in row['Tags'].split(',')]
        
        # Check each tag
        for tag in tags:
            if tag and tag not in seen_tags:
                # Add the tag to seen set
                seen_tags.add(tag)
                
                # Create a product entry for this tag
                product_entry = row.copy()
                selected_products.append(product_entry)
                break  # Only use this product once, even if it has multiple new tags
    
    # Create DataFrame from selected products
    output_df = pd.DataFrame(selected_products)
    
    # Sort by Tags for better readability
    output_df = output_df.sort_values('Tags')
    
    # Save to CSV
    output_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Created {output_file} with {len(output_df)} products representing {len(seen_tags)} unique tags")
    
    # Print tag summary
    print("\nTags represented:")
    for tag in sorted(seen_tags):
        print(f"- {tag}")

if __name__ == "__main__":
    input_file = "./output/wordpress-to-shopify_20241120_160116.csv"  # Your input file name
    create_category_samples(input_file)