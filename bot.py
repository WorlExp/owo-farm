import discord
from discord.ext import commands
import discord_self
import re
import asyncio
import random

# -------------------------------------------------------------------
# AYARLAR
# -------------------------------------------------------------------
OWO_BOT_ID = 408785106942164992  # OwO botunun Discord ID'si
BASLANGIC_COOLDOWN = 15          # İlk bekleme süresi (saniye)
COOLDOWN_ARTIS = 1               # Her komuttan sonra bekleme süresine eklenecek miktar
KOMUTLAR = ["owo hunt", "owo battle", "owo pray"]  # Kullanılacak OwO komutları

# -------------------------------------------------------------------
# ANA BOT (Slash komutları için)
# -------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Aktif self-bot istemcilerini saklamak için sözlük
# { token: {"client": client, "task": task} }
aktif_hesaplar = {}

@bot.event
async def on_ready():
    print(f"[ANA BOT] Giriş yapıldı: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"[ANA BOT] {len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"[ANA BOT] Slash senkronizasyon hatası: {e}")

@bot.tree.command(name="add", description="OwO botunu kasmak için bir hesap (token) ekler.")
async def add(interaction: discord.Interaction, token: str):
    """
    /add (token) komutu.
    Token ile bir self-bot başlatır ve komutun yazıldığı kanalda OwO kasmaya başlar.
    """
    await interaction.response.defer(ephemeral=True)

    kanal = interaction.channel
    if kanal is None:
        await interaction.followup.send("❌ Bu komut sadece bir kanalda kullanılabilir.")
        return

    # Aynı token zaten ekli mi?
    if token in aktif_hesaplar:
        await interaction.followup.send("⚠️ Bu token zaten aktif. Önce /remove ile kaldırın.")
        return

    # Self-bot istemcisini oluştur
    client = discord_self.Client()

    @client.event
    async def on_ready():
        print(f"[SELF-BOT] Giriş yapıldı: {client.user}")
        # OwO kasma görevini başlat
        task = client.loop.create_task(owo_kas(client, kanal))
        aktif_hesaplar[token]["task"] = task

    @client.event
    async def on_message(message: discord.Message):
        # Sadece OwO botunun mesajlarını incele
        if message.author.id != OWO_BOT_ID:
            return
        await owo_mesaj_analiz(message, client)

    # İstemciyi başlatmayı dene
    try:
        await client.start(token)
    except discord.LoginFailure:
        await interaction.followup.send("❌ Geçersiz token. Lütfen kontrol edin.")
        return
    except Exception as e:
        await interaction.followup.send(f"❌ Giriş hatası: {e}")
        return

    # Başarılıysa kaydet
    aktif_hesaplar[token] = {"client": client, "task": None, "kanal": kanal.id}
    await interaction.followup.send(
        f"✅ Hesap eklendi ve OwO kasma başlatıldı.\n"
        f"**Kullanıcı:** {client.user}\n"
        f"**Kanal:** {kanal.mention}\n"
        f"**Başlangıç Cooldown:** {BASLANGIC_COOLDOWN}s (her komutta +{COOLDOWN_ARTIS}s)"
    )

@bot.tree.command(name="remove", description="Ekli bir hesabı durdurur ve kaldırır.")
async def remove(interaction: discord.Interaction, token: str):
    """Belirtilen token'a ait self-bot'u durdurur."""
    await interaction.response.defer(ephemeral=True)

    if token not in aktif_hesaplar:
        await interaction.followup.send("❌ Bu token aktif değil.")
        return

    data = aktif_hesaplar.pop(token)
    task = data.get("task")
    if task:
        task.cancel()
    client = data["client"]
    await client.close()
    await interaction.followup.send("✅ Hesap durduruldu ve kaldırıldı.")

@bot.tree.command(name="list", description="Aktif hesapları listeler.")
async def list_accounts(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not aktif_hesaplar:
        await interaction.followup.send("📭 Aktif hesap yok.")
        return

    mesaj = "**Aktif Hesaplar:**\n"
    for token, data in aktif_hesaplar.items():
        client = data["client"]
        kanal_id = data.get("kanal", "?")
        mesaj += f"- `{client.user}` | Kanal: <#{kanal_id}>\n"
    await interaction.followup.send(mesaj)

# -------------------------------------------------------------------
# OWO MESAJ ANALİZİ (Mute ve Cooldown tespiti)
# -------------------------------------------------------------------
async def owo_mesaj_analiz(message: discord.Message, client: discord_self.Client):
    """
    OwO botunun mesajlarını analiz eder:
    - Cooldown süresini okur (bilgi amaçlı)
    - Mute mesajı gelirse mute süresini kaydeder ve beklemeye alır
    """
    içerik = message.content.lower()
    now = asyncio.get_event_loop().time()

    # Cooldown mesajı örneği: "... again in 15 seconds"
    cooldown_match = re.search(r"in (\d+)\s*seconds", içerik)
    if cooldown_match:
        ow_süresi = int(cooldown_match.group(1))
        # OwO'nun verdiği süreyi logla (kendi cooldown'umuzu ayrıca yönetiyoruz)
        print(f"[OWO] Cooldown mesajı: {ow_süresi}s")

    # Mute mesajı örnekleri:
    # "You are muted for 5 minutes"
    # "You have been muted"
    if "muted" in içerik:
        mute_match = re.search(r"muted for (\d+)\s*(minute|second|hour|min|sec|hour)", içerik)
        if mute_match:
            miktar = int(mute_match.group(1))
            birim = mute_match.group(2)
            if "min" in birim:
                saniye = miktar * 60
            elif "hour" in birim:
                saniye = miktar * 3600
            else:
                saniye = miktar
            client.mute_until = now + saniye
            print(f"[OWO] Mute algılandı! {saniye}s boyunca beklenecek.")
        else:
            # Süre belirtilmemişse varsayılan 5 dakika bekle
            client.mute_until = now + 300
            print("[OWO] Mute algılandı (süre belirsiz). 300s beklenecek.")

    # "You can't use this command right now" gibi mesajlar da olabilir
    if "you can't use" in içerik or "slow down" in içerik:
        # Kısa bir süre bekle
        client.mute_until = now + 5
        print("[OWO] Geçici kısıtlama algılandı. 5s beklenecek.")

# -------------------------------------------------------------------
# OWO KASMA DÖNGÜSÜ
# -------------------------------------------------------------------
async def owo_kas(client: discord_self.Client, kanal: discord.TextChannel):
    """
    Ana döngü:
    1. Mute kontrolü yapar.
    2. Kendi cooldown süresini bekler.
    3. Rastgele bir OwO komutu gönderir.
    4. Cooldown süresini 1 artırır.
    """
    await client.wait_until_ready()

    # Başlangıç değerleri
    client.cooldown = BASLANGIC_COOLDOWN
    client.mute_until = 0

    print(f"[OWO] Kasma başladı. Kanal: {kanal.name} | Başlangıç Cooldown: {client.cooldown}s")

    while not client.is_closed():
        now = asyncio.get_event_loop().time()

        # 1) Mute kontrolü
        if now < client.mute_until:
            bekle = client.mute_until - now
            print(f"[OWO] Mute nedeniyle {bekle:.1f}s bekleniyor...")
            await asyncio.sleep(bekle)
            continue

        # 2) Cooldown bekle
        print(f"[OWO] Cooldown bekleniyor: {client.cooldown}s")
        await asyncio.sleep(client.cooldown)

        # Mute tekrar kontrol (bekleme sırasında mute gelmiş olabilir)
        if asyncio.get_event_loop().time() < client.mute_until:
            continue

        # 3) Rastgele komut seç ve gönder
        komut = random.choice(KOMUTLAR)
        try:
            await kanal.send(komut)
            print(f"[OWO] Gönderildi: {komut} (Cooldown: {client.cooldown}s)")
        except Exception as e:
            print(f"[OWO] Mesaj gönderme hatası: {e}")
            await asyncio.sleep(5)
            continue

        # 4) Cooldown süresini artır
        client.cooldown += COOLDOWN_ARTIS

        # OwO'nun cevabını işlemesi için kısa bir süre tanı
        await asyncio.sleep(2)

# -------------------------------------------------------------------
# BOTU ÇALIŞTIR
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Ana bot token'ınızı buraya yazın
    ANA_BOT_TOKEN = "ANA_BOT_TOKENINIZ"
    bot.run(ANA_BOT_TOKEN)
