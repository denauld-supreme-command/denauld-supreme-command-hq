import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
from datetime import datetime
import re
import os

class NFLDataScraper:
    def __init__(self):
        self.base_url = "https://www.spotrac.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.data = {}
        
    def random_delay(self, min_seconds=1, max_seconds=3):
        """Random delay to be respectful to the server"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def safe_request(self, url, max_retries=3):
        """Make request with retry logic"""
        for attempt in range(max_retries):
            try:
                self.random_delay()
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
    def scrape_salary_cap_data(self):
        """Scrape current salary cap information"""
        print("Scraping salary cap data...")
        url = f"{self.base_url}/nfl/cap"
        
        response = self.safe_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        cap_data = []
        
        # Find salary cap table
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    team_cell = cells[0]
                    team_link = team_cell.find('a')
                    if team_link:
                        team_name = team_link.text.strip()
                        team_abbr = self.extract_team_abbr(team_link.get('href', ''))
                        
                        # Extract cap data
                        try:
                            active_cap = self.clean_money(cells[1].text.strip())
                            dead_cap = self.clean_money(cells[2].text.strip())
                            cap_space = self.clean_money(cells[3].text.strip())
                            
                            cap_data.append({
                                'team': team_name,
                                'abbr': team_abbr,
                                'active_cap': active_cap,
                                'dead_cap': dead_cap,
                                'cap_space': cap_space,
                                'total_cap': active_cap + dead_cap
                            })
                        except (ValueError, IndexError):
                            continue
        
        self.data['salary_cap'] = cap_data
        print(f"Scraped {len(cap_data)} teams' salary cap data")
        
    def scrape_multi_year_cash(self):
        """Scrape multi-year cash data"""
        print("Scraping multi-year cash data...")
        url = f"{self.base_url}/nfl/cash"
        
        response = self.safe_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        cash_data = []
        
        # Find cash table
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:
                # Get years from header
                header_row = rows[0]
                year_cells = header_row.find_all(['th', 'td'])[1:]  # Skip team column
                years = [cell.text.strip() for cell in year_cells if cell.text.strip().isdigit()]
                
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > 1:
                        team_cell = cells[0]
                        team_link = team_cell.find('a')
                        if team_link:
                            team_name = team_link.text.strip()
                            team_abbr = self.extract_team_abbr(team_link.get('href', ''))
                            
                            yearly_cash = {}
                            for i, year in enumerate(years[:6]):  # Limit to 6 years
                                try:
                                    if i + 1 < len(cells):
                                        cash_value = self.clean_money(cells[i + 1].text.strip())
                                        yearly_cash[year] = cash_value
                                except (ValueError, IndexError):
                                    yearly_cash[year] = 0
                            
                            cash_data.append({
                                'team': team_name,
                                'abbr': team_abbr,
                                'yearly_cash': yearly_cash
                            })
        
        self.data['multi_year_cash'] = cash_data
        print(f"Scraped {len(cash_data)} teams' multi-year cash data")
        
    def scrape_team_rosters(self):
        """Scrape team rosters with contracts"""
        print("Scraping team rosters...")
        url = f"{self.base_url}/nfl/teams"
        
        response = self.safe_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get team links
        team_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if '/nfl/' in href and '/cap/' in href and len(href.split('/')) >= 4:
                team_links.append(href)
        
        rosters_data = {}
        
        # Limit to first 5 teams for demo purposes
        for team_link in team_links[:5]:
            try:
                team_abbr = team_link.split('/')[-2]
                roster_data = self.scrape_single_team_roster(team_link, team_abbr)
                if roster_data:
                    rosters_data[team_abbr] = roster_data
                    print(f"Scraped roster for {team_abbr}")
            except Exception as e:
                print(f"Error scraping team {team_link}: {e}")
                continue
        
        self.data['rosters'] = rosters_data
        
    def scrape_single_team_roster(self, team_url, team_abbr):
        """Scrape individual team roster"""
        full_url = f"{self.base_url}{team_url}"
        response = self.safe_request(full_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        players = []
        
        # Find roster table
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 6:
                    try:
                        player_name = cells[0].text.strip()
                        position = cells[1].text.strip()
                        age = cells[2].text.strip()
                        
                        # Contract info
                        cap_hit = self.clean_money(cells[3].text.strip())
                        base_salary = self.clean_money(cells[4].text.strip())
                        
                        if player_name and position:
                            players.append({
                                'name': player_name,
                                'position': position,
                                'age': age,
                                'cap_hit': cap_hit,
                                'base_salary': base_salary,
                                'team': team_abbr
                            })
                    except (ValueError, IndexError):
                        continue
        
        return players[:25]  # Limit to 25 players for demo
        
    def extract_team_abbr(self, href):
        """Extract team abbreviation from URL"""
        parts = href.split('/')
        for part in parts:
            if len(part) == 3 and part.isupper():
                return part
        return "UNK"
        
    def clean_money(self, money_str):
        """Convert money string to integer"""
        if not money_str or money_str in ['-', 'N/A', '']:
            return 0
        
        # Remove all non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.-]', '', money_str)
        
        if not cleaned:
            return 0
            
        try:
            # Handle millions/thousands
            if 'M' in money_str.upper():
                return int(float(cleaned) * 1000000)
            elif 'K' in money_str.upper():
                return int(float(cleaned) * 1000)
            else:
                return int(float(cleaned))
        except ValueError:
            return 0
            
    def scrape_contract_details(self):
        """Scrape detailed contract information"""
        print("Scraping contract details...")
        url = f"{self.base_url}/nfl/contracts"
        
        response = self.safe_request(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        contracts = []
        
        # Find contracts table
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:50]:  # Limit to 50 contracts
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 5:
                    try:
                        player_name = cells[0].text.strip()
                        team = cells[1].text.strip()
                        position = cells[2].text.strip()
                        contract_value = self.clean_money(cells[3].text.strip())
                        aav = self.clean_money(cells[4].text.strip())
                        
                        contracts.append({
                            'player': player_name,
                            'team': team,
                            'position': position,
                            'total_value': contract_value,
                            'aav': aav
                        })
                    except (ValueError, IndexError):
                        continue
        
        self.data['contracts'] = contracts
        print(f"Scraped {len(contracts)} contract details")
        
    def scrape_all_data(self):
        """Scrape all NFL data"""
        print("Starting comprehensive NFL data scraping...")
        
        try:
            self.scrape_salary_cap_data()
            self.scrape_multi_year_cash()
            self.scrape_team_rosters()
            self.scrape_contract_details()
            
            # Add metadata
            self.data['metadata'] = {
                'scraped_at': datetime.now().isoformat(),
                'source': 'spotrac.com',
                'scraper_version': '1.0'
            }
            
            print("✅ All NFL data scraped successfully!")
            return self.data
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return None
            
    def save_data(self, filename='nfl_data.json'):
        """Save scraped data to JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
            
        filepath = f"data/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
            
        print(f"💾 Data saved to {filepath}")
        
    def export_for_demo(self):
        """Export data formatted for NFL Executive Demo"""
        demo_data = {
            'salary_cap_summary': self.get_cap_summary(),
            'sample_team_roster': self.get_sample_roster(),
            'top_contracts': self.get_top_contracts(),
            'performance_ratings': self.generate_performance_ratings()
        }
        
        with open('data/demo_data.json', 'w') as f:
            json.dump(demo_data, f, indent=2)
            
        print("📊 Demo data exported to data/demo_data.json")
        return demo_data
        
    def get_cap_summary(self):
        """Get salary cap summary for demo"""
        if 'salary_cap' in self.data and self.data['salary_cap']:
            # Use first team as example
            team_data = self.data['salary_cap'][0]
            return {
                'cap_ceiling': 255000000,  # Current NFL cap
                'cap_rollover': 4485068,
                'cap_adjusted': team_data['total_cap'],
                'cap_floor': 89,  # 89% of cap
                'active_contracts': team_data['active_cap'],
                'dead_cap': team_data['dead_cap'],
                'cap_space': team_data['cap_space']
            }
        return {}
        
    def get_sample_roster(self):
        """Get sample roster for demo"""
        if 'rosters' in self.data:
            for team, roster in self.data['rosters'].items():
                if roster:
                    return roster[:15]  # Return first 15 players
        return []
        
    def get_top_contracts(self):
        """Get top contracts for demo"""
        if 'contracts' in self.data:
            return sorted(self.data['contracts'], 
                         key=lambda x: x['total_value'], 
                         reverse=True)[:10]
        return []
        
    def generate_performance_ratings(self):
        """Generate performance ratings for demo"""
        return {
            'concept_rating': 5.0,
            'drive_rating': 5.0,
            'formation_defensibility': 5.0,
            'formation_performance': 5.0,
            'play_sequence': 5.0,
            'scheme_rating': 5.0,
            'tactics_rating': 5.0,
            'play_comparison': 5.0
        }

def main():
    """Main execution function"""
    scraper = NFLDataScraper()
    
    print("🏈 NFL Executive Demo Data Scraper")
    print("=" * 50)
    
    # Scrape all data
    data = scraper.scrape_all_data()
    
    if data:
        # Save raw data
        scraper.save_data()
        
        # Export demo-formatted data
        demo_data = scraper.export_for_demo()
        
        print("\n🎯 Data Summary:")
        print(f"📊 Salary Cap Data: {len(data.get('salary_cap', []))} teams")
        print(f"💰 Multi-Year Cash: {len(data.get('multi_year_cash', []))} teams")
        print(f"👥 Team Rosters: {len(data.get('rosters', {}))} teams")
        print(f"📋 Contracts: {len(data.get('contracts', []))} contracts")
        
        print("\n✅ Ready to update NFL Executive Demo with real data!")
        
        return demo_data
    else:
        print("❌ Failed to scrape data")
        return None

if __name__ == "__main__":
    main()
