import os
import threading
import discord
from discord.ext import commands
from discord import ui
from datetime import datetime

# พยายามโหลด dotenv ถ้ามี (สำหรับการรันแบบ local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ----------------- ตั้งค่า Environment Variables (เหมาะสำหรับ Host) -----------------
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "1556622862083694667"))
PORT = int(os.getenv("PORT", "8080"))
# ---------------------------------------------------------------------------------

# เว็บเซิร์ฟเวอร์ขนาดเล็กสำหรับ Ping ป้องกัน Render เข้าสู่โหมดหลับ (Keep-Alive)
def run_keep_alive():
    try:
        from flask import Flask
        app = Flask(__name__)

        @app.route("/")
        def home():
            return "Bot is alive and running!"

        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        print(f"[KeepAlive] Server could not start: {e}")

class OpenShopModal(ui.Modal, title="✨ ประกาศเปิดร้าน (OPEN)"):
    announcement = ui.TextInput(
        label="📢 ข้อความประกาศ",
        style=discord.TextStyle.paragraph,
        default="ขณะนี้ร้านเปิดให้บริการตามปกติแล้วครับ/ค่ะ สามารถทักสอบถามหรือสั่งซื้อสินค้าได้ทันที!",
        placeholder="พิมพ์ข้อความเปิดร้าน...",
        required=True,
        max_length=1500
    )
    extra_note = ui.TextInput(
        label="📌 หมายเหตุ / โปรโมชันพิเศษ (ถ้ามี)",
        style=discord.TextStyle.short,
        placeholder="เช่น วันนี้เปิดถึง 23:00 น. | ซื้อครบ 200 ลด 10%",
        required=False,
        max_length=200
    )
    banner_url = ui.TextInput(
        label="🖼️ ลิงก์รูปภาพ Banner (ไม่ใส่ก็ได้)",
        style=discord.TextStyle.short,
        placeholder="https://... (URL รูปภาพ)",
        required=False,
        max_length=400
    )

    async def on_submit(self, interaction: discord.Interaction):
        target_channel = interaction.client.get_channel(TARGET_CHANNEL_ID)
        if not target_channel:
            await interaction.response.send_message("❌ ไม่พบห้องปลายทาง กรุณาเช็ก Channel ID", ephemeral=True)
            return

        current_time = datetime.now()
        unix_ts = int(current_time.timestamp())

        # สร้างไอคอน
        icon_url = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else interaction.client.user.display_avatar.url

        embed = discord.Embed(
            title="🟢　ร้านเปิดให้บริการแล้ว • STORE OPEN",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"> **🛍️ ประกาศจากทางร้าน :**\n"
                f"> {self.announcement.value.replace(chr(10), chr(10) + '> ')}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.from_rgb(87, 242, 135), # Discord Emerald Green
            timestamp=current_time
        )

        embed.set_author(
            name=f"{interaction.guild.name if interaction.guild else 'STORE'} • Official Status",
            icon_url=icon_url
        )
        embed.set_thumbnail(url=icon_url)

        if self.extra_note.value:
            embed.add_field(
                name="📌 หมายเหตุเพิ่มเติม",
                value=f"```{self.extra_note.value}```",
                inline=False
            )

        embed.add_field(
            name="💬 ช่องทางติดต่อ",
            value="สามารถเปิดตั๋ว (Ticket) หรือทักข้อความได้เลยครับ",
            inline=True
        )
        embed.add_field(
            name="⏰ อัปเดตเมื่อ",
            value=f"<t:{unix_ts}:T> (<t:{unix_ts}:R>)",
            inline=True
        )

        if self.banner_url.value and self.banner_url.value.startswith(("http://", "https://")):
            embed.set_image(url=self.banner_url.value)

        embed.set_footer(
            text=f"อัปเดตสถานะโดย: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await target_channel.send(embed=embed)
        await interaction.response.send_message("✅ ส่งประกาศเปิดร้านเรียบร้อยแล้ว!", ephemeral=True)


class CloseShopModal(ui.Modal, title="🌙 ประกาศปิดร้าน (CLOSED)"):
    announcement = ui.TextInput(
        label="📢 ข้อความประกาศ",
        style=discord.TextStyle.paragraph,
        default="ขณะนี้ร้านปิดให้บริการแล้ว ขอขอบคุณลูกค้าทุกท่าน สามารถทิ้งข้อความไว้ได้เลยครับ/ค่ะ",
        placeholder="พิมพ์ข้อความปิดร้าน...",
        required=True,
        max_length=1500
    )
    reopen_time = ui.TextInput(
        label="⏰ เวลาเปิดรอบถัดไป (ถ้ามี)",
        style=discord.TextStyle.short,
        placeholder="เช่น พรุ่งนี้ 10:00 น. หรือ แจ้งให้ทราบอีกครั้ง",
        required=False,
        max_length=200
    )
    banner_url = ui.TextInput(
        label="🖼️ ลิงก์รูปภาพ Banner (ไม่ใส่ก็ได้)",
        style=discord.TextStyle.short,
        placeholder="https://... (URL รูปภาพ)",
        required=False,
        max_length=400
    )

    async def on_submit(self, interaction: discord.Interaction):
        target_channel = interaction.client.get_channel(TARGET_CHANNEL_ID)
        if not target_channel:
            await interaction.response.send_message("❌ ไม่พบห้องปลายทาง กรุณาเช็ก Channel ID", ephemeral=True)
            return

        current_time = datetime.now()
        unix_ts = int(current_time.timestamp())

        icon_url = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else interaction.client.user.display_avatar.url

        embed = discord.Embed(
            title="🔴　ร้านปิดให้บริการชั่วคราว • STORE CLOSED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"> **💤 ข้อความถึงลูกค้า :**\n"
                f"> {self.announcement.value.replace(chr(10), chr(10) + '> ')}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.from_rgb(237, 66, 69), # Discord Crimson Red
            timestamp=current_time
        )

        embed.set_author(
            name=f"{interaction.guild.name if interaction.guild else 'STORE'} • Official Status",
            icon_url=icon_url
        )
        embed.set_thumbnail(url=icon_url)

        if self.reopen_time.value:
            embed.add_field(
                name="⏰ กำหนดการเปิดรอบถัดไป",
                value=f"```{self.reopen_time.value}```",
                inline=False
            )

        embed.add_field(
            name="📬 ฝากข้อความ",
            value="สามารถส่งข้อความทิ้งไว้ แอดมินจะตอบกลับทันทีเมื่อเปิดร้าน",
            inline=True
        )
        embed.add_field(
            name="⏰ อัปเดตเมื่อ",
            value=f"<t:{unix_ts}:T> (<t:{unix_ts}:R>)",
            inline=True
        )

        if self.banner_url.value and self.banner_url.value.startswith(("http://", "https://")):
            embed.set_image(url=self.banner_url.value)

        embed.set_footer(
            text=f"อัปเดตสถานะโดย: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await target_channel.send(embed=embed)
        await interaction.response.send_message("✅ ส่งประกาศปิดร้านเรียบร้อยแล้ว!", ephemeral=True)


class ShopControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เปิดร้าน (Open)", style=discord.ButtonStyle.success, emoji="🟢", custom_id="shop_open_btn")
    async def open_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(OpenShopModal())

    @ui.button(label="ปิดร้าน (Close)", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="shop_close_btn")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CloseShopModal())

    @ui.button(label="อัปเดตสต็อก (Stock)", style=discord.ButtonStyle.primary, emoji="📦", custom_id="shop_stock_btn")
    async def stock_button(self, interaction: discord.Interaction, button: ui.Button):
        # แสดงเมนูให้เลือกห้องก่อนส่งประกาศสต็อก (มองเห็นเฉพาะคนที่กด)
        view = StockChannelSelectView()
        await interaction.response.send_message("📍 **กรุณาเลือกห้อง (Channel) ที่ต้องการส่งประกาศอัปเดตสต็อก:**", view=view, ephemeral=True)


class StockModal(ui.Modal, title="📦 อัปเดตสต็อกสินค้า (STOCK)"):
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    server_name = ui.TextInput(
        label="🏙️ ชื่อเมือง / เซิร์ฟเวอร์",
        style=discord.TextStyle.short,
        placeholder="เช่น Bubble Town หรือ Mahanakorn Diwa",
        default="Bubble Town",
        required=True,
        max_length=100
    )
    sold_amount = ui.TextInput(
        label="☘️ ขายออกแล้ว",
        style=discord.TextStyle.short,
        placeholder="เช่น 220.4 M",
        required=True,
        max_length=50
    )
    stock_amount = ui.TextInput(
        label="📦 Stock คงเหลือ",
        style=discord.TextStyle.short,
        placeholder="เช่น 10 M",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        # เส้นตกแต่งบน-ล่าง ตามแบบในรูป
        top_border = "─━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━──━ ★・☆・━"
        bottom_border = "◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★◞◜◞◜◞◜★"

        # ข้อความเนื้อหาหลักตามแบบเป๊ะๆ
        # 🫧 ︳Bubble Town ➡ ︳🎀 ︳.☘️ ˖ ขายออกแล้ว 220.4 M .☘️ ˖ ︳🎀 ︳Stock  10 M ︳
        content_line = (
            f"🫧 ︳**{self.server_name.value.strip()}** ➡ ︳🎀 ︳"
            f".☘️ ˖ **ขายออกแล้ว {self.sold_amount.value.strip()}** .☘️ ˖ ︳"
            f"🎀 ︳**Stock  {self.stock_amount.value.strip()}** ︳"
        )

        full_message = f"{top_border}\n\n{content_line}\n\n{bottom_border}"

        try:
            # แปลง AppCommandChannel เป็น TextChannel / NewsChannel จริงของบอท
            target = interaction.guild.get_channel(self.target_channel.id) if interaction.guild else None
            if not target:
                target = interaction.client.get_channel(self.target_channel.id)
            if not target:
                target = await interaction.client.fetch_channel(self.target_channel.id)

            # ค้นหาข้อความเดิมของบอทในห้องนั้น (ย้อนหลัง 50 ข้อความล่าสุด)
            # วิธีนี้เหมาะกับโฮสต์ Render มากที่สุด เพราะ Render รีสตาร์ทไฟล์ในเครื่องจะหาย
            # แต่ข้อความใน Discord จะอยู่ตลอดไป บอทจะค้นหาแล้วแก้ไข (Edit) ข้อความเดิมได้เสมอ 100%
            existing_message = None
            async for msg in target.history(limit=50):
                if msg.author.id == interaction.client.user.id and "Stock" in msg.content:
                    existing_message = msg
                    break

            if existing_message:
                # แก้ไขข้อความเดิม
                await existing_message.edit(content=full_message)
                action_text = "แก้ไขข้อความเดิมเรียบร้อยแล้ว"
            else:
                # ถ้ายังไม่เคยมีข้อความของบอทในห้องนี้ ให้ส่งใหม่เป็นข้อความแรก
                await target.send(full_message)
                action_text = "ส่งประกาศสต็อกใหม่เรียบร้อยแล้ว"

            await interaction.response.send_message(
                f"✅ {action_text} ในห้อง {target.mention}!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ บอทไม่มีสิทธิ์ส่งหรือแก้ไขข้อความในห้อง {self.target_channel.mention} (กรุณาเช็กสิทธิ์ Send Messages / View History ของบอท)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ เกิดข้อผิดพลาด: {e}",
                ephemeral=True
            )


class ChannelSelect(ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="🔎 เลือกห้องที่ต้องการส่งประกาศสต็อก...",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            custom_id="stock_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected_channel = self.values[0]
        # เปิด Modal สำหรับกรอกรายละเอียดสต็อก
        await interaction.response.send_modal(StockModal(target_channel=selected_channel))


class StockChannelSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ChannelSelect())


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # ลงทะเบียน View ทั้งหมดเป็น Persistent View ทำงานได้ตลอดแม้รีสตาร์ทบอท
        self.add_view(ShopControlView())
        self.add_view(StockChannelSelectView())

    async def on_ready(self):
        try:
            print(f"[ONLINE] Logged in as: {self.user} (ID: {self.user.id})")
        except Exception:
            pass


bot = MyBot()

@bot.command(name="setup_shop")
@commands.has_permissions(administrator=True)
async def setup_shop(ctx):
    icon_url = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else bot.user.display_avatar.url
    embed = discord.Embed(
        title="⚙️ แผงควบคุมสถานะร้านค้า (Store Control Panel)",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ใช้สำหรับจัดการสถานะและสต็อกสินค้าของร้านค้าแบบเรียลไทม์\n"
            "เมื่อกดปุ่มจะมีหน้าต่างขึ้นมาให้ระบุรายละเอียดเพิ่มเติม\n\n"
            "🟢 **เปิดร้าน (Open)** : แจ้งเปิดร้านค้า พร้อมรับออเดอร์\n"
            "🔴 **ปิดร้าน (Close)** : แจ้งปิดร้านชั่วคราว / ระบุเวลาเปิดรอบถัดไป\n"
            "📦 **อัปเดตสต็อก (Stock)** : เลือกห้องแล้วแจ้งจำนวนสต็อกสินค้าล่าสุด\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(88, 101, 242) # Blurple
    )
    embed.set_author(name=f"{ctx.guild.name} Staff Panel", icon_url=icon_url)
    embed.set_thumbnail(url=icon_url)
    embed.set_footer(text="ระบบจัดการสถานะร้านค้าอัตโนมัติ")
    await ctx.send(embed=embed, view=ShopControlView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass

# รัน Keep-Alive Web Server สำหรับ Render
if os.getenv("RENDER") or os.getenv("PORT"):
    threading.Thread(target=run_keep_alive, daemon=True).start()

bot.run(TOKEN)