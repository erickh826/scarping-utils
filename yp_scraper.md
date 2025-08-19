# YP.com.hk Web Scraper
A comprehensive Python scraper for extracting business listings and categories from YP.com.hk (Yellow Pages Hong Kong). The scraper supports both Chinese (繁體中文) and English languages and handles the complete 3-level category hierarchy.

Features
- Multi-language Support: Scrapes content in Chinese (zh) or English (en)
- 3-Level Category Hierarchy: Properly extracts all category levels:
    - Level 1: Root categories (e.g., 食品糧油、餐飲業設備)
    - Level 2: Main subcategories (e.g., 飲品、煙草, 糧油、食品)
    - Level 3: Detailed categories (e.g., 糧食雜貨, 日本食品)
- Complete Business Information: Extracts company name, address, phone, and URL
- AJAX Pagination Support: Handles dynamic content loading
- Duplicate Prevention: Ensures no duplicate listings
- Multiple Output Formats: Saves data in both JSON and CSV formats

## Requirements
```
pip install requests beautifulsoup4
```

## Installation
1. Clone or download the script yp_scraper.py
2. Install the required packages:
```
pip install requests beautifulsoup4
```
## Usage
### Basic Usage
```
# Scrape in Chinese (default)
python yp_scraper.py

# Scrape in English
python yp_scraper.py --lang en
```

## Advanced Options
```
# Scrape with a custom starting URL
python yp_scraper.py --start-url "https://www.yp.com.hk/Category/Food-Products-Restaurant-Equipment/zh"

# Limit the number of Level 3 categories to scrape (useful for testing)
python yp_scraper.py --max-categories 5

# Combine options
python yp_scraper.py --lang en --max-categories 10
```

### Command Line Arguments
1. --lang: Language to scrape (<mark>zh</mark> for Chinese, <mark>en</mark> for English). Default: zh
2. --max-categories: Maximum number of Level 3 categories to scrape. Default: all categories
3. --start-url: Custom starting URL for scraping. Default: Food Products category


## Output Files
The scraper generates three types of files with timestamps:
### 1. Listings CSV File <br/>
<mark>yp_listings_[lang]_[timestamp].csv</mark> <br/>
Contains all scraped company listings with columns:

- companyTitle: Company name
- address: Business address
- phone: Contact phone number
- companyurl: Company detail page URL
- category_full_path: Complete category hierarchy (e.g., "主頁 > 食品糧油、餐飲業設備 > 糧油、食品 > 糧食雜貨")
- category_parent: Parent category name
- category_name: Direct category name
- language: Language of the content

### 2. Listings JSON File<br/>
<mark>yp_listings_[lang]_[timestamp].json</mark> <br/>
Same data as CSV but in JSON format for programmatic use.

### 3. Categories JSON File

<mark>yp_categories_[lang]_[timestamp].json </mark> <br/>

Contains all discovered categories with their hierarchy information:

- name: Category name
- url: Category URL
- parent: Parent category name
- level: Hierarchy level (1, 2, or 3)
- count: Number of listings in category
- full_path: Complete hierarchy path
- language: Language of the content


## Example Output

Sample Listing Data

```
{
  "companyTitle": "ABC食品有限公司",
  "address": "香港九龍觀塘區XXX街123號",
  "phone": "2345 6789",
  "companyurl": "https://www.yp.com.hk/CompanyInfo/...",
  "category_full_path": "主頁 > 食品糧油、餐飲業設備 > 糧油、食品 > 糧食雜貨",
  "category_parent": "糧油、食品",
  "category_name": "糧食雜貨",
  "language": "zh"
}
```

Performance Considerations
- The scraper includes delays between requests to be respectful to the server
- Default delay: 1 second between category pages, 2 seconds between categories during listing extraction
- Estimated time: ~1-2 minutes per category depending on the number of listings