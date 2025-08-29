from telethon import TelegramClient
import asyncio

async def test_channel_access():
    """Test script to check channel access and find available channels"""
    
    API_ID = '27859634'
    API_HASH = '1282021130f80b5d74c806158149f7d9'
    PHONE_NUMBER = '+4915772334180'
    
    # Test different channel formats
    test_channels = [
        '@tetralog',
        'tetralog',
        'https://t.me/tetralog',
        'Tetralog'
    ]
    
    client = TelegramClient(f'session_{PHONE_NUMBER}', int(API_ID), API_HASH)
    
    try:
        await client.start(phone=PHONE_NUMBER)
        print(f"✅ Connected as {PHONE_NUMBER}")
        
        print("\n🔍 Testing channel access...")
        print("=" * 50)
        
        for channel_id in test_channels:
            try:
                print(f"\nTesting: {channel_id}")
                channel = await client.get_entity(channel_id)
                print(f"   ✅ SUCCESS: {getattr(channel, 'title', 'Unknown')}")
                print(f"   ID: {channel.id}")
                print(f"   Type: {type(channel).__name__}")
                print(f"   Username: {getattr(channel, 'username', 'None')}")
                
                # Check if we can get participants (admin check)
                try:
                    participants = await client.get_participants(channel, limit=1)
                    print(f"   🔑 Access: Can view participants")
                except Exception as e:
                    print(f"   🔒 Access: Limited - {str(e)[:50]}...")
                    
            except Exception as e:
                print(f"   ❌ FAILED: {str(e)[:50]}...")
        
        print("\n" + "=" * 50)
        print("💡 If all channels failed, try:")
        print("   1. Check if the channel name is correct")
        print("   2. Make sure you're a member of the channel")
        print("   3. Try using a channel you know exists")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    
    finally:
        await client.disconnect()
        print("\n✅ Disconnected")

if __name__ == "__main__":
    asyncio.run(test_channel_access()) 