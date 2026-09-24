import os
import re
import random
import asyncio

import discord
from discord.ext import commands
import discord_self

# -------------------------------------------------------------------
# ORTAM DEĞİŞKENLERİ (Railway Variables'tan okunur)
# -------------------------------------------------------------------
ANA_BOT_TOKEN = os.getenv("ANA_BOT_TOKEN")
OWO_BOT_ID = int(os.getenv("OWO_BOT_ID", "408785106942164992"))
BASLANGIC_COOLDOWN = int(os.getenv("BASLANGIC_COOLDOWN", "15"))
COOLDOWN_ARTIS = int(os.getenv("COOLDOWN_ARTIS", "1"))

KOMUTLAR = ["owo hunt", "owo battle", "owo pray"]

# -------------------------------------------------------------------
# ANA BOT (Slash komutları)
# -------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Aktif self-bot istemcileri: { token: {"client": ..., "task": ..., "kanal": ...} }
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
    await interaction.response.defer(ephemeral=True)

    kanal = interaction.channel
    if kanal is None:
        await interaction.followup.send("❌ Bu komut sadece bir kanalda kullanılabilir.")
        return

    if token in aktif_hesaplar:
        await interaction.followup.send("⚠️ Bu token zaten aktif. Önce /remove ile kaldır.")
        return

    client = discord_self.Client()
    aktif_hesaplar[token] = {"client": client, "task": None, "kanal": kanal.id}

    @client.event
    async def on_ready():
        print(f"[SELF-BOT] Giriş yapıldı: {client.user}")
        task = client.loop.create_task(owo_kas(client, kanal))
        aktif_hesaplar[token]["task"] = task

    @client.event
    async def on_message(message: discord.Message):
        if message.author.id != OWO_BOT_ID:
            return
        await owo_mesaj_analiz(message, client)

    # İstemciyi arka planda başlat
    async def start_client():
        try:
            await client.start(token)
        except discord.LoginFailure:
            print(f"[SELF-BOT] Geçersiz token: {token[:10]}...")
            aktif_hesaplar.pop(token, None)
        except Exception as e:
            print(f"[SELF-BOT] Giriş hatası: {e}")
            aktif_hesaplar.pop(token, None)

    bot.loop.create_task(start_client())

    await interaction.followup.send(
        f"✅ Hesap ekleniyor ve OwO kasma başlatılıyor.\n"
        f"**Kanal:** {kanal.mention}\n"
        f"**Başlangıç Cooldown:** {BASLANGIC_COOLDOWN}s (her komutta +{COOLDOWN_ARTIS}s)\n"
        f"Token geçersizse loglarda hata görürsün."
    )


@bot.tree.command(name="remove", description="Ekli bir hesabı durdurur ve kaldırır.")
async def remove(interaction: discord.Interaction, token: str):
    await interaction.response.defer(ephemeral=True)

    if token not in aktif_hesaplar:
        await interaction.followup.send("❌ Bu token aktif değil.")
        return

    data = aktif_hesaplar.pop(token)
    task = data.get("task")
    if task:
        task.cancel()
    client = data["client"]
    try:
        await client.close()
    except Exception:
        pass
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
        kullanici = getattr(client, "user", None)
        mesaj += f"- `{kullanici}` | Kanal: <#{kanal_id}>\n"
    await interaction.followup.send(mesaj)


# -------------------------------------------------------------------
# OWO MESAJ ANALİZİ (Mute ve Cooldown tespiti)
# -------------------------------------------------------------------
async def owo_mesaj_analiz(message: discord.Message, client: discord_self.Client):
    içerik = message.content.lower()
    now = asyncio.get_event_loop().time()

    cooldown_match = re.search(r"in (\d+)\s*seconds", içerik)
    if cooldown_match:
        ow_süresi = int(cooldown_match.group(1))
        print(f"[OWO] Cooldown mesajı: {ow_süresi}s")

    if "muted" in içerik:
        mute_match = re.search(r"muted for (\d+)\s*(minute|second|hour|min|sec)", içerik)
        if mute_match:
            miktar = int(mute_match.group(1))
            birim = mute_match.group(2)
            if "hour" in birim:
                saniye = miktar * 3600
            elif "min" in birim:
                saniye = miktar * 60
            else:
                saniye = miktar
            client.mute_until = now + saniye
            print(f"[OWO] Mute algılandı! {saniye}s boyunca beklenecek.")
        else:
            client.mute_until = now + 300
            print("[OWO] Mute algılandı (süre belirsiz). 300s beklenecek.")

    if "you can't use" in içerik or "slow down" in içerik:
        client.mute_until = now + 5
        print("[OWO] Geçici kısıtlama algılandı. 5s beklenecek.")


# -------------------------------------------------------------------
# OWO KASMA DÖNGÜSÜ
# -------------------------------------------------------------------
async def owo_kas(client: discord_self.Client, kanal: discord.TextChannel):
    await client.wait_until_ready()

    client.cooldown = BASLANGIC_COOLDOWN
    client.mute_until = 0

    print(f"[OWO] Kasma başladı. Kanal: {kanal.name} | Başlangıç Cooldown: {client.cooldown}s")

    while not client.is_closed():
        now = asyncio.get_event_loop().time()

        if now < client.mute_until:
            bekle = client.mute_until - now
            print(f"[OWO] Mute nedeniyle {bekle:.1f}s bekleniyor...")
            await asyncio.sleep(bekle)
            continue

        print(f"[OWO] Cooldown bekleniyor: {client.cooldown}s")
        await asyncio.sleep(client.cooldown)

        if asyncio.get_event_loop().time() < client.mute_until:
            continue

        komut = random.choice(KOMUTLAR)
        try:
            await kanal.send(komut)
            print(f"[OWO] Gönderildi: {komut} (Cooldown: {client.cooldown}s)")
        except Exception as e:
            print(f"[OWO] Mesaj gönderme hatası: {e}")
            await asyncio.sleep(5)
            continue

        client.cooldown += COOLDOWN_ARTIS
        await asyncio.sleep(2)


# -------------------------------------------------------------------
# ÇALIŞTIR
# -------------------------------------------------------------------
if __name__ == "__main__":
    if not ANA_BOT_TOKEN:
        print("❌ HATA: ANA_BOT_TOKEN ortam değişkeni tanımlı değil!")
        raise SystemExit(1)
    bot.run(ANA_BOT_TOKEN)
