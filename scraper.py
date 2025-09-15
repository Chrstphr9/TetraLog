import streamlit as st
import asyncio
import os
from telethon import TelegramClient
from configparser import ConfigParser
from datetime import datetime
import csv
import json
import pandas as pd
from io import StringIO

class TelegramGroupScraperUI:
    def __init__(self):
        self.config_file = 'config.ini'
        self.config = ConfigParser()
        self.client = None
        self.setup_page()
        
    def setup_page(self):
        st.set_page_config(
            page_title="Telegram Group Scraper",
            page_icon="📡",
            layout="wide"
        )
        
        st.title("📡 Telegram Group Scraper")
        st.markdown("---")
        
    def sidebar_config(self):
        with st.sidebar:
            st.header("🔧 Configuration")
            
            # API Configuration
            api_id = st.text_input("API ID", type="password", help="Get from https://my.telegram.org")
            api_hash = st.text_input("API Hash", type="password")
            phone_number = st.text_input("Phone Number", placeholder="+1234567890")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Config"):
                    self.save_config(api_id, api_hash, phone_number)
            
            with col2:
                if st.button("📂 Load Config"):
                    self.load_config_to_ui()
            
            st.markdown("---")
            
            # Scraping Options
            st.header("🎯 Scraping Options")
            group_identifier = st.text_input(
                "Group Identifier", 
                placeholder="@group_username or group ID",
                help="Enter @username or group ID"
            )
            
            include_bots = st.checkbox("Include Bots", value=False)
            custom_filename = st.text_input("Custom Output Name (optional)")
            
            if st.button("🚀 Start Scraping", type="primary", use_container_width=True):
                if group_identifier:
                    self.run_scraping(group_identifier, include_bots, custom_filename)
                else:
                    st.error("Please enter a group identifier")
            
            st.markdown("---")
            st.info("💡 Only users with usernames will be collected")
    
    def save_config(self, api_id, api_hash, phone_number):
        if not all([api_id, api_hash, phone_number]):
            st.error("Please fill all configuration fields")
            return
            
        if not self.config.has_section('Telegram'):
            self.config.add_section('Telegram')
        
        self.config.set('Telegram', 'api_id', api_id)
        self.config.set('Telegram', 'api_hash', api_hash)
        self.config.set('Telegram', 'phone_number', phone_number)
        
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        
        st.success("Configuration saved successfully!")
    
    def load_config_to_ui(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            if self.config.has_section('Telegram'):
                # This would need JavaScript to set values - for demo purposes
                st.info("Configuration loaded. Values are in config file.")
            else:
                st.error("No valid configuration found")
        else:
            st.error("No configuration file found")
    
    async def scrape_group_members(self, group_identifier, include_bots=False, output_file=None):
        """Modified version of your scraper for Streamlit compatibility"""
        if not os.path.exists(self.config_file):
            st.error("Please save configuration first")
            return None
        
        self.config.read(self.config_file)
        api_id = self.config.get('Telegram', 'api_id')
        api_hash = self.config.get('Telegram', 'api_hash')
        phone_number = self.config.get('Telegram', 'phone_number')
        
        # Initialize client
        client = TelegramClient(
            session='telegram_session',
            api_id=int(api_id),
            api_hash=api_hash
        )
        
        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()
        
        members = []
        try:
            async with client:
                await client.start(phone=phone_number)
                
                status_container.info(f"🔍 Searching for group: {group_identifier}")
                
                # Get group entity
                try:
                    group = await client.get_entity(group_identifier)
                    status_container.success(f"✅ Found group: {getattr(group, 'title', 'Unknown')}")
                except Exception as e:
                    status_container.error(f"❌ Error finding group: {e}")
                    return None
                
                # Get all members
                status_container.info("📥 Fetching members (only those with username)...")
                
                all_members = []
                async for member in client.iter_participants(group):
                    all_members.append(member)
                
                total_members = len(all_members)
                processed = 0
                
                for member in all_members:
                    processed += 1
                    progress_bar.progress(processed / total_members)
                    
                    if member.bot and not include_bots:
                        continue
                    
                    if not member.username:
                        continue
                    
                    members.append({
                        'user_id': member.id,
                        'username': '@' + member.username,
                        'first_name': member.first_name or '',
                        'last_name': member.last_name or '',
                        'scraped_date': datetime.now().isoformat()
                    })
                
                status_container.success(f"✅ Scraping completed! Found {len(members)} members with usernames")
                
                return {
                    'group_name': getattr(group, 'title', group_identifier),
                    'members': members,
                    'total_scraped': len(members)
                }
                
        except Exception as e:
            status_container.error(f"❌ Error during scraping: {e}")
            return None
    
    def run_scraping(self, group_identifier, include_bots, custom_filename):
        """Run the scraping process"""
        with st.spinner("Starting scraping process..."):
            result = asyncio.run(self.scrape_group_members(group_identifier, include_bots))
            
            if result and result['members']:
                self.display_results(result, custom_filename)
    
    def display_results(self, result, custom_filename):
        """Display results and download options"""
        st.success(f"🎉 Successfully scraped {result['total_scraped']} members from {result['group_name']}")
        
        # Create DataFrame for display
        df = pd.DataFrame(result['members'])
        
        # Display preview
        st.subheader("📊 Data Preview")
        st.dataframe(df.head(10))
        
        # Generate filename
        if custom_filename:
            base_name = custom_filename
        else:
            safe_name = "".join(c for c in result['group_name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{safe_name}_members_{timestamp}"
        
        # CSV Download
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{base_name}.csv",
            mime="text/csv"
        )
        
        # JSON Download
        json_data = {
            'scraped_at': datetime.now().isoformat(),
            'group_name': result['group_name'],
            'total_members': result['total_scraped'],
            'members': result['members']
        }
        
        st.download_button(
            label="📥 Download JSON",
            data=json.dumps(json_data, indent=2),
            file_name=f"{base_name}.json",
            mime="application/json"
        )
    
    def run(self):
        """Main run method"""
        self.sidebar_config()
        
        # Main content
        st.header("📋 Instructions")
        st.markdown("""
        1. **Configure API**: Enter your Telegram API credentials from [my.telegram.org](https://my.telegram.org)
        2. **Save Configuration**: Click 'Save Config' to store your credentials
        3. **Enter Group**: Provide the group @username or ID
        4. **Start Scraping**: Click the button to begin
        5. **Download**: Get your data in CSV or JSON format
        
        ⚠️ **Note**: Only users with public usernames will be collected
        """)
        
        # Display session info if available
        if os.path.exists('config.ini'):
            st.sidebar.success("✅ Configuration file found")
        
        st.markdown("---")
        st.caption("Made with Streamlit & Telethon")

# Run the app
if __name__ == "__main__":
    app = TelegramGroupScraperUI()
    app.run()