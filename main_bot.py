import os
import subprocess
import sys
import discord
from discord.ext import commands

ANA_BOT_TOKEN = os.getenv("ANA_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# { token: {"process": subprocess.Popen, "kanal": int} }
aktif_hesaplar = {}


@bot.event
async def on_ready():
    print(f"[ANA BOT] Giriş yapıldı: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"[ANA BOT] {len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"[ANA BOT] Slash senkronizasyon hatası: {e}")


@bot.tree.command(name="add", description="OwO kasmak için bir hesap (token) ekler.")
async def add(interaction: discord.Interaction, token: str):
    await interaction.response.defer(ephemeral=True)

    if interaction.channel is None:
        await interaction.followup.send("❌ Bu komut bir kanalda kullanılmalı.")
        return

    if token in aktif_hesaplar:
        await interaction.followup.send("⚠️ Bu token zaten aktif. Önce /remove.")
        return

    # Self-bot worker'ı ayrı bir process olarak başlat
    try:
        proc = subprocess.Popen(
            [sys.executable, "selfbot_worker.py"],
            env={**os.environ, "SELF_TOKEN": token, "KANAL_ID": str(interaction.channel.id)},
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Worker başlatılamadı: {e}")
        return

    aktif_hesaplar[token] = {"process": proc, "kanal": interaction.channel.id}
    await interaction.followup.send(
        f"✅ Hesap ayrı process'te başlatıldı.\n"
        f"**Kanal:** {interaction.channel.mention}\n"
        f"**Process PID:** `{proc.pid}`"
    )


@bot.tree.command(name="remove", description="Bir hesabı durdurur.")
async def remove(interaction: discord.Interaction, token: str):
    await interaction.response.defer(ephemeral=True)

    if token not in aktif_hesaplar:
        await interaction.followup.send("❌ Bu token aktif değil.")
        return

    data = aktif_hesaplar.pop(token)
    proc = data["process"]
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    await interaction.followup.send("✅ Hesap durduruldu.")


@bot.tree.command(name="list", description="Aktif hesapları listeler.")
async def list_accounts(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not aktif_hesaplar:
        await interaction.followup.send("📭 Aktif hesap yok.")
        return

    mesaj = "**Aktif Hesaplar:**\n"
    for token, data in aktif_hesaplar.items():
        proc = data["process"]
        durum = "🟢 Çalışıyor" if proc.poll() is None else "🔴 Durdu"
        mesaj += f"- `...{token[-8:]}` | Kanal: <#{data['kanal']}> | {durum}\n"
    await interaction.followup.send(mesaj)


if __name__ == "__main__":
    if not ANA_BOT_TOKEN:
        print("❌ ANA_BOT_TOKEN eksik!")
        raise SystemExit(1)
    bot.run(ANA_BOT_TOKEN)
