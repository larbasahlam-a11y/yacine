import logging
import asyncio
import requests
import json
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ====== الإعدادات ======
TOKEN = "8054736760:AAE7TlEcsO4R25LI9e2nAzUr8o9VEzqt84E"  # ضع توكن البوت هنا
ADMIN_ID = 6936293942  # ضع معرفك (ID) هنا

# التوكن الخاص بتطبيق TikSpark
TIKSPARK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2YTRkMWZiOGMyY2ZkMjQxYTFlYmY4ODAiLCJyb2xlIjoiQVVUSCIsInRva2VuVmVyc2lvbiI6MSwiaWF0IjoxNzgzNDkzMDk1LCJleHAiOjE3ODQ3ODkwOTV9.h8_UIDCEIm9TECI_6zZ2qx5tJY2G-fvG1VXLrnUVqZM"

# ====== إعدادات السجلات ======
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== كلاس البوت ======
class TikSparkBot:
    def __init__(self):
        self.base_url = "https://api.tikspark.xyz/graphql"
        self.token = TIKSPARK_TOKEN
        self.device_info = '{"d":"62633330356361393666343862636466","n":"4954454c206974656c20413637314c43","o":"14","t":"d","v":"2.2.0","s":"0,0"}'
        self.session = requests.Session()
        self.total_score = 0
        self.success_count = 0
        self.fail_count = 0
        self.running = False

    def generate_headers(self, operation_name, operation_id):
        timestamp = str(int(time.time() * 1000))
        nonce = ''.join(random.choices('0123456789abcdef', k=16))
        csrf = f"{timestamp}:{''.join(random.choices('0123456789abcdef', k=64))}"
        return {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "multipart/mixed; deferSpec=20220824, application/json",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/json",
            'x-apollo-operation-id': operation_id,
            'x-apollo-operation-name': operation_name,
            'x-language': "ar",
            'x-app-name': "com.dev.vidspark",
            'token': self.token,
            'x-csrf-token': csrf,
            'x-device-info': self.device_info,
            'x-app-sig': ''.join(random.choices('0123456789abcdef', k=64)),
            'x-app-ts': timestamp,
            'x-app-nonce': nonce
        }

    def fetch_score(self):
        payload = {
            "operationName": "FetchScore",
            "variables": {},
            "query": "query FetchScore { fetchScore }"
        }
        headers = self.generate_headers("FetchScore", "88d30eeca55c0538539ad8217dfefd52b2f47015200cdbb7cb6ea5a765381d69")
        try:
            response = self.session.post(self.base_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('fetchScore', 0)
            return 0
        except:
            return 0

    def fetch_orders(self, page=1):
        payload = {
            "operationName": "FetchOrders",
            "variables": {"page": page},
            "query": "query FetchOrders($page: Int!) { getOrders(page: $page) { _id type videoLink tiktokerUsername avatar score priority } }"
        }
        headers = self.generate_headers("FetchOrders", "c2ca4b87e63f30f2cca10e5867d17ea0f1712e96e716a60513f68758b2256185")
        try:
            response = self.session.post(self.base_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                orders = data.get('data', {}).get('getOrders', [])
                return [o for o in orders if o.get('type') != 'followers']
            return []
        except:
            return []

    def action_order(self, order_id):
        attempts = random.randint(50, 100)
        initial_number = random.uniform(50000, 150000)
        time_spent = random.uniform(600000, 1800000)

        payload = {
            "operationName": "ActionOrder",
            "variables": {
                "orderId": order_id,
                "validationData": {
                    "attempts": attempts,
                    "initialNumber": initial_number,
                    "timeSpent": time_spent
                }
            },
            "query": """
            mutation ActionOrder($orderId: ID!, $validationData: ValidationDataInput!) {
                actionOrder(orderId: $orderId, validationData: $validationData) {
                    score
                    taskProgress {
                        count
                        startTime
                        taskProgressLimit
                    }
                }
            }
            """
        }
        headers = self.generate_headers("ActionOrder", "ddfbb49865193fd38840a34b92139f1759a71331e374bb1254f8e2352630e8f2")

        try:
            response = self.session.post(self.base_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                action_data = data.get('data', {}).get('actionOrder')
                if action_data and isinstance(action_data, dict):
                    score = action_data.get('score', 0)
                    if score > 0:
                        self.success_count += 1
                        self.total_score += score
                        return score
            return 0
        except:
            return 0

    def run_cycle(self, max_orders=5):
        """تشغيل دورة واحدة لجلب النقاط"""
        if self.running:
            return {"status": "already_running", "score": self.total_score}

        self.running = True
        self.success_count = 0
        self.fail_count = 0
        
        try:
            # جلب النقاط الحالية
            start_score = self.fetch_score()
            
            # جلب الطلبات من عدة صفحات
            all_orders = []
            for page in range(1, 6):
                orders = self.fetch_orders(page)
                if orders:
                    all_orders.extend(orders)
                time.sleep(0.2)
            
            if not all_orders:
                self.running = False
                return {"status": "no_orders", "score": start_score}
            
            # اختيار عشوائي
            selected = random.sample(all_orders, min(max_orders, len(all_orders)))
            gained = 0
            
            for order in selected:
                score = self.action_order(order['_id'])
                gained += score
                time.sleep(0.3)
            
            # جلب النقاط الجديدة
            end_score = self.fetch_score()
            
            self.running = False
            return {
                "status": "success",
                "start_score": start_score,
                "end_score": end_score,
                "gained": gained,
                "processed": len(selected),
                "success_count": self.success_count,
                "fail_count": self.fail_count
            }
        except Exception as e:
            self.running = False
            return {"status": "error", "error": str(e)}

# ====== البوت تليجرام ======
bot_instance = TikSparkBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🔥 **مــــرحبا  بـــــك  يـــا « @{user.username} »** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"       #TIKSPARK_POINTS_BOT 💰\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡️ **بوت جلب النقاط من تطبيق TikSpark**\n"
        f"📌 **الأوامر المتاحة:**\n"
        f"  /start → عرض هذه الرسالة\n"
        f"  /points → جلب نقاطك الحالية\n"
        f"  /collect → تشغيل دورة لجلب النقاط\n"
        f"  /status → حالة البوت\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"[⌤] Dev by: @yacine_X6 👑\n"
        f"[⌤] Power: DARK ALGIERS CYBER CORE 😈",
        parse_mode="Markdown"
    )

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري جلب النقاط...")
    score = bot_instance.fetch_score()
    if score is not None:
        await update.message.reply_text(f"💰 **نقاطك الحالية: {score} نقطة**", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ فشل جلب النقاط")

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمطور فقط!")
        return

    if bot_instance.running:
        await update.message.reply_text("⚠️ البوت يعمل حالياً، انتظر حتى ينتهي")
        return

    msg = await update.message.reply_text("⏳ جاري جلب النقاط...")
    
    result = bot_instance.run_cycle(max_orders=5)
    
    if result["status"] == "success":
        text = (
            f"✅ **تم جلب النقاط بنجاح!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **النقاط السابقة:** {result['start_score']}\n"
            f"💰 **النقاط الحالية:** {result['end_score']}\n"
            f"📈 **زيادة:** +{result['gained']} نقطة\n"
            f"📊 **تم معالجة:** {result['processed']} طلب\n"
            f"✅ **نجاح:** {result['success_count']}\n"
            f"❌ **فشل:** {result['fail_count']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"[⌤] Dev by: @yacine_X6 👑"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    elif result["status"] == "no_orders":
        await msg.edit_text(f"❌ لا توجد طلبات متاحة حالياً\n💰 نقاطك الحالية: {result['score']}")
    elif result["status"] == "already_running":
        await msg.edit_text("⚠️ البوت يعمل حالياً، انتظر حتى ينتهي")
    else:
        await msg.edit_text(f"❌ خطأ: {result.get('error', 'غير معروف')}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = bot_instance.fetch_score()
    status = "🟢 يعمل" if bot_instance.running else "🔴 متوقف"
    text = (
        f"📊 **حالة البوت**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡️ **الحالة:** {status}\n"
        f"💰 **النقاط الحالية:** {score}\n"
        f"✅ **إجمالي النجاح:** {bot_instance.success_count}\n"
        f"❌ **إجمالي الفشل:** {bot_instance.fail_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"[⌤] Dev by: @yacine_X6 👑"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ أمر غير معروف. استخدم /start")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("collect", collect))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(collect, pattern="collect"))
    app.add_handler(CallbackQueryHandler(points, pattern="points"))
    app.add_handler(MessageHandler(None, handle_message))
    
    print("🔥 بوت تيك سبارك شغال...")
    print(f"👑 المطور: @yacine_X6")
    app.run_polling()

if __name__ == "__main__":
    main()
