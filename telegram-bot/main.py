from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,  # <- This line fixes your error
)
import json
import os
from datetime import datetime
from io import BytesIO

BOT_TOKEN = '7934454241:AAEqtke_iXrU5N-AveoOl0NlK0YIQJgbrz8'
ADMIN_ID = 7290606783

# Initialize data storage
paired_numbers = {}
banned_users = set()
feedback_data = []
vip_users = set()  # VIP users set
usage_stats = {    # Usage statistics
    'pair_attempts': 0,
    'commands_used': {},
    'daily_active': {}
}

# Data file paths
DATA_FILE = "bot_data.json"
BACKUP_FOLDER = "backups"

# Ensure backup folder exists
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# Load data from file
def load_data():
    global paired_numbers, banned_users, feedback_data, vip_users, usage_stats
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            paired_numbers = data.get('paired_numbers', {})
            banned_users = set(data.get('banned_users', []))
            feedback_data = data.get('feedback_data', [])
            vip_users = set(data.get('vip_users', []))
            usage_stats = data.get('usage_stats', {
                'pair_attempts': 0,
                'commands_used': {},
                'daily_active': {}
            })
    except (FileNotFoundError, json.JSONDecodeError):
        save_data()  # Initialize with empty data

# Save data to file
def save_data():
    data = {
        'paired_numbers': paired_numbers,
        'banned_users': list(banned_users),
        'feedback_data': feedback_data,
        'vip_users': list(vip_users),
        'usage_stats': usage_stats
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Update usage statistics
def update_stats(command):
    today = datetime.now().strftime("%Y-%m-%d")
    usage_stats['commands_used'][command] = usage_stats['commands_used'].get(command, 0) + 1
    usage_stats['daily_active'][today] = usage_stats['daily_active'].get(today, 0) + 1
    save_data()

# Check if user is admin or VIP
def is_privileged(user_id):
    return user_id == ADMIN_ID or user_id in vip_users

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_stats('start')

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot!")
        return

    is_vip = "🌟 VIP User" if user_id in vip_users else ""

    base_commands = (
        f"✨ *Welcome to Anonymous Boy Bot* ✨ {is_vip}\n\n"
        "🔹 *Main Commands:*\n"
        "📱 /pair <number> - Pair your number\n"
        "❌ /delpair <number> - Remove pairing\n"
        "💌 /feedback <message> - Send feedback\n"
        "ℹ️ /help - Show help\n"
    )
    admin_commands = (
        "\n👑 *Admin/VIP Commands:*\n"
        "📊 /adminpanel - Admin dashboard\n"
        "📈 /stats - Show statistics\n"
        "📢 /broadcast <id> <msg> - Broadcast message\n"
        "👤 /userinfo <id> - Get user details\n"
        "⛔ /ban <id> - Ban user\n"
        "✅ /unban <id> - Unban user\n"
        "💾 /backup - Create backup\n"
        "🔄 /restore <file> - Restore backup\n"
        "📋 /listpair - List all pairs"
    )

    full_msg = base_commands
    if is_privileged(user_id):
        full_msg += admin_commands

    try:
        image_path = "/storage/emulated/0/Pictures/file_000000009edc61f881ef305fc245af29.png"
        with open(image_path, "rb") as img:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img,
                caption=full_msg,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        await update.message.reply_text(f"📛 Error: {e}\n\n{full_msg}")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_stats('help')

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned from using this bot!")
        return

    help_text = (
        "📚 *Bot Help Guide* 📚\n\n"
        "🔹 *Number Pairing:*\n"
        "📱 /pair <number> - Link your number\n"
        "   Example: `/pair 911234567890`\n\n"
        "❌ /delpair <number> - Unlink your number\n"
        "   Example: `/delpair 911234567890`\n\n"
        "💌 /feedback <message> - Send feedback\n"
        "   Example: `/feedback Great bot!`\n\n"
        "ℹ️ /help - Show this message"
    )

    if is_privileged(user_id):
        help_text += (
            "\n\n👑 *Admin/VIP Commands:*\n"
            "📊 /adminpanel - View stats\n"
            "📈 /stats - Show statistics\n"
            "👤 /userinfo <id> - User details\n"
            "⛔ /ban <id> - Ban user\n"
            "✅ /unban <id> - Unban user\n"
            "💾 /backup - Create backup\n"
            "🔄 /restore - Restore backup"
        )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# /pair command with VIP check
async def pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_stats('pair')

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned!")
        return

    # Check if user is VIP or has less than 3 numbers paired
    user_numbers = [num for num, uid in paired_numbers.items() if uid == user_id]
    if len(user_numbers) >= 3 and user_id not in vip_users and user_id != ADMIN_ID:
        await update.message.reply_text(
            "🔒 You've reached the pairing limit (3 numbers).\n"
            "🌟 Become a VIP user to pair unlimited numbers!\n"
            "Contact admin for VIP access."
        )
        return

    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: `/pair 91xxxxxxxxxx`", parse_mode=ParseMode.MARKDOWN)
        return

    number = context.args[0]
    processing_msg = await update.message.reply_text("⏳ Please wait while we process your pairing request. This may take a few moments...")

    if number.startswith('+'):
        await processing_msg.edit_text(
            "❌ Invalid format!\n\n"
            "📱 Please use:\n"
            "`91XXXXXXXXXX` (12 digits)\n\n"
            "🚫 No symbols or country codes",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(number) != 12 or not number.isdigit():
        await processing_msg.edit_text(
            "❌ Invalid number!\n\n"
            "🔢 Must be 12 digits\n"
            "📱 Example: `91XXXXXXXXXX`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    paired_numbers[number] = user_id
    save_data()
    await processing_msg.edit_text(f"✅ Number `{number}` paired successfully!", parse_mode=ParseMode.MARKDOWN)

    # Notify admin
    user = update.effective_user
    admin_msg = (
        f"📱 *New Pairing Alert* 📱\n\n"
        f"👤 User: {user.full_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📞 Number: `{number}`\n"
        f"🌟 VIP: {'Yes' if user_id in vip_users else 'No'}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode=ParseMode.MARKDOWN)

# /delpair command
async def delpair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_stats('delpair')

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned!")
        return

    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: `/delpair 91xxxxxxxxxx`", parse_mode=ParseMode.MARKDOWN)
        return

    number = context.args[0]

    if number not in paired_numbers:
        await update.message.reply_text("❌ This number is not paired!")
        return

    if paired_numbers[number] != user_id and not is_privileged(user_id):
        await update.message.reply_text("🚫 You can only delete your own paired numbers!")
        return

    del paired_numbers[number]
    save_data()
    await update.message.reply_text(f"✅ Number `{number}` unpaired successfully!", parse_mode=ParseMode.MARKDOWN)

# /feedback command
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_stats('feedback')

    if user_id in banned_users:
        await update.message.reply_text("🚫 You are banned!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/feedback <your message>`", parse_mode=ParseMode.MARKDOWN)
        return

    feedback_text = " ".join(context.args)
    feedback_data.append({
        'user_id': user_id,
        'text': feedback_text,
        'timestamp': datetime.now().isoformat()
    })
    save_data()

    # Notify admin
    user = update.effective_user
    admin_msg = (
        f"💌 *New Feedback* 💌\n\n"
        f"👤 User: {user.full_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🌟 VIP: {'Yes' if user_id in vip_users else 'No'}\n\n"
        f"📝 Feedback:\n{feedback_text}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode=ParseMode.MARKDOWN)

    await update.message.reply_text("✅ Thank you for your feedback!")

# /vip command (Admin only)
async def vip_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('vip')

    if not context.args:
        await update.message.reply_text(
            "🌟 *VIP Management* (Admin Only)\n\n"
            "Usage:\n"
            "• /vip add <user_id> - Add VIP\n"
            "• /vip remove <user_id> - Remove VIP\n"
            "• /vip list - Show all VIPs",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    action = context.args[0].lower()

    if action == 'add' and len(context.args) == 2:
        try:
            user_id = int(context.args[1])
            vip_users.add(user_id)
            save_data()
            await update.message.reply_text(f"🌟 User `{user_id}` added to VIP list!", parse_mode=ParseMode.MARKDOWN)

            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎉 Congratulations! You've been granted VIP status in Anonymous Boy Bot!\n\n"
                         "You now have access to:\n"
                         "• Unlimited number pairing\n"
                         "• Priority support\n"
                         "• Exclusive admin commands"
                )
            except:
                pass

        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")

    elif action == 'remove' and len(context.args) == 2:
        try:
            user_id = int(context.args[1])
            if user_id in vip_users:
                vip_users.remove(user_id)
                save_data()
                await update.message.reply_text(f"❌ User `{user_id}` removed from VIP list!", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(f"ℹ️ User `{user_id}` is not a VIP.", parse_mode=ParseMode.MARKDOWN)
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")

    elif action == 'list':
        if not vip_users:
            await update.message.reply_text("ℹ️ No VIP users yet.")
            return

        vip_list = "🌟 *VIP Users List* 🌟\n\n" + "\n".join(
            f"• `{user_id}`" for user_id in vip_users
        )
        await update.message.reply_text(vip_list, parse_mode=ParseMode.MARKDOWN)

    else:
        await update.message.reply_text("❌ Invalid command format!")

# /userinfo command
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('userinfo')

    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Usage: /userinfo <user_id>")
        return

    try:
        target_id = int(context.args[0])
        try:
            user = await context.bot.get_chat(target_id)
            is_banned = target_id in banned_users
            is_vip = target_id in vip_users
            user_numbers = [num for num, uid in paired_numbers.items() if uid == target_id]

            response = (
                f"📝 *User Report* 📝\n\n"
                f"👤 Name: {user.full_name}\n"
                f"🆔 ID: `{target_id}`\n"
                f"🔗 @{user.username if user.username else 'N/A'}\n"
                f"🚫 Banned: {'Yes' if is_banned else 'No'}\n"
                f"🌟 VIP: {'Yes' if is_vip else 'No'}\n"
                f"📱 Paired Numbers: {len(user_numbers)}"
            )

            if user_numbers:
                response += "\n\n" + "\n".join(f"• `{num}`" for num in user_numbers[:5])
                if len(user_numbers) > 5:
                    response += f"\n...and {len(user_numbers)-5} more"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

# /adminpanel command
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('adminpanel')

    stats = (
        "👑 *Admin/VIP Dashboard* 👑\n\n"
        f"📊 Stats:\n"
        f"• 📱 Paired numbers: {len(paired_numbers)}\n"
        f"• ⛔ Banned users: {len(banned_users)}\n"
        f"• 💌 Feedback entries: {len(feedback_data)}\n"
        f"• 🌟 VIP users: {len(vip_users)}\n\n"
        "🔧 Available Commands:\n"
        "📈 /stats - Show statistics\n"
        "📋 /listpair - Show all pairs\n"
        "👤 /userinfo <id> - User details\n"
        "⛔ /ban <id> - Ban user\n"
        "✅ /unban <id> - Unban user\n"
        "💾 /backup - Create backup\n"
        "🔄 /restore - Restore backup"
    )

    if user_id == ADMIN_ID:
        stats += "\n🌟 /vip - Manage VIP users (Admin only)"

    await update.message.reply_text(stats, parse_mode=ParseMode.MARKDOWN)

# /stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('stats')

    # Count total unique users
    try:
        total_users = len(set(paired_numbers.values()))
    except Exception as e:
        print(f"Error counting users: {e}")
        total_users = "N/A"

    # Count total paired numbers
    total_pairs = len(paired_numbers)

    # Count banned users
    total_banned = len(banned_users)

    # Count feedback entries
    total_feedback = len(feedback_data)

    # Count VIP users
    total_vip = len(vip_users)

    # Prepare statistics message
    stats_message = (
        "📊 *Detailed Statistics* 📊\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"📱 Total Paired Numbers: `{total_pairs}`\n"
        f"⛔ Banned Users: `{total_banned}`\n"
        f"💌 Feedback Entries: `{total_feedback}`\n"
        f"🌟 VIP Users: `{total_vip}`\n\n"
        "_Updated in real-time_"
    )

    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

# /listpair command
async def listpair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('listpair')

    if not paired_numbers:
        await update.message.reply_text("ℹ️ No numbers paired yet.")
        return

    # Create a list of all pairs
    pairs_list = []
    for number, uid in paired_numbers.items():
        try:
            user = await context.bot.get_chat(uid)
            name = user.full_name
            username = f"@{user.username}" if user.username else "No username"
        except:
            name = "Unknown"
            username = "Unknown"

        pairs_list.append(f"• `{number}` → {name} ({username}) [ID: `{uid}`]")

    # Split into chunks of 50 to avoid message length limits
    chunk_size = 50
    for i in range(0, len(pairs_list), chunk_size):
        chunk = pairs_list[i:i + chunk_size]
        message = "📋 *Paired Numbers List* 📋\n\n" + "\n".join(chunk)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# /ban command
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('ban')

    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Usage: /ban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id == ADMIN_ID:
            await update.message.reply_text("🤨 You can't ban the admin!")
            return

        if target_id in vip_users and user_id != ADMIN_ID:
            await update.message.reply_text("🚫 Only admin can ban VIP users!")
            return

        banned_users.add(target_id)
        save_data()

        # Remove all pairs for banned user
        global paired_numbers
        paired_numbers = {num: uid for num, uid in paired_numbers.items() if uid != target_id}
        save_data()

        await update.message.reply_text(f"⛔ User `{target_id}` has been banned and all their pairings removed!", parse_mode=ParseMode.MARKDOWN)

        # Notify the banned user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="🚫 You have been banned from using Anonymous Boy Bot!\n\n"
                     "All your paired numbers have been removed."
            )
        except:
            pass

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

# /unban command
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('unban')

    if len(context.args) != 1:
        await update.message.reply_text("ℹ️ Usage: /unban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id in banned_users:
            banned_users.remove(target_id)
            save_data()
            await update.message.reply_text(f"✅ User `{target_id}` has been unbanned!", parse_mode=ParseMode.MARKDOWN)

            # Notify the unbanned user
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text="🎉 You have been unbanned from Anonymous Boy Bot!\n\n"
                         "You can now use the bot again."
                )
            except:
                pass
        else:
            await update.message.reply_text(f"ℹ️ User `{target_id}` is not banned.", parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

# /backup command
async def backup_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('backup')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.json")

    try:
        with open(DATA_FILE, 'r') as src, open(backup_file, 'w') as dst:
            dst.write(src.read())
        await update.message.reply_text(f"✅ Backup created successfully!\n\nFile: `{backup_file}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Backup failed: {e}")

# /restore command
async def restore_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Only admin can restore backups!")
        return

    update_stats('restore')

    if not context.args:
        # List available backups
        try:
            backups = sorted([f for f in os.listdir(BACKUP_FOLDER) if f.startswith('backup_') and f.endswith('.json')])
            if not backups:
                await update.message.reply_text("ℹ️ No backup files found.")
                return

            await update.message.reply_text(
                "📂 Available backups:\n\n" +
                "\n".join(f"• `{f}`" for f in backups[-10:]) +  # Show last 10 backups
                "\n\nUsage: /restore <filename>",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error listing backups: {e}")
        return

    backup_file = os.path.join(BACKUP_FOLDER, context.args[0])
    if not os.path.exists(backup_file):
        await update.message.reply_text("❌ Backup file not found!")
        return

    try:
        # Load the backup first to validate it
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        # If validation passes, proceed with restore
        with open(backup_file, 'r') as src, open(DATA_FILE, 'w') as dst:
            dst.write(src.read())

        # Reload the data
        load_data()

        await update.message.reply_text(f"✅ Data restored successfully from `{backup_file}`!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Restore failed: {e}")

# /broadcast command
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_privileged(user_id):
        await update.message.reply_text("🚫 Unauthorized!")
        return

    update_stats('broadcast')

    if len(context.args) < 2:
        await update.message.reply_text("ℹ️ Usage: /broadcast <user_id/all> <message>")
        return

    target = context.args[0]
    message = " ".join(context.args[1:])

    if target.lower() == 'all':
        # Send to all users who have paired numbers
        users_to_notify = set(paired_numbers.values())
        total = len(users_to_notify)
        success = 0
        failed = 0

        processing_msg = await update.message.reply_text(f"📢 Broadcasting to {total} users...")

        for uid in users_to_notify:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                success += 1
            except:
                failed += 1

        await processing_msg.edit_text(
            f"📢 Broadcast completed!\n\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}"
        )
    else:
        # Send to specific user
        try:
            target_id = int(target)
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                await update.message.reply_text(f"✅ Message sent to user `{target_id}`!", parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send message: {e}")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")

# Message handler for forwarding
async def forward_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        return

    # Check if message is from a paired number
    for number, uid in paired_numbers.items():
        if uid == user_id and str(number) in update.message.text:
            # Forward to admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📩 *New Message Alert* 📩\n\n"
                     f"👤 From: {update.effective_user.full_name}\n"
                     f"🆔 ID: `{user_id}`\n"
                     f"📞 Number: `{number}`\n\n"
                     f"📝 Message:\n{update.message.text}",
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text("✅ Your message has been forwarded to admin!")
            return

# Main bot setup
if __name__ == "__main__":
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    commands = [
        ('start', start),
        ('help', help_command),
        ('pair', pair),
        ('delpair', delpair),
        ('delsession', delpair),
        ('feedback', feedback),
        ('adminpanel', admin_panel),
        ('vip', vip_management),
        ('stats', stats),
        ('listpair', listpair),
        ('userinfo', user_info),
        ('ban', ban_user),
        ('unban', unban_user),
        ('backup', backup_data),
        ('restore', restore_data),
        ('broadcast', broadcast)
    ]

    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), forward_user_message))

    print("🤖 Bot is running with VIP features...")
    app.run_polling()
