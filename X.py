from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
import asyncio
import csv
import json
import random
from datetime import datetime
import os

class TelegramChannelManager:
    def __init__(self, config_file='config.ini', added_file='added_users.json'):
        self.config_file = config_file
        self.added_file = added_file
        self.client = None
        self.added_users = self._load_added_users()

    def _load_added_users(self):
        """Load already-added users from JSON file."""
        if os.path.exists(self.added_file):
            with open(self.added_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def _save_added_users(self):
        """Save updated list of added users."""
        with open(self.added_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.added_users), f, indent=2)

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

    async def add_users_to_channel(self, channel_username, users_data, batch_size=5, delay=3, limit=15):
        """Add up to `limit` users, skipping duplicates"""
        try:
            channel = await self.client.get_entity(channel_username)
            print(f"📋 Target channel: {getattr(channel, 'title', 'Unknown')}")

            total_added = 0
            total_failed = 0

            # Filter users that are not already added
            filtered_users = [u for u in users_data if self._get_user_identifier(u) not in self.added_users]

            # Limit to 15 users max
            users_data = filtered_users[:limit]

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
                        await self.client(InviteToChannelRequest(channel=channel, users=users_to_add))
                        added_in_batch = len(users_to_add)
                        total_added += added_in_batch

                        # Save added users
                        for user in batch:
                            self.added_users.add(self._get_user_identifier(user))
                        self._save_added_users()

                        print(f"   ✅ Successfully added {added_in_batch} users to channel")
                    except Exception as e:
                        print(f"   ❌ Failed to add batch: {e}")
                        total_failed += len(users_to_add)

                if total_added >= limit:
                    print("⏹️ Limit reached (15 users). Stopping...")
                    break

                if i + batch_size < len(users_data):
                    print(f"⏳ Waiting {delay} seconds before next batch...")
                    await asyncio.sleep(delay)

            print(f"\n🎉 Channel Addition Complete!")
            print(f"   Total successfully added: {total_added}")
            print(f"   Total failed: {total_failed}")

            return total_added, total_failed

        except Exception as e:
            print(f"❌ Error in add_users_to_channel: {e}")
            return 0, len(users_data)

    async def _get_user_entity(self, user_data):
        try:
            if user_data.get('username'):
                username = user_data['username']
                if not username.startswith('@'):
                    username = '@' + username
                return await self.client.get_entity(username)
            if user_data.get('user_id'):
                return await self.client.get_entity(int(user_data['user_id']))
            if user_data.get('phone'):
                return await self._get_user_by_phone(user_data['phone'])
            return None
        except Exception:
            if user_data.get('phone'):
                return await self._get_user_by_phone(user_data['phone'])
            return None

    async def _get_user_by_phone(self, phone_number):
        try:
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
        if user_data.get('username'):
            return user_data['username'].lower()
        elif user_data.get('user_id'):
            return f"ID:{user_data['user_id']}"
        elif user_data.get('phone'):
            return f"PHONE:{user_data['phone']}"
        else:
            return "UNKNOWN"

    async def load_scraped_data(self, csv_file):
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


# Main
async def main():
    manager = TelegramChannelManager()

    API_ID = '27859634'
    API_HASH = '1282021130f80b5d74c806158149f7d9'
    PHONE_NUMBER = '+4915772334180'

    TARGET_CHANNEL = 'https://t.me/+nZZuq9C8EZxkMmZi'
    SCRAPED_CSV = 'your_group_username_members_20250829_142923.csv'

    if not await manager.initialize_client(API_ID, API_HASH, PHONE_NUMBER):
        return

    try:
        users_data = await manager.load_scraped_data(SCRAPED_CSV)
        if not users_data:
            return

        print(f"\n🚀 Adding up to 15 users to channel...")

        added, failed = await manager.add_users_to_channel(
            channel_username=TARGET_CHANNEL,
            users_data=users_data,
            batch_size=5,
            delay=3,
            limit=15
        )

        results = {
            'operation_date': datetime.now().isoformat(),
            'target_channel': TARGET_CHANNEL,
            'successfully_added': added,
            'failed_to_add': failed
        }

        with open('operation_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📊 Results saved to operation_results.json")

    finally:
        await manager.client.disconnect()
        print("✅ Client disconnected")


if __name__ == "__main__":
    asyncio.run(main())
