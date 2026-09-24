import os
import re
import random
import asyncio
import discord_self

SELF_TOKEN = os.getenv("SELF_TOKEN")
KANAL_ID = int(os.getenv("KANAL_ID", "0"))
OWO_BOT_ID = int(os.getenv("OWO_BOT_ID", "408785106942164992"))
BASLANGIC_COOLDOWN = int(os.getenv("BASLANGIC_COOLDOWN", "15"))
COOLDOWN_ARTIS = int(os.getenv("COOLDOWN_ARTIS", "1"))
KOMUTLAR = ["owo hunt", "owo battle", "owo pray"]

client = discord_self.Client()


@client.event
async def on_ready():
    print(f"[WORKER] Giriş: {client.user}")
    kanal = client.get_channel(KANAL_ID)
    if kanal is None:
        print(f"[WORKER] Kanal bulunamadı: {KANAL_ID}")
        await client.close()
        return
    client.loop.create_task(owo_kas(client, kanal))


@client.event
async def on_message(message):
    if message.author.id != OWO_BOT_ID:
        return
    içerik = message.content.lower()
    now = asyncio.get_event_loop().time()

    if "muted" in içerik:
        m = re.search(r"muted for (\d+)\s*(minute|second|hour|min|sec)", içerik)
        if m:
            miktar = int(m.group(1))
            birim = m.group(2)
            if "hour" in birim:
                saniye = miktar * 3600
            elif "min" in birim:
                saniye = miktar * 60
            else:
                saniye = miktar
            client.mute_until = now + saniye
            print(f"[WORKER] Mute: {saniye}s")
        else:
            client.mute_until = now + 300
            print("[WORKER] Mute: 300s")

    if "you can't use" in içerik or "slow down" in içerik:
        client.mute_until = now + 5


async def owo_kas(client, kanal):
    await client.wait_until_ready()
    client.cooldown = BASLANGIC_COOLDOWN
    client.mute_until = 0
    print(f"[WORKER] Kasma başladı. Cooldown: {client.cooldown}s")

    while not client.is_closed():
        now = asyncio.get_event_loop().time()
        if now < client.mute_until:
            await asyncio.sleep(client.mute_until - now)
            continue

        await asyncio.sleep(client.cooldown)

        if asyncio.get_event_loop().time() < client.mute_until:
            continue

        komut = random.choice(KOMUTLAR)
        try:
            await kanal.send(komut)
            print(f"[WORKER] {komut} gönderildi (cd: {client.cooldown}s)")
        except Exception as e:
            print(f"[WORKER] Hata: {e}")
            await asyncio.sleep(5)
            continue

        client.cooldown += COOLDOWN_ARTIS
        await asyncio.sleep(2)


if __name__ == "__main__":
    if not SELF_TOKEN or not KANAL_ID:
        print("❌ SELF_TOKEN veya KANAL_ID eksik!")
        raise SystemExit(1)
    try:
        client.run(SELF_TOKEN)
    except Exception as e:
        print(f"[WORKER] Çöktü: {e}")
        raise SystemExit(1)
