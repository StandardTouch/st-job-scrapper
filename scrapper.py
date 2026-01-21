import os
import csv
import logging
from scrapling.fetchers import Fetcher, StealthyFetcher
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
from email_template import send_email_report
load_dotenv()

# Configure logging to file with datetime stamps
logs_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(logs_dir, exist_ok=True)
log_filename = os.path.join(logs_dir, f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {log_filename}")

# Function to parse and convert datetime string to MySQL DATETIME format
def parse_datetime_to_mysql(datetime_str):
    """
    Convert datetime string from format 'Wednesday, Jan 21, 2026, 1:33:31 AM'
    to MySQL DATETIME format '2026-01-21 01:33:31'
    """
    if not datetime_str:
        return None
    
    try:
        datetime_str = datetime_str.strip()
        
        # Check if already in MySQL format (YYYY-MM-DD HH:MM:SS)
        # Pattern: starts with 20XX-XX-XX XX:XX:XX (19 characters)
        if len(datetime_str) == 19 and datetime_str[4] == '-' and datetime_str[7] == '-' and datetime_str[10] == ' ' and datetime_str[13] == ':' and datetime_str[16] == ':':
            try:
                # Validate it's a valid datetime
                datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                return datetime_str  # Already in correct format
            except ValueError:
                pass  # Not valid MySQL format, continue parsing
        
        # Try to parse common formats
        formats = [
            "%A, %b %d, %Y, %I:%M:%S %p",  # Wednesday, Jan 21, 2026, 1:33:31 AM
            "%A, %B %d, %Y, %I:%M:%S %p",  # Wednesday, January 21, 2026, 1:33:31 AM
            "%b %d, %Y, %I:%M:%S %p",      # Jan 21, 2026, 1:33:31 AM
            "%B %d, %Y, %I:%M:%S %p",      # January 21, 2026, 1:33:31 AM
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                # Convert to MySQL DATETIME format: YYYY-MM-DD HH:MM:SS
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        
        # If all formats fail, log warning and return None
        logger.warning(f"Could not parse datetime: {datetime_str}")
        return None
    except Exception as e:
        logger.error(f"Error parsing datetime '{datetime_str}': {str(e)}")
        return None

base_url = "https://www.expatriates.com"
conn = None
# Details page scrapping
def scrap_details_page(url, log=False):
    try:
        page = StealthyFetcher.fetch(
            base_url + url,
            solve_cloudflare=True,
            humanize=True,
            headless=True
        )

        # Get the post-info div
        post_info = page.css_first('.post-info')
        if not post_info:
            return {"success": False}

        # Extract Posted Date and Time
        posted_date_time = None
        timestamp_span = post_info.css_first('#timestamp')
        if timestamp_span:
            datetime_str = timestamp_span.text.strip()
            # Convert to MySQL DATETIME format
            posted_date_time = parse_datetime_to_mysql(datetime_str)

        # Extract Category, Region, and Posting ID
        category = None
        region = None
        posting_id = None

        category_li = post_info.css('li')
        for li in category_li:
            category_text = li.xpath('//li[strong[text()="Category:"]]/text()').get().strip()
            region_text = li.xpath('//li[strong[text()="Region:"]]/text()').get().strip()
            posting_id_text = li.xpath('//li[strong[text()="Posting ID:"]]/text()').get().strip()
            if category_text:
                category = category_text
            if region_text:
                region = region_text
            if posting_id_text:
                posting_id = posting_id_text
            
            if category and region and posting_id:
                break
        
        # title
        h1 = post_info.xpath('//div[@class="page-title"]/h1').first
        title = h1.text.strip() if h1 else None

        # Extract Mobile Number
        mobile_no = None
        phone_link = post_info.css_first('#phone-link')
        if phone_link:
            mobile_no = phone_link.text.strip()
        else:
            # Fallback: try to get from posting-phone button
            phone_button = post_info.css_first('.posting-phone')
            if phone_button:
                phone_a = phone_button.css_first('a')
                if phone_a:
                    mobile_no = phone_a.text.strip()

        # Extract WhatsApp Number
        whatsapp_number = None
        whatsapp_links = post_info.css('a')
        for link in whatsapp_links:
            href = link.css_first('::attr(href)')
            text = link.text.strip() if link.text else ''
            if href:
                href_lower = href.lower()
                if 'wa.me' in href_lower or 'whatsapp' in href_lower or 'Chat on WhatsApp' in text:
                    # Extract phone number from WhatsApp link
                    if 'wa.me' in href_lower:
                        whatsapp_number = href.split('wa.me/')[-1].split('?')[0]
                    elif 'api.whatsapp.com' in href_lower:
                        whatsapp_number = href.split('send?phone=')[-1].split('&')[0]
                    elif 'whatsapp.com' in href_lower:
                        # Try to extract from various WhatsApp URL formats
                        if 'phone=' in href_lower:
                            whatsapp_number = href.split('phone=')[-1].split('&')[0]
                    break

        # Compile all extracted data
        extracted_data = {
            "title": title,
            "posted_date_time": posted_date_time,
            "category": category,
            "region": region,
            "posting_id": posting_id,
            "mobile_no": mobile_no,
            "whatsapp_number": whatsapp_number,
            "success": True,
        }

        # Log the extracted data
        if log:
            logger.info("=" * 50)
            logger.info("EXTRACTED DATA")
            logger.info("=" * 50)
            for key, value in extracted_data.items():
                logger.info(f"{key.replace('_', ' ').title()}: {value}")
            logger.info("=" * 50)

        return extracted_data
    except Exception as e:
        if log:
            logger.error(f"Error scraping details page {url}: {str(e)}")
        return {"success": False}


def scrape_listing_pages(total_pages=1, max_items=None):
    current_page = 1
    items = []
    success_page_count = 0
    failed_page_count = 0

    while current_page <= total_pages:
        try:
            current_url = base_url + "/scripts/search/search.epl?page=" + str(current_page) + "&region_id=49&ads=1"
            page = StealthyFetcher.fetch(current_url, solve_cloudflare=True, humanize=True, headless=True)
            search_items = page.css(".search-item")
            
            for item in search_items:
                a = item.css('div.search-item > a').first

                link = a.attrib.get('href')
                title = a.text.strip()
                data = {
                    "link": link,
                    "title": title,
                }
                item_details = scrap_details_page(link, log=True)
                data.update(item_details)
                items.append(data)
                if max_items and len(items) >= max_items:
                    break
            
            success_page_count += 1
        except Exception as e:
            logger.error(f"Error fetching listing page {current_page}: {str(e)}")
            failed_page_count += 1
        
        current_page += 1
        
        if max_items and len(items) >= max_items:
            break
    
    return items, success_page_count, failed_page_count


def save_to_csv(items, success_page_count, failed_page_count, csv_filename="scraped_data.csv"):
    if not items:
        return
    
    # Save CSV to data directory
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, csv_filename)
    
    csv_headers = ["SL.no", "Link", "title", "success", "posted_date_time", "category", "region", "posting_id", "mobile_no", "whatsapp_number"]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        
        for index, item in enumerate(items, start=1):
            row = {
                "SL.no": index,
                "Link": item.get("link", ""),
                "title": item.get("title", ""),
                "success": item.get("success", False),
                "posted_date_time": item.get("posted_date_time", ""),
                "category": item.get("category", ""),
                "region": item.get("region", ""),
                "posting_id": item.get("posting_id", ""),
                "mobile_no": item.get("mobile_no", ""),
                "whatsapp_number": item.get("whatsapp_number", ""),
            }
            writer.writerow(row)
    
    logger.info(f"\nData saved to {csv_path}")
    logger.info(f"Success pages: {success_page_count}, Failed pages: {failed_page_count}")

# check mysql connection
def check_mysql_connection():
    global conn
    try:
        # Get environment variables with defaults/validation
        db_host = os.getenv('DB_HOST')
        if not db_host:
            raise Exception("DB_HOST environment variable is not set. Set it to 'mysql' (service name) or your MySQL host.")
        
        db_port = os.getenv('DB_PORT', '3306')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')
        
        if not all([db_user, db_password, db_name]):
            missing = [var for var, val in [('DB_USER', db_user), ('DB_PASSWORD', db_password), ('DB_NAME', db_name)] if not val]
            raise Exception(f"Missing required environment variables: {', '.join(missing)}")
        
        conn = mysql.connector.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name,
        )
        if not conn.is_connected():
            raise Exception("MySQL connection failed: Connection not established")
        logger.info("MySQL connection successful")
        return True
    except Exception as e:
        error_msg = f"Error connecting to MySQL: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

# close mysql connection
def close_mysql_connection():
    try:
        global conn
        if conn:
            conn.close()
    except Exception as e:
        logger.error(f"Error closing MySQL connection: {str(e)}")

# run migration of tables if not exists
def run_migration():
    global conn
    if not conn or not conn.is_connected():
        raise Exception("Cannot run migration: MySQL connection not established")
    
    try:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS scrapping_report (id INT AUTO_INCREMENT PRIMARY KEY, start_date_time DATETIME DEFAULT NULL, end_date_time DATETIME DEFAULT NULL, total_pages INT DEFAULT NULL, total_items INT DEFAULT NULL, success_listing_pages INT DEFAULT NULL, failed_listing_pages INT DEFAULT NULL, success_details_pages INT DEFAULT NULL, failed_details_pages INT DEFAULT NULL, created_at DATETIME DEFAULT NULL, updated_at DATETIME DEFAULT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS scrapping_items (id INT AUTO_INCREMENT PRIMARY KEY, scrapping_report_id INT DEFAULT NULL, link VARCHAR(255) DEFAULT NULL, title VARCHAR(255) DEFAULT NULL, success BOOLEAN DEFAULT NULL, posted_date_time DATETIME DEFAULT NULL, category VARCHAR(255) DEFAULT NULL, region VARCHAR(255) DEFAULT NULL, posting_id VARCHAR(255) DEFAULT NULL, mobile_no VARCHAR(255) DEFAULT NULL, whatsapp_number VARCHAR(255) DEFAULT NULL, created_at DATETIME DEFAULT NULL, updated_at DATETIME DEFAULT NULL)")
        conn.commit()
        cursor.close()
        logger.info("Migration completed successfully")
        return True
    except Exception as e:
        error_msg = f"Error running migration: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

# insert scrapping report
def insert_scrapping_report(start_date_time, end_date_time, total_pages, total_items, success_listing_pages, failed_listing_pages, success_details_pages, failed_details_pages):
    global conn
    if not conn or not conn.is_connected():
        raise Exception("Cannot insert report: MySQL connection not established")
    
    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        cursor.execute("INSERT INTO scrapping_report (start_date_time, end_date_time, total_pages, total_items, success_listing_pages, failed_listing_pages, success_details_pages, failed_details_pages, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (start_date_time, end_date_time, total_pages, total_items, success_listing_pages, failed_listing_pages, success_details_pages, failed_details_pages, current_time, current_time))
        report_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return report_id
    except Exception as e:
        logger.error(f"Error inserting scrapping report: {str(e)}")
        raise

# insert scrapping items
def insert_scrapping_items(scrapping_report_id, items):
    global conn
    if not conn or not conn.is_connected():
        raise Exception("Cannot insert items: MySQL connection not established")
    
    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        for item in items:
            # Ensure posted_date_time is in correct format or None
            posted_dt = item.get('posted_date_time')
            if posted_dt and isinstance(posted_dt, str):
                # Check if already in MySQL format (YYYY-MM-DD HH:MM:SS)
                if not posted_dt.startswith('20') or len(posted_dt) != 19 or posted_dt[4] != '-' or posted_dt[7] != '-':
                    # If not in MySQL format, try to parse it
                    posted_dt = parse_datetime_to_mysql(posted_dt)
                # If already in MySQL format, use as-is
            
            cursor.execute("INSERT INTO scrapping_items (scrapping_report_id, link, title, success, posted_date_time, category, region, posting_id, mobile_no, whatsapp_number, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (scrapping_report_id, item.get('link'), item.get('title'), item.get('success'), posted_dt, item.get('category'), item.get('region'), item.get('posting_id'), item.get('mobile_no'), item.get('whatsapp_number'), current_time, current_time))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Error inserting scrapping items: {str(e)}")
        raise

# get scrapping report by id
def get_scrapping_report(report_id):
    global conn
    if not conn or not conn.is_connected():
        raise Exception("Cannot get report: MySQL connection not established")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM scrapping_report WHERE id = %s", (report_id,))
        report = cursor.fetchone()
        cursor.close()
        return report
    except Exception as e:
        logger.error(f"Error getting scrapping report: {str(e)}")
        raise

# Main execution
if __name__ == "__main__":
    try:
        # Check database connection - must succeed before proceeding
        check_mysql_connection()
        
        # Run migration - must succeed before proceeding
        run_migration()
        
        # Only proceed with scraping if connection and migration are successful
        start_date_time = datetime.now()
        items, success_page_count, failed_page_count = scrape_listing_pages(total_pages=1, max_items=1)
        end_date_time = datetime.now()
        total_pages = 1
        total_items = len(items)
        success_listing_pages = success_page_count
        failed_listing_pages = failed_page_count
        success_details_pages = len([item for item in items if item.get('success')])
        failed_details_pages = len([item for item in items if not item.get('success')])
        scrapping_report_id = insert_scrapping_report(start_date_time, end_date_time, total_pages, total_items, success_listing_pages, failed_listing_pages, success_details_pages, failed_details_pages)
        insert_scrapping_items(scrapping_report_id, items)
        save_to_csv(items, success_page_count, failed_page_count)
        
        # Get report data and send email
        report_data = get_scrapping_report(scrapping_report_id)
        if report_data:
            send_email_report(report_data)
        
        close_mysql_connection()
    except Exception as e:
        logger.error(f"\n{'='*50}")
        logger.error(f"ERROR: {str(e)}")
        logger.error(f"{'='*50}")
        logger.error("Scraping aborted. Please fix the error and try again.")
        close_mysql_connection()
        exit(1)