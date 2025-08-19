import requests
from bs4 import BeautifulSoup
import json
import time
import csv
import re
from urllib.parse import urljoin, urlparse, quote, unquote
import os
from datetime import datetime
import hashlib

class YPMultiLevelScraper:
    def __init__(self, base_url="https://www.yp.com.hk"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        self.all_categories = []
        self.scraped_data = []
        self.visited_urls = set()
        self.processed_companies = set()  # Track unique companies to avoid duplicates
        
    def clean_company_name(self, text):
        """Remove '分店' and clean company name"""
        if not text:
            return ""
        # Remove 分店 (branch) text
        text = re.sub(r'\s*分店\s*', '', text)
        # Clean up whitespace
        text = text.strip()
        return text
    
    def clean_category_name(self, text):
        """Remove count numbers and clean category name"""
        if not text:
            return ""
        # Remove numbers in parentheses like (25)
        text = re.sub(r'\s*\(\d+\)\s*', '', text)
        # Remove trailing numbers
        text = re.sub(r'(\d+)$', '', text)
        # Clean up whitespace
        text = text.strip()
        return text
    
    def parse_category_text(self, text):
        """Parse category text to extract name and count"""
        if not text:
            return None, None
        
        text = text.strip()
        
        # Pattern 1: "茶葉─批發 (74)"
        match = re.match(r'^(.+?)\s*\((\d+)\)$', text)
        if match:
            return match.group(1).strip(), int(match.group(2))
        
        # Pattern 2: "茶葉─批發74"
        match = re.match(r'^(.+?)(\d+)$', text)
        if match:
            name_part = match.group(1)
            if name_part.endswith('─') or name_part.endswith('-') or name_part.endswith(' '):
                return name_part.strip('─- '), int(match.group(2))
        
        # Pattern 3: Space before number "茶葉─批發 74"
        match = re.match(r'^(.+?)\s+(\d+)$', text)
        if match:
            return match.group(1).strip(), int(match.group(2))
        
        # No count found
        return text, None
    
    def extract_categories_from_page(self, url, parent_category="", level=1):
        """Extract categories from a page"""
        if url in self.visited_urls or level > 3:
            return []
        
        self.visited_urls.add(url)
        categories = []
        
        try:
            print(f"{'  ' * level}Extracting categories from level {level}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for category links
            found_links = soup.select('a[href*="/Category/"]')
            
            seen_categories = set()
            for link in found_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip pagination and non-category links
                if not text or '/CompanyInfo/' in href or '/p' in href and re.search(r'/p\d+/', href):
                    continue
                
                # Parse category name and count
                clean_name, count = self.parse_category_text(text)
                
                if not clean_name or clean_name in seen_categories:
                    continue
                
                seen_categories.add(clean_name)
                full_url = urljoin(self.base_url, href)
                
                # Determine hierarchy
                if parent_category:
                    full_path = f"{parent_category} > {clean_name}"
                else:
                    full_path = f"主頁 > 食品糧油、餐飲業設備 > {clean_name}"
                
                category_info = {
                    'name': clean_name,
                    'url': full_url,
                    'parent': parent_category if parent_category else "食品糧油、餐飲業設備",
                    'level': level,
                    'count': count,
                    'full_path': full_path
                }
                
                categories.append(category_info)
                self.all_categories.append(category_info)
                print(f"{'  ' * (level+1)}Found: {clean_name} ({count} items)")
                
                # Explore subcategories
                if level < 3 and '/Category/' in href and not '/CompanyInfo/' in href:
                    time.sleep(1)
                    subcategories = self.extract_categories_from_page(
                        full_url, 
                        clean_name,
                        level + 1
                    )
                    categories.extend(subcategories)
            
            return categories
            
        except Exception as e:
            print(f"Error extracting categories: {e}")
            return []
    
    def scrape_listings_from_category(self, category_info):
        """Scrape business listings from a category page"""
        url = category_info['url']
        all_listings = []
        page_num = 1
        max_pages = 50
        
        # Determine category hierarchy
        path_parts = category_info['full_path'].split(' > ')
        category_parent = path_parts[-2] if len(path_parts) > 2 else "食品糧油、餐飲業設備"
        category_name = category_info['name']
        
        while page_num <= max_pages:
            try:
                # Construct URL with pagination
                if '/p' in url:
                    # Replace existing page number
                    paginated_url = re.sub(r'/p\d+/', f'/p{page_num}/', url)
                else:
                    # Add page number
                    if url.endswith('/zh'):
                        paginated_url = url.replace('/zh', f'/p{page_num}/zh')
                    else:
                        paginated_url = f"{url}/p{page_num}/zh"
                
                print(f"  Scraping page {page_num}: {paginated_url}")
                
                response = self.session.get(paginated_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find the main content section that holds the list
                content_section = soup.find('div', class_='iypColContentSection')
                if not content_section:
                    content_section = soup  # Fallback to entire page
                
                # Find all company info divs - only get desktop version to avoid duplicates
                company_items = content_section.find_all('div', class_=re.compile(r'companyInfo.*responsiveDesktop'))
                
                if not company_items:
                    # Try alternative selectors
                    company_items = content_section.find_all('div', class_='companyInfo')
                    # Filter out mobile versions if both exist
                    company_items = [item for item in company_items if 'responsiveMobile' not in item.get('class', [])]
                
                if not company_items:
                    print(f"    No companies found on page {page_num}")
                    break
                
                print(f"    Found {len(company_items)} companies on page {page_num}")
                
                for item in company_items:
                    try:
                        listing_data = {
                            'category_full_path': category_info['full_path'],
                            'category_parent': category_parent,
                            'category_name': category_name
                        }
                        
                        # Extract company title
                        title_elem = item.find('div', class_='companyTitle')
                        if title_elem:
                            title_link = title_elem.find('a')
                            if title_link:
                                # Clean company name (remove 分店)
                                company_name = self.clean_company_name(title_link.get_text(strip=True))
                                listing_data['companyTitle'] = company_name
                                
                                # Get company URL
                                company_href = title_link.get('href', '')
                                if company_href:
                                    listing_data['companyurl'] = urljoin(self.base_url, company_href)
                        
                        # Extract phone number
                        phone_found = False
                        # Look for phone icon container
                        phone_containers = item.find_all('div', class_='companyDataCellContainer')
                        for container in phone_containers:
                            icon = container.find('div', class_='companyDataIcon')
                            if icon and 'phone.svg' in str(icon):
                                phone_value = container.find('div', class_='companyDataValue')
                                if phone_value:
                                    phone_text = phone_value.get_text(strip=True)
                                    if phone_text and re.search(r'\d', phone_text):
                                        listing_data['phone'] = phone_text
                                        phone_found = True
                                        break
                        
                        # Alternative phone extraction
                        if not phone_found:
                            phone_elem = item.find('span', class_='infoDetailSpanA')
                            if phone_elem and re.search(r'\d{4}', phone_elem.get_text()):
                                listing_data['phone'] = phone_elem.get_text(strip=True)
                        
                        # Extract address
                        address_found = False
                        # Look for map icon container
                        for container in phone_containers:
                            icon = container.find('div', class_='companyDataIcon')
                            if icon and 'map.svg' in str(icon):
                                address_value = container.find('div', class_='companyDataValue')
                                if address_value:
                                    address_text = address_value.get_text(strip=True)
                                    if address_text:
                                        listing_data['address'] = address_text
                                        address_found = True
                                        break
                        
                        # Alternative address extraction
                        if not address_found:
                            address_elem = item.find('span', class_='desktopUrlLink')
                            if address_elem and not address_elem.get_text().startswith('http'):
                                listing_data['address'] = address_elem.get_text(strip=True)
                        
                        # Only add if we have at least company title
                        if listing_data.get('companyTitle'):
                            # Create a unique key to avoid duplicates
                            unique_key = f"{listing_data.get('companyTitle', '')}_{listing_data.get('phone', '')}_{listing_data.get('address', '')}"
                            
                            if unique_key not in self.processed_companies:
                                self.processed_companies.add(unique_key)
                                all_listings.append(listing_data)
                    
                    except Exception as e:
                        print(f"      Error parsing company item: {e}")
                        continue
                
                # Check for next page
                # Look for pagination
                pagination = soup.find('div', class_='pagination') or soup.find('ul', class_='pagination')
                has_next = False
                
                if pagination:
                    # Check for next page link
                    next_link = pagination.find('a', text=re.compile(r'下一頁|Next|>'))
                    if next_link and next_link.get('href'):
                        has_next = True
                    
                    # Also check if current page is not the last
                    current_page = pagination.find('li', class_='active') or pagination.find('span', class_='current')
                    if current_page:
                        next_sibling = current_page.find_next_sibling('li')
                        if next_sibling and next_sibling.find('a'):
                            has_next = True
                
                # Alternative: check if we found companies (if yes, likely more pages)
                if not has_next and len(company_items) >= 10:  # Usually 10-20 per page
                    has_next = True
                
                if not has_next or page_num >= max_pages:
                    print(f"    Stopping at page {page_num} (has_next={has_next})")
                    break
                
                page_num += 1
                time.sleep(1.5)  # Rate limiting
                
            except Exception as e:
                print(f"    Error on page {page_num}: {e}")
                break
        
        return all_listings
    
    def scrape_all(self, start_url, max_categories=None):
        """Main method to scrape everything"""
        print("=" * 50)
        print("Starting YP.com.hk scraping")
        print("=" * 50)
        
        # Step 1: Extract all categories
        print("\nStep 1: Extracting categories...")
        self.extract_categories_from_page(start_url, "", 1)
        
        print(f"\nFound {len(self.all_categories)} total categories")
        
        # Step 2: Scrape listings from each category
        print("\nStep 2: Scraping listings from categories...")
        categories_to_scrape = self.all_categories[:max_categories] if max_categories else self.all_categories
        
        total_listings = 0
        for i, category in enumerate(categories_to_scrape, 1):
            print(f"\n[{i}/{len(categories_to_scrape)}] Processing: {category['name']}")
            if category.get('count'):
                print(f"  Expected: {category['count']} listings")
            
            listings = self.scrape_listings_from_category(category)
            self.scraped_data.extend(listings)
            total_listings += len(listings)
            
            print(f"  Found: {len(listings)} listings (Total so far: {total_listings})")
            
            if category.get('count') and len(listings) < category['count'] * 0.5:
                print(f"  ⚠️ Warning: Found significantly fewer listings than expected")
            
            time.sleep(2)  # Rate limiting between categories
    
    def save_data(self):
        """Save scraped data to JSON and CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save to JSON
        json_file = f'yp_listings_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        print(f"\nData saved to {json_file}")
        
        # Save to CSV
        if self.scraped_data:
            csv_file = f'yp_listings_{timestamp}.csv'
            
            # Define the order of fields
            fieldnames = ['companyTitle', 'address', 'phone', 'companyurl', 
                         'category_full_path', 'category_parent', 'category_name']
            
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in self.scraped_data:
                    # Ensure all fields exist
                    clean_row = {field: row.get(field, '') for field in fieldnames}
                    writer.writerow(clean_row)
            
            print(f"Data saved to {csv_file}")
        
        # Save categories
        categories_file = f'yp_categories_{timestamp}.json'
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_categories, f, ensure_ascii=False, indent=2)
        print(f"Categories saved to {categories_file}")
        
        # Generate summary
        print("\n" + "=" * 50)
        print("SCRAPING SUMMARY")
        print("=" * 50)
        print(f"Total categories found: {len(self.all_categories)}")
        print(f"Total unique companies scraped: {len(self.scraped_data)}")
        
        # Count by category
        category_counts = {}
        for item in self.scraped_data:
            cat = item.get('category_name', 'Unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("\nTop categories by number of companies:")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count} companies")

def main():
    # Initialize scraper
    scraper = YPMultiLevelScraper()
    
    # Starting URL
    start_url = "https://www.yp.com.hk/Category/Food-Products-Restaurant-Equipment/Food-Products-Supplies/zh"
    
    # Scrape all categories or limit for testing
    # Set max_categories=5 for testing, None for all
    scraper.scrape_all(start_url, max_categories=None)
    
    # Save results
    scraper.save_data()

if __name__ == "__main__":
    main()