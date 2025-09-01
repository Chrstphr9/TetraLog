from telethon import TelegramClient
import asyncio
import csv
import json
import os
from configparser import ConfigParser
from datetime import datetime

class TelegramGroupScraper:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = ConfigParser()
        self.client = None
        
    def load_config(self):
        """Load configuration from file or create new one"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            return True
        return False
    
    def save_config(self, api_id, api_hash, phone_number):
        """Save configuration to file"""
        if not self.config.has_section('Telegram'):
            self.config.add_section('Telegram')
        
        self.config.set('Telegram', 'api_id', str(api_id))
        self.config.set('Telegram', 'api_hash', api_hash)
        self.config.set('Telegram', 'phone_number', phone_number)
        
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        print(f"Configuration saved to {self.config_file}")
    
    def get_credentials(self):
        """Get credentials from user input or config file"""
        if self.load_config():
            print("Loaded existing configuration.")
            return (
                self.config.get('Telegram', 'api_id'),
                self.config.get('Telegram', 'api_hash'),
                self.config.get('Telegram', 'phone_number')
            )
        else:
            print("No configuration found. Please enter your Telegram API credentials:")
            api_id = input("API ID: ").strip()
            api_hash = input("API Hash: ").strip()
            phone_number = input("Phone Number (with country code, e.g., +1234567890): ").strip()
            
            # Save credentials for future use
            self.save_config(api_id, api_hash, phone_number)
            return api_id, api_hash, phone_number
    
    async def initialize_client(self):
        """Initialize Telegram client"""
        api_id, api_hash, phone_number = self.get_credentials()
        
        self.client = TelegramClient(
            session='telegram_session',
            api_id=int(api_id),
            api_hash=api_hash
        )
        
        return phone_number
    
    async def scrape_group_members(self, group_identifier, output_file=None, include_bots=False):
        """
        Scrape members from a specific group/channel.
        🚨 Only collects users that have a USERNAME.
        """
        phone_number = await self.initialize_client()
        
        async with self.client:
            await self.client.start(phone=phone_number)
            
            print(f"🔍 Searching for group: {group_identifier}")
            
            # Get group entity
            try:
                group = await self.client.get_entity(group_identifier)
                print(f"✅ Found group: {getattr(group, 'title', 'Unknown')}")
            except Exception as e:
                print(f"❌ Error finding group '{group_identifier}': {e}")
                return
            
            print("📥 Fetching members (only those with username)...")
            
            # Get all members
            members = []
            try:
                async for member in self.client.iter_participants(group):
                    # Skip bots unless explicitly requested
                    if member.bot and not include_bots:
                        continue
                    
                    # Skip users without a username
                    if not member.username:
                        continue
                    
                    members.append({
                        'user_id': member.id,
                        'username': '@' + member.username,
                        'scraped_date': datetime.now().isoformat()
                    })
                    
                    if len(members) % 100 == 0:
                        print(f"   📊 Collected {len(members)} members with usernames...")
                
                print(f"✅ Total members with username: {len(members)}")
            except Exception as e:
                print(f"❌ Error fetching members: {e}")
                return
            
            # Generate output filename if not provided
            if output_file is None:
                group_name = getattr(group, 'title', group_identifier)
                safe_name = "".join(c for c in group_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"{safe_name}_members_{timestamp}.csv"
            
            # Save results
            await self.save_to_csv(members, output_file)
            await self.save_to_json(members, output_file.replace('.csv', '.json'))
            
            print(f"\n📊 SCRAPING SUMMARY:")
            print(f"   Group: {getattr(group, 'title', 'Unknown')}")
            print(f"   Members with usernames: {len(members)}")
            print(f"   Output files: {output_file}, {output_file.replace('.csv', '.json')}")
    
    async def save_to_csv(self, data, filename):
        """Save scraped members to CSV"""
        if not data:
            print("⚠️ No data to save")
            return
        
        fieldnames = ['user_id', 'username', 'scraped_date']
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ CSV saved: {filename}")
    
    async def save_to_json(self, data, filename):
        """Save scraped members to JSON"""
        if not data:
            return
        
        output_data = {
            'scraped_at': datetime.now().isoformat(),
            'total_members': len(data),
            'members': data
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
        print(f"✅ JSON saved: {filename}")


# Example usage
async def main():
    scraper = TelegramGroupScraper()
    
    group_to_scrape = "@your_group_username"  # Change this
    await scraper.scrape_group_members(
        group_identifier=group_to_scrape,
        include_bots=False
    )

if __name__ == "__main__":
    asyncio.run(main())
