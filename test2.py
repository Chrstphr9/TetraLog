from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact, InputUser
import asyncio
import csv
import json
import random
import time
from datetime import datetime

class TelegramChannelManager:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.client = None
        
    async def initialize_client(self, api_id, api_hash, phone_number):
        """Initialize Telegram client"""
        self.client = TelegramClient(
            session=f'session_{phone_number}',
            api_id=int(api_id),
            api_hash=api_hash
        )
        
        try:
            await self.client.start(phone=phone_number)
            print(f"✅ Successfully initialized client for {phone_number}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize client for {phone_number}: {e}")
            return False

    async def add_users_to_channel(self, channel_username, users_data, batch_size=10, delay=2):
        """
        Add multiple users to a channel using various identifiers
        
        Args:
            channel_username: Target channel username (@channelname)
            users_data: List of user dictionaries from scraped data
            batch_size: Number of users to process in each batch
            delay: Delay between batches in seconds
        """
        try:
            # Get channel entity
            channel = await self.client.get_entity(channel_username)
            print(f"📋 Target channel: {getattr(channel, 'title', 'Unknown')}")
            
            total_added = 0
            total_failed = 0
            
            # Process users in batches
            for i in range(0, len(users_data), batch_size):
                batch = users_data[i:i + batch_size]
                print(f"\n🔄 Processing batch {i//batch_size + 1}/{(len(users_data)-1)//batch_size + 1}")
                
                users_to_add = []
                
                for user in batch:
                    try:
                        user_entity = await self._get_user_entity(user)
                        if user_entity:
                            users_to_add.append(user_entity)
                            print(f"   ✅ Prepared: {self._get_user_identifier(user)}")
                        else:
                            print(f"   ❌ Could not resolve: {self._get_user_identifier(user)}")
                            total_failed += 1
                    except Exception as e:
                        print(f"   ❌ Error processing {self._get_user_identifier(user)}: {e}")
                        total_failed += 1
                
                if users_to_add:
                    try:
                        # Add users to channel
                        await self.client(InviteToChannelRequest(
                            channel=channel,
                            users=users_to_add
                        ))
                        
                        added_in_batch = len(users_to_add)
                        total_added += added_in_batch
                        print(f"   ✅ Successfully added {added_in_batch} users to channel")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to add batch: {e}")
                        total_failed += len(users_to_add)
                
                # Delay between batches to avoid rate limiting
                if i + batch_size < len(users_data):
                    print(f"⏳ Waiting {delay} seconds before next batch...")
                    await asyncio.sleep(delay)
            
            print(f"\n🎉 Channel Addition Complete!")
            print(f"   Total successfully added: {total_added}")
            print(f"   Total failed: {total_failed}")
            print(f"   Success rate: {(total_added/(total_added+total_failed))*100:.1f}%")
            
            return total_added, total_failed
            
        except Exception as e:
            print(f"❌ Error in add_users_to_channel: {e}")
            return 0, len(users_data)

    async def _get_user_entity(self, user_data):
        """Get user entity using available identifiers"""
        try:
            # Try username first (most reliable)
            if user_data.get('username') and user_data['username'].startswith('@'):
                return await self.client.get_entity(user_data['username'])
            
            # Try user ID
            if user_data.get('user_id'):
                return await self.client.get_entity(int(user_data['user_id']))
            
            # Try phone number (requires importing as contact first)
            if user_data.get('phone'):
                return await self._get_user_by_phone(user_data['phone'])
            
            return None
            
        except Exception as e:
            # If all methods fail, try to import contact by phone
            if user_data.get('phone'):
                return await self._get_user_by_phone(user_data['phone'])
            return None

    async def _get_user_by_phone(self, phone_number):
        """Get user entity by phone number (imports as contact first)"""
        try:
            # Import contact
            from telethon.tl.types import InputPhoneContact
            
            contact = InputPhoneContact(
                client_id=random.randrange(-2**63, 2**63),
                phone=phone_number,
                first_name="",
                last_name=""
            )
            
            result = await self.client(ImportContactsRequest([contact]))
            
            if result.users:
                return result.users[0]
            return None
            
        except Exception as e:
            print(f"   ❌ Error importing phone contact {phone_number}: {e}")
            return None

    def _get_user_identifier(self, user_data):
        """Get readable user identifier for logging"""
        if user_data.get('username'):
            return user_data['username']
        elif user_data.get('user_id'):
            return f"ID:{user_data['user_id']}"
        elif user_data.get('phone'):
            return f"PHONE:{user_data['phone']}"
        else:
            return "UNKNOWN"

    async def load_scraped_data(self, csv_file):
        """Load scraped data from CSV file"""
        users = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                users = list(reader)
            
            print(f"📊 Loaded {len(users)} users from {csv_file}")
            return users
            
        except Exception as e:
            print(f"❌ Error loading CSV file: {e}")
            return []

    async def verify_consent(self, users_data, consent_file='consent_records.json'):
        """Verify that all users have given consent"""
        try:
            with open(consent_file, 'r') as f:
                consent_data = json.load(f)
            
            consented_users = []
            non_consented_users = []
            
            for user in users_data:
                user_id = user.get('user_id', '')
                username = user.get('username', '')
                phone = user.get('phone', '')
                
                # Check if any identifier exists in consent records
                if (user_id and user_id in consent_data.get('user_ids', [])) or \
                   (username and username in consent_data.get('usernames', [])) or \
                   (phone and phone in consent_data.get('phones', [])):
                    consented_users.append(user)
                else:
                    non_consented_users.append(user)
            
            print(f"📋 Consent Verification:")
            print(f"   Users with consent: {len(consented_users)}")
            print(f"   Users without consent: {len(non_consented_users)}")
            
            if non_consented_users:
                print("❌ WARNING: Some users lack consent. Aborting operation.")
                return []
            
            return consented_users
            
        except FileNotFoundError:
            print("❌ Consent file not found. Aborting.")
            return []
        except Exception as e:
            print(f"❌ Error verifying consent: {e}")
            return []

    async def create_consent_template(self):
        """Create a consent file template for educational purposes"""
        template = {
            "educational_purpose": "User onboarding for research study",
            "consent_date": datetime.now().isoformat(),
            "user_ids": ["123456789", "987654321"],
            "usernames": ["@user1", "@user2"],
            "phones": ["+1234567890", "+0987654321"],
            "consent_terms": {
                "data_usage": "Educational research only",
                "storage_duration": "30 days",
                "right_to_withdraw": "Yes",
                "contact_info": "researcher@university.edu"
            }
        }
        
        with open('consent_template.json', 'w') as f:
            json.dump(template, f, indent=2)
        
        print("✅ Created consent template: consent_template.json")

# Main execution function
async def main():
    manager = TelegramChannelManager()
    
    print("🤖 Telegram Channel User Manager - Educational Use")
    print("=" * 60)
    print("⚠️  REQUIRES SIGNED CONSENT FROM ALL USERS")
    print("⚠️  FOR EDUCATIONAL PURPOSES ONLY")
    print("=" * 60)
    
    # Your account credentials (from my.telegram.org)
    API_ID = '27859634'
    API_HASH = '1282021130f80b5d74c806158149f7d9'
    PHONE_NUMBER = '+4915772334180'  # Your account phone number
    
    # Target channel and data files
    TARGET_CHANNEL = '@your_educational_channel'  # Change this
    SCRAPED_CSV = 'your_group_username_members_20250821_174632.csv'  # Your scraped data file
    CONSENT_FILE = 'signed_consent.json'  # Your consent records
    
    # Initialize client
    if not await manager.initialize_client(API_ID, API_HASH, PHONE_NUMBER):
        return
    
    try:
        # Load scraped data
        users_data = await manager.load_scraped_data(SCRAPED_CSV)
        if not users_data:
            return
        
        # Verify consent (CRITICAL STEP)
        consented_users = await manager.verify_consent(users_data, CONSENT_FILE)
        if not consented_users:
            print("❌ Operation aborted due to consent issues")
            return
        
        print(f"\n🚀 Starting to add {len(consented_users)} consented users to channel...")
        
        # Add users to channel
        added, failed = await manager.add_users_to_channel(
            channel_username=TARGET_CHANNEL,
            users_data=consented_users,
            batch_size=5,  # Smaller batches to avoid rate limits
            delay=3        # Longer delay for safety
        )
        
        # Save operation results
        results = {
            'operation_date': datetime.now().isoformat(),
            'target_channel': TARGET_CHANNEL,
            'total_users': len(consented_users),
            'successfully_added': added,
            'failed_to_add': failed,
            'success_rate': f"{(added/(added+failed))*100:.1f}%" if added+failed > 0 else "0%"
        }
        
        with open('operation_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Results saved to operation_results.json")
        
    finally:
        await manager.client.disconnect()
        print("✅ Client disconnected")

# Alternative: Batch processing with multiple accounts
async def batch_processing_with_multiple_accounts():
    """Example for handling large numbers of users with multiple accounts"""
    accounts = [
        {'api_id': 'id1', 'api_hash': 'hash1', 'phone': '+1111111111'},
        {'api_id': 'id2', 'api_hash': 'hash2', 'phone': '+2222222222'},
        # Add more test accounts as needed
    ]
    
    users_data = []  # Load your scraped data here
    target_channel = '@your_channel'
    
    users_per_account = len(users_data) // len(accounts)
    
    for i, account in enumerate(accounts):
        print(f"\n👤 Processing with account {i+1}: {account['phone']}")
        
        manager = TelegramChannelManager()
        if await manager.initialize_client(account['api_id'], account['api_hash'], account['phone']):
            
            # Get this account's share of users
            start_idx = i * users_per_account
            end_idx = start_idx + users_per_account if i < len(accounts) - 1 else len(users_data)
            account_users = users_data[start_idx:end_idx]
            
            added, failed = await manager.add_users_to_channel(
                target_channel, account_users, batch_size=3, delay=5
            )
            
            await manager.client.disconnect()
            
            # Wait before next account
            await asyncio.sleep(10)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
    
    # For creating consent template (run once)
    # manager = TelegramChannelManager()
    # asyncio.run(manager.create_consent_template())