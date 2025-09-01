from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import datetime
import os

# ================= CONFIG =================
API_ID = 22963476
API_HASH = "4df552f09c239685a58db6afcc8ca946"
BOT_TOKEN = "8386284438:AAH0ZCxTVw5g7fbE1exrXi6hvUZlS6Rk-yQ"
ADMIN_ID = 7704212317
UPI_ID = "gauravyadav349@axl"

# ================= BOT INIT =================
app = Client("premium_forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= DATABASE SETUP =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    plan TEXT,
    group_limit INTEGER,
    status TEXT
)
""")

# Orders table
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan TEXT,
    amount INTEGER,
    status TEXT,
    payment_screenshot TEXT,
    order_date TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# Links table (source channel -> target group)
cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    source_chat_id TEXT,
    target_chat_id TEXT
)
""")
conn.commit()

# ================= PLANS =================
PLANS = {
    "Free": {"price": 0, "limit": 1},
    "Silver": {"price": 49, "limit": 10},
    "Gold": {"price": 99, "limit": 25},
    "Diamond": {"price": 199, "limit": 70},
    "Platinum": {"price": 499, "limit": 9999}
}

# ================= HELPER FUNCTIONS =================
def get_user_plan_limit(user_id):
    cursor.execute("SELECT plan, group_limit FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        return user[0], user[1]
    return "Free", 1

def get_user_links_count(user_id):
    cursor.execute("SELECT COUNT(*) FROM links WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

def is_paid_user(user_id):
    """Check if user has a paid plan (not Free)"""
    cursor.execute("SELECT plan FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user and user[0] != "Free":
        return True
    return False

# ================= ADMIN COMMANDS =================
@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(client, message):
    keyboard = [
        [InlineKeyboardButton("User Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("Pending Orders", callback_data="admin_pending")],
        [InlineKeyboardButton("Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("View Links", callback_data="admin_links")]
    ]
    await message.reply_text("Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= BUY COMMAND =================
@app.on_message(filters.command("buy"))
async def buy_command(client, message):
    keyboard = [[InlineKeyboardButton(f"{name} - ₹{data['price']}", callback_data=f"buy_{name}")]
                for name, data in PLANS.items() if name != "Free"]

    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

    await message.reply_text(
        "**Select a plan:**\n\n"
        "Free - 1 group\n"
        "Silver - ₹49, 10 groups\n"
        "Gold - ₹99, 25 groups\n"
        "Diamond - ₹199, 70 groups\n"
        "Platinum - ₹499, unlimited groups",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= START COMMAND =================
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, plan, group_limit, status) VALUES (?, ?, ?, ?)",
                       (user_id, "Free", 1, "active"))
        conn.commit()

    await message.reply_text(
        "Welcome to Auto Forward Bot!\n\n"
        "Use /buy to purchase a plan\n"
        "Use /menu to see plans and options.\n"
        "Use /myplan to check your current plan.\n"
        "Use /set to configure forwarding"
    )

# ================= MYPLAN COMMAND =================
@app.on_message(filters.command("myplan"))
async def my_plan(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT plan, group_limit FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        links_count = get_user_links_count(user_id)
        await message.reply_text(
            f"**Your Plan Details:**\n\n"
            f"📋 Plan: {user[0]}\n"
            f"👥 Group Limit: {user[1]}\n"
            f"🔗 Current Links: {links_count}/{user[1]}"
        )
    else:
        await message.reply_text("You are not registered. Use /start to register.")

# ================= MENU COMMAND =================
@app.on_message(filters.command("menu"))
async def menu(client, message):
    keyboard = [[InlineKeyboardButton(f"{name} - ₹{data['price']}", callback_data=f"buy_{name}")]
                for name, data in PLANS.items() if name != "Free"]

    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

    await message.reply_text(
        "**Select a plan:**\n\n"
        "Free - 1 group\n"
        "Silver - ₹49, 10 groups\n"
        "Gold - ₹99, 25 groups\n"
        "Diamond - ₹199, 70 groups\n"
        "Platinum - ₹499, unlimited groups",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUY PLAN HANDLER =================
@app.on_callback_query(filters.regex(r"buy_"))
async def buy_plan(client, callback_query):
    plan = callback_query.data.split("_")[1]
    price = PLANS[plan]["price"]

    await callback_query.message.edit_text(
        f"✅ You selected **{plan} Plan**\n\n"
        f"💰 Price: ₹{price}\n\n"
        f"Pay via UPI:\n`{UPI_ID}`\n\n"
        "📸 After payment, send **screenshot here**.\n\n"
        "⚠️ Please note: Payments are manually verified and may take up to 24 hours.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel")]])
    )

    cursor.execute("INSERT INTO orders (user_id, plan, amount, status) VALUES (?, ?, ?, ?)",
                   (callback_query.from_user.id, plan, price, "pending"))
    conn.commit()

# ================= CANCEL HANDLER =================
@app.on_callback_query(filters.regex("cancel"))
async def cancel_handler(client, callback_query):
    await callback_query.message.edit_text("Operation cancelled.")

# ================= PAYMENT SCREENSHOT =================
@app.on_message(filters.photo & ~filters.command(["start", "menu", "plans", "buy", "admin", "myplan"]))
async def payment_screenshot(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (user_id,))
    order = cursor.fetchone()

    if not order:
        await message.reply_text("❌ No pending order found. Please select a plan first using /buy.")
        return

    file_id = message.photo.file_id
    cursor.execute("UPDATE orders SET payment_screenshot=?, status='waiting' WHERE id=?", (file_id, order[0]))
    conn.commit()

    # Send to Admin for approval
    await app.send_photo(
        ADMIN_ID,
        file_id,
        caption=f"**Payment Screenshot**\n\nUser ID: `{user_id}`\nPlan: {order[2]}\nAmount: ₹{order[3]}\nOrder ID: {order[0]}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}_{order[2]}_{order[0]}"),
             InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}_{order[0]}")]
        ])
    )
    await message.reply_text("✅ Screenshot sent for verification. Please wait for approval.")

# ================= ADMIN APPROVAL =================
@app.on_callback_query(filters.regex(r"approve_"))
async def approve_payment(client, callback_query):
    data = callback_query.data.split("_")
    user_id = int(data[1])
    plan = data[2]
    order_id = int(data[3])

    limit = PLANS[plan]["limit"]

    cursor.execute("UPDATE users SET plan=?, group_limit=?, status='active' WHERE user_id=?",
                   (plan, limit, user_id))
    cursor.execute("UPDATE orders SET status='approved' WHERE id=?", (order_id,))
    conn.commit()

    await app.send_message(user_id, f"✅ Your **{plan} Plan** is now activated!\n\nGroup limit: {limit}")
    await callback_query.message.edit_caption(f"✅ Approved user {user_id} for {plan} plan.")

# ================= REJECT PAYMENT =================
@app.on_callback_query(filters.regex(r"reject_"))
async def reject_payment(client, callback_query):
    data = callback_query.data.split("_")
    user_id = int(data[1])
    order_id = int(data[2])

    cursor.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
    conn.commit()

    await app.send_message(user_id, "❌ Your payment was rejected. Please contact admin for assistance.")
    await callback_query.message.edit_caption("❌ Payment rejected.")

# ================= ADMIN STATS =================
@app.on_callback_query(filters.regex("admin_stats"))
async def admin_stats(client, callback_query):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE status='active'")
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='approved'")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='pending' OR status='waiting'")
    pending_orders = cursor.fetchone()[0]

    stats_text = (
        f"**Bot Statistics:**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"✅ Active Users: {active_users}\n"
        f"💰 Total Orders: {total_orders}\n"
        f"⏳ Pending Orders: {pending_orders}"
    )

    await callback_query.message.edit_text(stats_text)

# ================= PENDING ORDERS =================
@app.on_callback_query(filters.regex("admin_pending"))
async def admin_pending(client, callback_query):
    cursor.execute("SELECT * FROM orders WHERE status='waiting'")
    pending_orders = cursor.fetchall()

    if not pending_orders:
        await callback_query.message.edit_text("No pending orders at the moment.")
        return

    orders_text = "**Pending Orders:**\n\n"
    for order in pending_orders:
        orders_text += f"Order ID: {order[0]}\nUser ID: {order[1]}\nPlan: {order[2]}\nAmount: ₹{order[3]}\n\n"

    await callback_query.message.edit_text(orders_text)

# ================= BROADCAST MESSAGE =================
@app.on_callback_query(filters.regex("admin_broadcast"))
async def admin_broadcast(client, callback_query):
    await callback_query.message.edit_text("Please send the broadcast message in the format:\n/broadcast Your message here")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_message(client, message):
    if len(message.text.split(" ", 1)) < 2:
        await message.reply_text("Please provide a message to broadcast.")
        return

    broadcast_text = message.text.split(" ", 1)[1]
    cursor.execute("SELECT user_id FROM users WHERE status='active'")
    users = cursor.fetchall()

    success = 0
    failed = 0

    for user in users:
        try:
            await app.send_message(user[0], f"📢 **Broadcast Message:**\n\n{broadcast_text}")
            success += 1
        except:
            failed += 1

    await message.reply_text(f"Broadcast completed:\n✅ Success: {success}\n❌ Failed: {failed}")

# ================= DEACTIVATE COMMAND =================
@app.on_message(filters.command("deactivate") & filters.user(ADMIN_ID))
async def deactivate_user(client, message):
    try:
        user_id = int(message.text.split(" ")[1])
        cursor.execute("UPDATE users SET status='inactive' WHERE user_id=?", (user_id,))
        conn.commit()
        await message.reply_text(f"✅ User {user_id} deactivated.")
    except:
        await message.reply_text("Usage: /deactivate <user_id>")

# ================= SET SOURCE -> TARGET LINK =================
@app.on_message(filters.command("set"))
async def set_link(client, message):
    user_id = message.from_user.id
    
    # Check if user is admin or paid user
    if user_id != ADMIN_ID:
        if not is_paid_user(user_id):
            await message.reply_text("❌ You need to purchase a plan to use this feature. Use /buy")
            return
        
        plan, limit = get_user_plan_limit(user_id)
        
        # Check if user has reached their link limit
        current_links = get_user_links_count(user_id)
        if current_links >= limit:
            await message.reply_text(f"❌ You have reached your maximum limit of {limit} links for {plan} plan.")
            return

    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            await message.reply_text("Usage: /set <source_chat_id> <target_chat_id>")
            return

        source_chat_id = parts[1]
        target_chat_id = parts[2]

        # Check for duplicates
        cursor.execute("SELECT id FROM links WHERE source_chat_id=? AND target_chat_id=?", (source_chat_id, target_chat_id))
        if cursor.fetchone():
            await message.reply_text(f"❌ Link already exists between `{source_chat_id}` and `{target_chat_id}`")
            return

        # Insert link with user_id
        cursor.execute("INSERT INTO links (user_id, source_chat_id, target_chat_id) VALUES (?, ?, ?)", 
                      (user_id, source_chat_id, target_chat_id))
        conn.commit()
        await message.reply_text(f"✅ Successfully linked source `{source_chat_id}` to target `{target_chat_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# ================= UNSET LINK =================
@app.on_message(filters.command("unset"))
async def unset_link(client, message):
    user_id = message.from_user.id
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            await message.reply_text("Usage: /unset <source_chat_id> <target_chat_id>")
            return

        source_chat_id = parts[1]
        target_chat_id = parts[2]

        # Check if user owns this link or is admin
        if user_id == ADMIN_ID:
            cursor.execute("DELETE FROM links WHERE source_chat_id=? AND target_chat_id=?", (source_chat_id, target_chat_id))
        else:
            cursor.execute("DELETE FROM links WHERE user_id=? AND source_chat_id=? AND target_chat_id=?", 
                          (user_id, source_chat_id, target_chat_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.reply_text(f"✅ Successfully unlinked source `{source_chat_id}` from target `{target_chat_id}`")
        else:
            await message.reply_text(f"❌ No link found between `{source_chat_id}` and `{target_chat_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# ================= VIEW MY LINKS =================
@app.on_message(filters.command("mylinks"))
async def my_links(client, message):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        cursor.execute("SELECT * FROM links")
    else:
        cursor.execute("SELECT * FROM links WHERE user_id=?", (user_id,))
    
    links = cursor.fetchall()

    if not links:
        await message.reply_text("No links found.")
        return

    links_text = "**Your Links:**\n\n"
    for link in links:
        links_text += f"ID: {link[0]}\nSource: `{link[2]}`\nTarget: `{link[3]}`\n\n"

    await message.reply_text(links_text)

# ================= VIEW LINKS (ADMIN) =================
@app.on_callback_query(filters.regex("admin_links"))
async def admin_links(client, callback_query):
    cursor.execute("SELECT * FROM links")
    links = cursor.fetchall()

    if not links:
        await callback_query.message.edit_text("No links found.")
        return

    links_text = "**All Links:**\n\n"
    for link in links:
        links_text += f"ID: {link[0]}\nUser: {link[1]}\nSource: `{link[2]}`\nTarget: `{link[3]}`\n\n"

    await callback_query.message.edit_text(links_text)

# ================= AUTO-FORWARD =================
@app.on_message(filters.group | filters.channel)
async def auto_forward(client, message):
    try:
        # Skip if message is from bot itself
        if message.from_user and message.from_user.id == (await client.get_me()).id:
            return
            
        # Skip service messages (join/leave messages, etc.)
        if not message.text and not message.caption and not message.photo and not message.video and not message.document:
            return

        cursor.execute("SELECT target_chat_id FROM links WHERE source_chat_id=?", (str(message.chat.id),))
        targets = cursor.fetchall()

        if not targets:
            return  # No linked targets

        for target in targets:
            target_id = target[0]
            try:
                # Forward the message with original sender info
                await message.forward(chat_id=int(target_id))
                
            except Exception as e:
                print(f"❌ Failed to forward to {target_id}: {e}")
                
    except Exception as e:
        print(f"❌ Auto-forward error: {e}")

# ================= GET CHAT ID COMMAND =================
@app.on_message(filters.command("id"))
async def get_chat_id(client, message):
    chat_id = message.chat.id
    await message.reply_text(f"This chat's ID is: `{chat_id}`")

# ================= RUN THE BOT =================
if __name__ == "__main__":
    print("✅ Bot is running...")
    app.run()
