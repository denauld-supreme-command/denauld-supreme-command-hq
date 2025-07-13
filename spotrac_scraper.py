#!/usr/bin/env python3
"""
Spotrac NFL Salary Cap Data Scraper
Scrapes live salary cap data from Spotrac.com for Philadelphia Eagles
Updates every 5 minutes and outputs JSON for salary cap module
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
import logging
from urllib.parse import urljoin
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotrac_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SpotracScraper:
    def __init__(self, team_name="philadelphia-eagles"):
        self.team_name = team_name
        self.base_url = "https://www.spotrac.com"
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # URLs to scrape
        self.urls = {
            'contracts': f'{self.base_url}/nfl/{self.team_name}/cap/',
            'extensions': f'{self.base_url}/nfl/contracts/extensions/',
            'remaining': f'{self.base_url}/nfl/contracts/remaining/',
            'incentives': f'{self.base_url}/nfl/contracts/incentives/_/year/2025',
            'franchise_tag': f'{self.base_url}/nfl/contracts/franchise-tag/',
            'transition_tag': f'{self.base_url}/nfl/contracts/transition-tag/',
            'market_value': f'{self.base_url}/nfl/market-value/',
            'team_cap': f'{self.base_url}/nfl/{self.team_name}/cap/2025/'
        }
        
        # Initialize data structure
        self.salary_cap_data = {
            'team': 'Philadelphia Eagles',
            'last_updated': None,
            'salary_cap': {
                'total_cap': 0,
                'used_cap': 0,
                'available_cap': 0,
                'dead_money': 0,
                'cap_percentage': 0
            },
            'top_contracts': [],
            'extension_candidates': [],
            'remaining_guarantees': [],
            'incentives_2025': [],
            'franchise_players': [],
            'market_values': [],
            'cap_history': []
        }

    def safe_request(self, url, max_retries=3, delay=2):
        """Make a safe HTTP request with retries and error handling"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching: {url} (Attempt {attempt + 1})")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                time.sleep(delay)  # Be respectful to the server
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(delay * (attempt + 1))
        return None

    def parse_currency(self, text):
        """Parse currency string to integer (dollars)"""
        if not text:
            return 0
        
        # Remove all non-numeric characters except decimal point and minus
        cleaned = re.sub(r'[^\d.\-]', '', str(text))
        if not cleaned:
            return 0
            
        try:
            value = float(cleaned)
            # Check if it's in millions (common in Spotrac)
            if 'M' in str(text) or 'million' in str(text).lower():
                value *= 1000000
            elif 'K' in str(text) or 'thousand' in str(text).lower():
                value *= 1000
            return int(value)
        except ValueError:
            return 0

    def scrape_team_cap_overview(self):
        """Scrape team salary cap overview"""
        logger.info("Scraping team salary cap overview...")
        
        response = self.safe_request(self.urls['team_cap'])
        if not response:
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Look for cap summary table or div
            cap_summary = soup.find('div', class_='cap-summary') or soup.find('table', class_='cap-table')
            
            if cap_summary:
                # Extract total cap space
                total_cap_elem = soup.find(text=re.compile(r'Total Cap Space|Salary Cap'))
                if total_cap_elem:
                    total_cap_parent = total_cap_elem.find_parent()
                    if total_cap_parent:
                        total_cap_text = total_cap_parent.get_text()
                        self.salary_cap_data['salary_cap']['total_cap'] = self.parse_currency(total_cap_text)
                
                # Extract used cap space
                used_cap_elem = soup.find(text=re.compile(r'Cap Used|Active Cap'))
                if used_cap_elem:
                    used_cap_parent = used_cap_elem.find_parent()
                    if used_cap_parent:
                        used_cap_text = used_cap_parent.get_text()
                        self.salary_cap_data['salary_cap']['used_cap'] = self.parse_currency(used_cap_text)
                
                # Extract available cap space
                available_cap_elem = soup.find(text=re.compile(r'Cap Space|Available'))
                if available_cap_elem:
                    available_cap_parent = available_cap_elem.find_parent()
                    if available_cap_parent:
                        available_cap_text = available_cap_parent.get_text()
                        self.salary_cap_data['salary_cap']['available_cap'] = self.parse_currency(available_cap_text)
                
                # Extract dead money
                dead_money_elem = soup.find(text=re.compile(r'Dead Money|Dead Cap'))
                if dead_money_elem:
                    dead_money_parent = dead_money_elem.find_parent()
                    if dead_money_parent:
                        dead_money_text = dead_money_parent.get_text()
                        self.salary_cap_data['salary_cap']['dead_money'] = self.parse_currency(dead_money_text)
            
            # Calculate percentage if we have total and used
            total_cap = self.salary_cap_data['salary_cap']['total_cap']
            used_cap = self.salary_cap_data['salary_cap']['used_cap']
            
            if total_cap > 0:
                self.salary_cap_data['salary_cap']['cap_percentage'] = round((used_cap / total_cap) * 100, 1)
                
                # Calculate available if not found
                if self.salary_cap_data['salary_cap']['available_cap'] == 0:
                    self.salary_cap_data['salary_cap']['available_cap'] = total_cap - used_cap
            
            logger.info(f"Cap overview scraped: ${total_cap:,} total, ${used_cap:,} used")
            
        except Exception as e:
            logger.error(f"Error scraping cap overview: {e}")

    def scrape_player_contracts(self):
        """Scrape individual player contracts"""
        logger.info("Scraping player contracts...")
        
        response = self.safe_request(self.urls['contracts'])
        if not response:
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Look for player contract table
            contract_table = soup.find('table', class_='datatable') or soup.find('table', id='contracts')
            
            if contract_table:
                rows = contract_table.find_all('tr')[1:]  # Skip header row
                
                for row in rows[:15]:  # Top 15 contracts
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        try:
                            # Extract player info
                            player_name = cells[0].get_text(strip=True)
                            position = cells[1].get_text(strip=True) if len(cells) > 1 else 'N/A'
                            
                            # Extract contract details (structure may vary)
                            cap_hit = self.parse_currency(cells[2].get_text(strip=True)) if len(cells) > 2 else 0
                            total_value = self.parse_currency(cells[3].get_text(strip=True)) if len(cells) > 3 else 0
                            guaranteed = self.parse_currency(cells[4].get_text(strip=True)) if len(cells) > 4 else 0
                            
                            # Extract years remaining (if available)
                            years_remaining = 0
                            if len(cells) > 5:
                                years_text = cells[5].get_text(strip=True)
                                years_match = re.search(r'(\d+)', years_text)
                                if years_match:
                                    years_remaining = int(years_match.group(1))
                            
                            contract_data = {
                                'player_name': player_name,
                                'position': position,
                                'cap_hit_2025': cap_hit,
                                'total_value': total_value,
                                'guaranteed': guaranteed,
                                'years_remaining': years_remaining,
                                'restructure_potential': cap_hit > 5000000  # Players with >$5M cap hit
                            }
                            
                            self.salary_cap_data['top_contracts'].append(contract_data)
                            
                        except Exception as e:
                            logger.warning(f"Error parsing contract row: {e}")
                            continue
                
                logger.info(f"Scraped {len(self.salary_cap_data['top_contracts'])} player contracts")
            
        except Exception as e:
            logger.error(f"Error scraping player contracts: {e}")

    def scrape_extension_candidates(self):
        """Scrape potential extension candidates"""
        logger.info("Scraping extension candidates...")
        
        response = self.safe_request(self.urls['extensions'])
        if not response:
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Look for Eagles players in extension discussions
            eagles_players = soup.find_all(text=re.compile(r'Philadelphia|Eagles', re.IGNORECASE))
            
            for player_text in eagles_players[:10]:  # Limit results
                parent = player_text.find_parent('tr') or player_text.find_parent('div')
                if parent:
                    player_info = parent.get_text(strip=True)
                    
                    # Extract player name (usually first part)
                    player_name_match = re.search(r'^([A-Za-z\.\s]+)', player_info)
                    if player_name_match:
                        player_name = player_name_match.group(1).strip()
                        
                        extension_data = {
                            'player_name': player_name,
                            'current_status': 'Extension Candidate',
                            'priority': 'High' if any(pos in player_info.upper() for pos in ['QB', 'WR', 'OT']) else 'Medium',
                            'contract_year': 2025
                        }
                        
                        self.salary_cap_data['extension_candidates'].append(extension_data)
            
            logger.info(f"Found {len(self.salary_cap_data['extension_candidates'])} extension candidates")
            
        except Exception as e:
            logger.error(f"Error scraping extension candidates: {e}")

    def scrape_market_values(self):
        """Scrape current market values for positions"""
        logger.info("Scraping market values...")
        
        response = self.safe_request(self.urls['market_value'])
        if not response:
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Look for position market value table
            market_table = soup.find('table', class_='datatable') or soup.find('table', id='market-values')
            
            if market_table:
                rows = market_table.find_all('tr')[1:]  # Skip header
                
                for row in rows[:20]:  # Top 20 positions
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        try:
                            position = cells[0].get_text(strip=True)
                            avg_salary = self.parse_currency(cells[1].get_text(strip=True))
                            top_salary = self.parse_currency(cells[2].get_text(strip=True)) if len(cells) > 2 else 0
                            
                            market_data = {
                                'position': position,
                                'average_salary': avg_salary,
                                'top_salary': top_salary,
                                'market_tier': 'Premium' if avg_salary > 10000000 else 'Standard'
                            }
                            
                            self.salary_cap_data['market_values'].append(market_data)
                            
                        except Exception as e:
                            logger.warning(f"Error parsing market value row: {e}")
                            continue
                
                logger.info(f"Scraped {len(self.salary_cap_data['market_values'])} market values")
            
        except Exception as e:
            logger.error(f"Error scraping market values: {e}")

    def scrape_all_data(self):
        """Scrape all salary cap data from Spotrac"""
        logger.info("Starting comprehensive Spotrac data scrape...")
        
        try:
            # Scrape different data types
            self.scrape_team_cap_overview()
            self.scrape_player_contracts()
            self.scrape_extension_candidates()
            self.scrape_market_values()
            
            # Update timestamp
            self.salary_cap_data['last_updated'] = datetime.now().isoformat()
            
            logger.info("Data scraping completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data scraping: {e}")

    def save_data(self, filename='salary_cap_data.json'):
        """Save scraped data to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs('data', exist_ok=True)
            filepath = os.path.join('data', filename)
            
            with open(filepath, 'w') as f:
                json.dump(self.salary_cap_data, f, indent=2, default=str)
            
            logger.info(f"Data saved to {filepath}")
            
            # Also save a backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f'salary_cap_data_backup_{timestamp}.json'
            backup_filepath = os.path.join('data', 'backups', backup_filename)
            
            os.makedirs(os.path.dirname(backup_filepath), exist_ok=True)
            with open(backup_filepath, 'w') as f:
                json.dump(self.salary_cap_data, f, indent=2, default=str)
            
            logger.info(f"Backup saved to {backup_filepath}")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def load_existing_data(self, filename='salary_cap_data.json'):
        """Load existing data if available"""
        try:
            filepath = os.path.join('data', filename)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    existing_data = json.load(f)
                
                # Merge with existing data structure
                for key in existing_data:
                    if key in self.salary_cap_data:
                        self.salary_cap_data[key] = existing_data[key]
                
                logger.info(f"Loaded existing data from {filepath}")
                return True
        except Exception as e:
            logger.warning(f"Could not load existing data: {e}")
        
        return False

    def validate_data(self):
        """Validate scraped data quality"""
        issues = []
        
        # Check salary cap totals
        if self.salary_cap_data['salary_cap']['total_cap'] == 0:
            issues.append("Total salary cap not found")
        
        if self.salary_cap_data['salary_cap']['used_cap'] == 0:
            issues.append("Used salary cap not found")
        
        # Check contract data
        if len(self.salary_cap_data['top_contracts']) == 0:
            issues.append("No player contracts found")
        
        # Check for reasonable values
        total_cap = self.salary_cap_data['salary_cap']['total_cap']
        if total_cap > 0 and (total_cap < 200000000 or total_cap > 300000000):
            issues.append(f"Total cap seems unreasonable: ${total_cap:,}")
        
        if issues:
            logger.warning(f"Data validation issues: {', '.join(issues)}")
        else:
            logger.info("Data validation passed")
        
        return len(issues) == 0

def run_continuous_scraper(interval_minutes=5):
    """Run the scraper continuously with specified interval"""
    scraper = SpotracScraper()
    
    logger.info(f"Starting continuous scraper (interval: {interval_minutes} minutes)")
    
    while True:
        try:
            # Load existing data first
            scraper.load_existing_data()
            
            # Scrape new data
            scraper.scrape_all_data()
            
            # Validate data quality
            if scraper.validate_data():
                # Save data if validation passes
                scraper.save_data()
                logger.info("Scrape cycle completed successfully")
            else:
                logger.warning("Data validation failed, skipping save")
            
            # Wait for next cycle
            logger.info(f"Waiting {interval_minutes} minutes until next scrape...")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("Scraper stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in scraper loop: {e}")
            logger.info("Waiting 1 minute before retry...")
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape NFL salary cap data from Spotrac')
    parser.add_argument('--team', default='philadelphia-eagles', help='Team name for Spotrac URLs')
    parser.add_argument('--interval', type=int, default=5, help='Scrape interval in minutes')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuously')
    
    args = parser.parse_args()
    
    if args.once:
        # Run once and exit
        scraper = SpotracScraper(args.team)
        scraper.scrape_all_data()
        scraper.save_data()
        print("Single scrape completed")
    else:
        # Run continuously
        run_continuous_scraper(args.interval)
