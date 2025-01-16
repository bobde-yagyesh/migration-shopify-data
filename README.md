# WordPress to Shopify Data Migration

This project aims to provide a solution for converting WordPress product data to Shopify format. The main objective is to create a tool that can be used by WordPress users to migrate their existing products to Shopify.

## Features

- Convert WordPress product data to Shopify format
- Handles product variants and images
- Supports product options
- Outputs a CSV file with the converted data

## Requirements

- Python 3.x
- Pandas
- Numpy
- Streamlit


## SCRIPTS USAGE

<table>
<tr>
<th>Sno.</th>
<th>Input File</th>
<th>Output File</th>
<th>Description</th>
<th>Path</th>
</tr>
<tr>
<td>1</td>
<td>Wordpress Exported File Csv</td>
<td>Shopify Importable File Csv</td>
<td>Converts wordpress data to Shopify format with variants.</td>
<td>./scripts/old/app.py</td>
</tr>
<tr>
<td>2</td>
<td>Wordpress Exported File Csv</td>
<td>Shopify Importable File Csv</td>
<td>Converts wordpress data to Shopify format with variant images. BUG: Variants not propertly handled</td>
<td>.scripts/old/new.py</td>
<td>3</td>
<td>Wordpress Exported File Csv</td>
<td>Shopify Importable File Csv</td>
<td>Converts wordpress data to Shopify format with variant images and handles the cases if variant images are not present. Handles variant properly. Add alt text if color option is present</td>
<td>./optimized_wordpress_to_shopify_v1.py</td>
</tr>
<tr>
<td>4</td>
<td>Shopify Output Csv</td>
<td>Tag Wise Analysis/Stats csv</td>
<td>Generates Tag Wise Analysis/Stats, Product stats, variant stats, blank image stats</td>
<td>./tooling_ouput.py</td>
</tr>
<tr>
<td>5</td>
<td>Shopify Output Csv</td>
<td>Wordpress Convert to shopify</td>
<td>It is improved from v1 because it provided all meta fields like brand, fabric, texture, material, thickness etc</td>
<td>./optimized_wordpress_to_shopify_v2.py</td>
</tr>
</table>