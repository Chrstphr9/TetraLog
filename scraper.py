from telethon import TelegramClient, events
import asyncio
import csv
import json
import os
from configparser import ConfigParser
from datetime import datetime
import time

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
            print("(Get these from https://my.telegram.org)")
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
        Scrape members from a specific group/channel
        
        Args:
            group_identifier: Group username (@groupname), invite link, or group name
            output_file: Custom output filename (optional)
            include_bots: Whether to include bot accounts
        """
        phone_number = await self.initialize_client()
        
        async with self.client:
            await self.client.start(phone=phone_number)
            
            print(f"🔍 Searching for group: {group_identifier}")
            
            # Get group entity
            try:
                group = await self.client.get_entity(group_identifier)
                print(f"Found group: {getattr(group, 'title', 'Unknown')}")
                print(f"   Group ID: {group.id}")
                print(f"   Group Type: {type(group).__name__}")
            except Exception as e:
                print(f"Error finding group '{group_identifier}': {e}")
                print("Try using:")
                print("   - @username (for public groups)")
                print("   - Exact group name")
                print("   - Group invite link")
                return
            
            print("📥 Fetching members... (this may take a while for large groups)")
            
            # Get all members with progress tracking
            try:
                members = []
                async for member in self.client.iter_participants(group):
                    members.append(member)
                    if len(members) % 100 == 0:
                        print(f"   📊 Fetched {len(members)} members...")
                
                print(f"✅ Total members found: {len(members)}")
                
            except Exception as e:
                print(f"Error fetching members: {e}")
                print("💡 Possible reasons:")
                print("   - Group restricts member list access")
                print("   - You don't have permission to view members")
                print("   - Group is private and you're not a member")
                return
            
            # Process member data - ONLY user_id, username, and phone
            member_data = []
            phone_numbers_found = 0
            usernames_found = 0
            
            for i, member in enumerate(members):
                # Skip bots unless requested
                if member.bot and not include_bots:
                    continue
                
                # Get phone number if available
                phone_number = getattr(member, 'phone', '')
                if phone_number:
                    phone_numbers_found += 1
                
                # Get username and add @ prefix
                username = getattr(member, 'username', '')
                if username:
                    username = '@' + username
                    usernames_found += 1
                
                # Extract only user_id, username, and phone
                member_info = {
                    'user_id': member.id,
                    'username': username,
                    'phone': phone_number or '',
                    'scraped_date': datetime.now().isoformat()
                }
                
                member_data.append(member_info)
            
            # Generate output filename if not provided
            if output_file is None:
                group_name = getattr(group, 'title', group_identifier)
                # Clean filename
                safe_name = "".join(c for c in group_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"{safe_name}_members_{timestamp}.csv"
            
            # Save to CSV
            await self.save_to_csv(member_data, output_file)
            
            # Also save as JSON for better structure
            json_file = output_file.replace('.csv', '.json')
            await self.save_to_json(member_data, json_file)
            
            # Print summary
            print(f"\n📊 SCRAPING SUMMARY:")
            print(f"   Group: {getattr(group, 'title', 'Unknown')}")
            print(f"   Total members processed: {len(member_data)}")
            print(f"   Members with phone numbers: {phone_numbers_found}")
            print(f"   Members with usernames: {usernames_found}")
            print(f"   Bots included: {include_bots}")
            print(f"   Output files: {output_file}, {json_file}")
    
    async def save_to_csv(self, data, filename):
        """Save data to CSV file - only user_id, username, phone"""
        if not data:
            print("No data to save")
            return
        
        fieldnames = ['user_id', 'username', 'phone', 'scraped_date']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✅ CSV saved: {filename} ({len(data)} records)")
    
    async def save_to_json(self, data, filename):
        """Save data to JSON file - only user_id, username, phone"""
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
    
    async def scrape_multiple_groups(self, group_list, include_bots=False):
        """Scrape multiple groups in sequence"""
        print(f"🚀 Starting batch scraping of {len(group_list)} groups...")
        
        for i, group_id in enumerate(group_list, 1):
            print(f"\n📍 Processing group {i}/{len(group_list)}: {group_id}")
            await self.scrape_group_members(group_id, include_bots=include_bots)
            
            # Add delay between groups to avoid rate limiting
            if i < len(group_list):
                print("⏳ Waiting 3 seconds before next group...")
                await asyncio.sleep(3)
        
        print(f"\n🎉 Batch scraping completed! Processed {len(group_list)} groups.")
    
    async def get_group_info(self, group_identifier):
        """Get basic information about a group without scraping members"""
        phone_number = await self.initialize_client()
        
        async with self.client:
            await self.client.start(phone=phone_number)
            
            try:
                group = await self.client.get_entity(group_identifier)
                
                info = {
                    'id': group.id,
                    'title': getattr(group, 'title', 'Unknown'),
                    'username': getattr(group, 'username', ''),
                    'type': type(group).__name__,
                    'members_count': getattr(group, 'participants_count', 'Unknown'),
                    'description': getattr(group, 'about', ''),
                    'verified': getattr(group, 'verified', False),
                    'scam': getattr(group, 'scam', False),
                    'fake': getattr(group, 'fake', False)
                }
                
                print("📋 GROUP INFORMATION:")
                for key, value in info.items():
                    print(f"   {key}: {value}")
                
                return info
                
            except Exception as e:
                print(f"❌ Error getting group info: {e}")
                return None

    async def export_phone_numbers(self, csv_file, output_phones_file=None):
        """Extract just phone numbers from a scraped CSV file"""
        if not output_phones_file:
            output_phones_file = csv_file.replace('.csv', '_phones.txt')
        
        phones = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['phone'] and row['phone'].strip():
                        phones.append(row['phone'].strip())
            
            # Remove duplicates
            phones = list(set(phones))
            
            # Save to file
            with open(output_phones_file, 'w', encoding='utf-8') as f:
                for phone in phones:
                    f.write(phone + '\n')
            
            print(f"✅ Extracted {len(phones)} unique phone numbers to {output_phones_file}")
            return phones
            
        except Exception as e:
            print(f"❌ Error extracting phone numbers: {e}")
            return []

# Example usage and testing
async def main():
    scraper = TelegramGroupScraper()
    
    print("🤖 Telegram Group Member Scraper")
    print("=" * 50)
    print("⚠️  EDUCATIONAL USE ONLY - Respect Privacy!")
    print("⚠️  Phone number scraping may violate:")
    print("   - Telegram Terms of Service")
    print("   - Privacy laws (GDPR, CCPA, etc.)")
    print("   - Ethical guidelines")
    print("=" * 50)
    
    # Method 1: Single group scraping
    print("\n1️⃣ Single Group Scraping:")
    
    # Replace with your target group
    group_to_scrape = "@your_group_username"  # Change this to your target group
    
    # Get group info first (optional)
    await scraper.get_group_info(group_to_scrape)
    
    # Scrape the group
    await scraper.scrape_group_members(
        group_identifier=group_to_scrape,
        include_bots=False  # Set to True to include bots
    )
    
    # Method 2: Extract phone numbers from existing CSV
    # await scraper.export_phone_numbers('your_scraped_file.csv')

if __name__ == "__main__":
    asyncio.run(main())