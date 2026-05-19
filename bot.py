from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from telegram.constants import ChatAction

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import google.generativeai as genai

import os
import asyncio
import sqlite3
import logging
import random
import time

from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================
# LOGS
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================
# CONFIG
# =========================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADMIN_ID = 5651378630
GRUPO_ID = -1001234567890

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# =========================================
# GEMINI
# =========================================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS funcionarios (
    user_id INTEGER PRIMARY KEY,
    nome TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT
)
""")

conn.commit()

# =========================================
# MEMÓRIA
# =========================================

memoria = {}

MAX_MSG = 12

usuarios_aguardando = {}

ultimo_tempo = {}

# =========================================
# IA
# =========================================

SYSTEM_PROMPT = """
Você é uma IA extremamente inteligente e humana.

REGRAS:

- Responda em português brasileiro
- Seja natural
- Seja moderna
- Use emojis quando fizer sentido
- Não faça respostas gigantes sem necessidade
- Explique bem
- Seja útil
- Nunca corte frases
- Fale igual ChatGPT
"""

# =========================================
# ADMIN
# =========================================

def eh_admin(user_id):
    return user_id == ADMIN_ID

# =========================================
# CONFIG
# =========================================

def salvar_config(chave, valor):

    cursor.execute(
        """
        INSERT OR REPLACE INTO configuracoes
        (chave, valor)
        VALUES (?, ?)
        """,
        (chave, valor)
    )

    conn.commit()

def pegar_config(chave, padrao=None):

    cursor.execute(
        "SELECT valor FROM configuracoes WHERE chave=?",
        (chave,)
    )

    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    return padrao

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
🤖 BOT ONLINE

Comandos:

/status
/listar
/ligar
/desligar
"""

    await update.message.reply_text(texto)

# =========================================
# STATUS
# =========================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    agora = datetime.now(TIMEZONE).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    ativo = pegar_config("ativo", "0")

    status_texto = "🟢 Ativo" if ativo == "1" else "🔴 Desligado"

    texto = f"""
📊 STATUS

🕒 {agora}

⚙️ Sistema:
{status_texto}
"""

    await update.message.reply_text(texto)

# =========================================
# ADD FUNCIONÁRIO
# =========================================

async def addfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.effective_user.id):
        return

    try:

        user_id = int(context.args[0])

        nome = " ".join(context.args[1:])

        cursor.execute(
            """
            INSERT OR REPLACE INTO funcionarios
            (user_id, nome)
            VALUES (?, ?)
            """,
            (user_id, nome)
        )

        conn.commit()

        await update.message.reply_text(
            f"✅ {nome} adicionado"
        )

    except:

        await update.message.reply_text(
            "Use:\n/addfuncionario ID Nome"
        )

# =========================================
# LISTAR
# =========================================

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute(
        "SELECT * FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:

        await update.message.reply_text(
            "❌ Nenhum funcionário"
        )

        return

    texto = "📋 FUNCIONÁRIOS\n\n"

    for f in funcionarios:

        texto += f"👤 {f[1]}\n🆔 {f[0]}\n\n"

    await update.message.reply_text(texto)

# =========================================
# LIGAR
# =========================================

async def ligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    salvar_config("ativo", "1")

    await update.message.reply_text(
        "🟢 Sistema ativado"
    )

# =========================================
# DESLIGAR
# =========================================

async def desligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    salvar_config("ativo", "0")

    await update.message.reply_text(
        "🔴 Sistema desligado"
    )

# =========================================
# AVISO
# =========================================

ultimo_envio = None

async def enviar_aviso(context: ContextTypes.DEFAULT_TYPE):

    global ultimo_envio

    ativo = pegar_config("ativo", "0")

    if ativo != "1":
        return

    agora = datetime.now(TIMEZONE)

    horario = agora.strftime("%H:%M")

    if horario != "08:00":
        return

    controle = agora.strftime("%Y-%m-%d %H:%M")

    if ultimo_envio == controle:
        return

    ultimo_envio = controle

    cursor.execute(
        "SELECT * FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:
        return

    usuarios_aguardando.clear()

    marcacoes = ""

    for funcionario in funcionarios:

        user_id = funcionario[0]
        nome = funcionario[1]

        usuarios_aguardando[user_id] = True

        marcacoes += f'<a href="tg://user?id={user_id}">{nome}</a>\n'

    texto = f"""
📢 Bom dia equipe!

Respondam confirmando suas tarefas 🚀

{marcacoes}
"""

    await context.bot.send_message(
        chat_id=GRUPO_ID,
        text=texto,
        parse_mode="HTML"
    )

# =========================================
# IA
# =========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        mensagem = update.message.text

        if not mensagem:
            return

        user_id = update.effective_user.id

        chat_id = update.effective_chat.id

        nome = update.effective_user.first_name

        # =========================================
        # CONFIRMA FUNCIONÁRIO
        # =========================================

        if user_id in usuarios_aguardando:

            del usuarios_aguardando[user_id]

            await update.message.reply_text(
                f"✅ Presença confirmada, {nome}!"
            )

        # =========================================
        # ANTI FLOOD
        # =========================================

        agora = time.time()

        if user_id in ultimo_tempo:

            diferenca = agora - ultimo_tempo[user_id]

            if diferenca < 1:

                return

        ultimo_tempo[user_id] = agora

        # =========================================
        # DIGITANDO
        # =========================================

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING
        )

        # =========================================
        # MEMÓRIA
        # =========================================

        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {mensagem}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MSG:]

        historico = "\n".join(memoria[user_id])

        prompt = f"""
{SYSTEM_PROMPT}

CONVERSA:
{historico}

IA:
"""

        resposta = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,
                "max_output_tokens": 1500,
            }
        )

        texto = resposta.text.strip()

        memoria[user_id].append(
            f"IA: {texto}"
        )

        # =========================================
        # DIVIDE RESPOSTA GRANDE
        # =========================================

        limite = 3500

        partes = [
            texto[i:i + limite]
            for i in range(0, len(texto), limite)
        ]

        for parte in partes:

            await update.message.reply_text(parte)

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(
            "❌ Erro temporário."
        )

# =========================================
# MAIN
# =========================================

async def main():

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    comandos = [

        BotCommand("start", "Iniciar"),
        BotCommand("status", "Status"),
        BotCommand("listar", "Funcionários"),
        BotCommand("ligar", "Ativar"),
        BotCommand("desligar", "Desativar"),
    ]

    await app.bot.set_my_commands(comandos)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("ligar", ligar))
    app.add_handler(CommandHandler("desligar", desligar))
    app.add_handler(CommandHandler("addfuncionario", addfuncionario))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    scheduler = AsyncIOScheduler(
        timezone=TIMEZONE
    )

    scheduler.add_job(
        enviar_aviso,
        "interval",
        seconds=30,
        args=[app]
    )

    scheduler.start()

    print("🚀 BOT ONLINE")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

# =========================================
# START
# =========================================

if __name__ == "__main__":
    asyncio.run(main())
