import streamlit as st
import asyncio
try:
    from X import TelegramChannelManager
except Exception as import_error:
    TelegramChannelManager = None
    _telethon_import_error = import_error
import json
import pandas as pd
import os
from datetime import datetime

st.title("TetraLogX")
st.write("Upload a CSV file with user data and add them to your Telegram channel/group")

# Create two columns for better layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔑 API Credentials")
    api_id = st.text_input("API ID", help="Get from https://my.telegram.org")
    api_hash = st.text_input("API Hash", type="password", help="Get from https://my.telegram.org")
    phone_number = st.text_input("Phone Number", placeholder="+1234567890", help="Include country code")

with col2:
    st.subheader("⚙️ Settings")
    channel = st.text_input("Channel/Group Link", placeholder="https://t.me/yourgroup or @username")
    limit = st.number_input("Number of users to add", min_value=1, max_value=50, value=15)
    batch_size = st.number_input("Batch size", min_value=1, max_value=10, value=5)
    delay = st.number_input("Delay between batches (seconds)", min_value=1, max_value=30, value=3)

st.subheader("📁 User Data Source")
data_source = st.radio(
    "Choose data source:",
    ["📤 Upload CSV file", "📝 Enter data manually"],
    horizontal=True
)

uploaded_file = None
users_data = None

if data_source == "📤 Upload CSV file":
    uploaded_file = st.file_uploader(
        "Upload CSV file with users", 
        type=["csv"],
        help="CSV should contain columns: username, user_id (required), phone, first_name, last_name (optional)"
    )
    
elif data_source == "📝 Enter data manually":
    st.info("Enter user data manually (one user per row)")
    
    # Manual data entry
    num_users = st.number_input("Number of users to add", min_value=1, max_value=20, value=3)
    
    manual_users = []
    for i in range(num_users):
        st.write(f"**User {i+1}:**")
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input(f"Username {i+1}", key=f"username_{i}")
            user_id = st.text_input(f"User ID {i+1}", key=f"user_id_{i}")
        with col2:
            phone = st.text_input(f"Phone {i+1}", key=f"phone_{i}")
            first_name = st.text_input(f"First Name {i+1}", key=f"first_name_{i}")
            last_name = st.text_input(f"Last Name {i+1}", key=f"last_name_{i}")
        
        if username or user_id or phone:
            manual_users.append({
                'username': username,
                'user_id': user_id,
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name
            })
    
    if manual_users:
        users_data = manual_users
        st.write(f"📝 **Manual Data:** {len(manual_users)} users entered")
        manual_df = pd.DataFrame(manual_users)
        st.dataframe(manual_df, use_container_width=True)

# Show preview of uploaded CSV file
if data_source == "📤 Upload CSV file" and uploaded_file is not None:
    try:
        # Reset file pointer to beginning
        uploaded_file.seek(0)
        
        # Try to read CSV with different encodings
        df = None
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, dtype=str, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception:
                continue
        
        if df is None or df.empty:
            st.error("❌ CSV file is empty or could not be read. Please check your file.")
        elif len(df.columns) == 0:
            st.error("❌ CSV file has no columns. Please check your file format.")
        else:
            st.write("📋 **File Preview:**")
            st.dataframe(df.head(), use_container_width=True)
            st.write(f"Total users in file: {len(df)}")
            st.write(f"Columns found: {', '.join(df.columns)}")
            
            # Validate required columns
            required_columns = ['username', 'user_id']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.warning(f"⚠️ Missing required columns: {', '.join(missing_columns)}")
            else:
                st.success("✅ All required columns found!")
                # Check for optional columns
                optional_columns = ['phone', 'first_name', 'last_name']
                available_optional = [col for col in optional_columns if col in df.columns]
                if available_optional:
                    st.info(f"📋 Optional columns found: {', '.join(available_optional)}")
                
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {e}")
        st.info("💡 Make sure your CSV file has headers and contains data")

# Show existing added users count
if os.path.exists('added_users.json'):
    with open('added_users.json', 'r') as f:
        added_users = json.load(f)
    st.info(f"📊 Previously added users: {len(added_users)}")

if st.button("🚀 Start Adding Users", type="primary"):
    if TelegramChannelManager is None:
        st.error("Telethon (and dependencies) are not installed. Please install requirements and reload.")
        st.code("pip install -r requirements.txt")
        if '_telethon_import_error' in globals():
            st.exception(_telethon_import_error)
        raise SystemExit
    if not (api_id and api_hash and phone_number):
        st.error("⚠️ Please fill in all API credentials.")
    elif data_source == "📤 Upload CSV file" and not uploaded_file:
        st.error("⚠️ Please upload a CSV file.")
    elif data_source == "📝 Enter data manually" and not users_data:
        st.error("⚠️ Please provide user data.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            manager = TelegramChannelManager()

            async def run_addition():
                status_text.text("🔄 Initializing Telegram client...")
                ok = await manager.initialize_client(api_id, api_hash, phone_number)
                if not ok:
                    st.error("❌ Could not connect to Telegram. Check API credentials.")
                    return

                status_text.text("📊 Processing user data...")
                progress_bar.progress(0.1)

                # Load users data based on source
                if data_source == "📤 Upload CSV file":
                    # Load from uploaded file
                    uploaded_file.seek(0)
                    try:
                        df = pd.read_csv(uploaded_file, dtype=str, encoding='utf-8')
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, dtype=str, encoding='latin-1')
                    
                    if df.empty or len(df.columns) == 0:
                        st.error("❌ CSV file is empty or has no columns. Please check your file.")
                        return
                    
                    users_data = df.fillna("").to_dict("records")
                # For manual data, users_data is already loaded

                # Normalize data to match X.py expectations
                for user in users_data:
                    # Clean username
                    if user.get("username"):
                        u = str(user["username"]).strip()
                        if u and u != "nan":
                            if not u.startswith("@"):
                                user["username"] = f"@{u}"
                        else:
                            user["username"] = ""

                    # Clean phone
                    if user.get("phone"):
                        phone = str(user["phone"]).strip()
                        if phone and phone != "nan":
                            user["phone"] = phone
                        else:
                            user["phone"] = ""

                    # Clean user_id
                    if user.get("user_id"):
                        try:
                            uid = str(user["user_id"]).strip()
                            if uid and uid != "nan":
                                user["user_id"] = int(uid)
                            else:
                                user["user_id"] = ""
                        except (ValueError, TypeError):
                            user["user_id"] = ""

                progress_bar.progress(0.2)
                status_text.text(f"🚀 Adding up to {limit} users to channel...")

                added, failed = await manager.add_users_to_channel(
                    channel_username=channel,
                    users_data=users_data,  # X.py handles the limit internally
                    batch_size=batch_size,
                    delay=delay,
                    limit=limit  # Pass limit parameter
                )

                progress_bar.progress(1.0)
                
                # Save results
                results = {
                    "operation_date": datetime.now().isoformat(),
                    "target_channel": channel,
                    "successfully_added": added,
                    "failed_to_add": failed,
                    "total_users_in_file": len(users_data),
                    "limit_set": limit
                }
                
                with open("operation_results.json", "w") as f:
                    json.dump(results, f, indent=2)

                status_text.text("✅ Operation completed!")
                st.success(f"✅ Done! Successfully added: {added}, Failed: {failed}")
                
                # Display results in expandable section
                with st.expander("📊 Detailed Results"):
                    st.json(results)

                await manager.client.disconnect()

            # Run the async function
            asyncio.run(run_addition())
            
        except Exception as e:
            st.error(f"❌ An error occurred: {e}")
            progress_bar.progress(0)
            status_text.text("❌ Operation failed")

# Add information section
with st.expander("ℹ️ How to use"):
    st.markdown("""
    1. **Get API Credentials**: Visit https://my.telegram.org to get your API ID and API Hash
    2. **Choose Data Source**: 
       - **Upload CSV**: Upload your own CSV file with user data
       - **Enter Manually**: Type user data directly into the form
    3. **CSV Format**: 
       - **Required**: `username`, `user_id`
       - **Optional**: `phone`, `first_name`, `last_name`
    4. **Set Parameters**: Configure how many users to add and batch settings
    5. **Run**: Click "Start Adding Users" and wait for completion
    
    **Note**: The app tracks previously added users to avoid duplicates.
    """)

