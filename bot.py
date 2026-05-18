from telegram import (
    Update,
    BotCommand
)

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

# SEU ID TELEGRAM
ADMIN_ID = 5651378630

# ID DO GRUPO
GRUPO_ID = -1001234567890

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# =========================================
# GEMINI
# =========================================

if not TOKEN:
    raise Exception("TOKEN não encontrada")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY não encontrada")

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
CREATE TABLE IF NOT EXISTS usuarios (
    user_id INTEGER PRIMARY KEY,
    nome TEXT,
    mensagens INTEGER DEFAULT 0,
    criado_em TEXT
)
""")

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
MAX_MSG = 6

# =========================================
# CONTROLE
# =========================================

usuarios_aguardando = {}
ultimo_tempo = {}
TEMPO_MINIMO = 1.5

# =========================================
# SYSTEM PROMPT
# =========================================

SYSTEM_PROMPT = """
Você é uma inteligência artificial extremamente inteligente, organizada e natural.

REGRAS:

- Responda em português brasileiro
- Nunca fale como robô
- Seja parecida com ChatGPT
- Responda curto quando possível
- Explique melhor quando necessário
- Organize respostas
- Use emojis quando combinar
- Use listas organizadas
- Não faça textões desnecessários
- Nunca corte respostas no meio
- Sempre finalize o raciocínio
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
# USUÁRIOS
# =========================================

def criar_usuario(user_id, nome):

    cursor.execute(
        "SELECT * FROM usuarios WHERE user_id=?",
        (user_id,)
    )

    usuario = cursor.fetchone()

    if not usuario:

        cursor.execute(
            """
            INSERT INTO usuarios
            (user_id, nome, criado_em)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                nome,
                str(datetime.now())
            )
        )

        conn.commit()

# =========================================
# COMANDOS TELEGRAM
# =========================================

async def configurar_comandos(app):

    comandos = [

        BotCommand("start", "Iniciar bot"),
        BotCommand("comandos", "Ver comandos"),
        BotCommand("addfuncionario", "Adicionar funcionário"),
        BotCommand("removerfuncionario", "Remover funcionário"),
        BotCommand("listar", "Listar funcionários"),
        BotCommand("horario", "Definir horário"),
        BotCommand("mensagem", "Definir mensagem"),
        BotCommand("ligar", "Ativar sistema"),
        BotCommand("desligar", "Desativar sistema"),
        BotCommand("ping", "Status bot")
    ]

    await app.bot.set_my_commands(comandos)

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto = """
🤖 BOT ONLINE 🚀

💬 Sistema funcionando.

Use /comandos
"""

    await update.message.reply_text(texto)

# =========================================
# COMANDOS
# =========================================

async def comandos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto = """
📌 COMANDOS

/addfuncionario ID Nome

/removerfuncionario ID

/listar

/horario 08:00

/mensagem texto

/ligar

/desligar

/ping
"""

    await update.message.reply_text(texto)

# =========================================
# ADD FUNCIONÁRIO
# =========================================

async def addfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    args = context.args

    if len(args) < 2:

        await update.message.reply_text(
            "Use:\n/addfuncionario ID Nome"
        )

        return

    user_id = int(args[0])
    nome = " ".join(args[1:])

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
        f"✅ Funcionário {nome} adicionado"
    )

# =========================================
# REMOVER
# =========================================

async def removerfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    args = context.args

    if not args:

        await update.message.reply_text(
            "Use:\n/removerfuncionario ID"
        )

        return

    user_id = int(args[0])

    cursor.execute(
        "DELETE FROM funcionarios WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

    await update.message.reply_text(
        "🗑 Funcionário removido"
    )

# =========================================
# LISTAR
# =========================================

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    cursor.execute(
        "SELECT user_id, nome FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:

        await update.message.reply_text(
            "❌ Nenhum funcionário cadastrado"
        )

        return

    texto = "📋 FUNCIONÁRIOS\n\n"

    for funcionario in funcionarios:

        texto += f"👤 {funcionario[1]}\nID: {funcionario[0]}\n\n"

    await update.message.reply_text(texto)

# =========================================
# HORÁRIO
# =========================================

async def horario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    args = context.args

    if not args:

        await update.message.reply_text(
            "Use:\n/horario 08:00"
        )

        return

    novo_horario = args[0]

    salvar_config(
        "horario",
        novo_horario
    )

    await update.message.reply_text(
        f"⏰ Horário definido para {novo_horario}"
    )

# =========================================
# MENSAGEM
# =========================================

async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto_msg = update.message.text.replace(
        "/mensagem",
        ""
    ).strip()

    if not texto_msg:

        await update.message.reply_text(
            "Use:\n/mensagem sua mensagem"
        )

        return

    salvar_config(
        "mensagem",
        texto_msg
    )

    await update.message.reply_text(
        "✅ Mensagem salva"
    )

# =========================================
# LIGAR
# =========================================

async def ligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    salvar_config(
        "ativo",
        "1"
    )

    await update.message.reply_text(
        "🟢 Sistema ativado"
    )

# =========================================
# DESLIGAR
# =========================================

async def desligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    salvar_config(
        "ativo",
        "0"
    )

    await update.message.reply_text(
        "🔴 Sistema desligado"
    )

# =========================================
# PING
# =========================================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    agora = datetime.now(TIMEZONE).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    await update.message.reply_text(
        f"🟢 BOT ONLINE\n\n🕒 Brasília:\n{agora}"
    )

# =========================================
# ENVIAR AVISO
# =========================================

async def enviar_aviso(app):

    ativo = pegar_config("ativo", "0")

    if ativo != "1":
        return

    horario = pegar_config("horario")

    if not horario:
        return

    agora = datetime.now(TIMEZONE).strftime(
        "%H:%M"
    )

    if agora != horario:
        return

    mensagem = pegar_config(
        "mensagem",
        "Bom dia 🚀"
    )

    cursor.execute(
        "SELECT user_id, nome FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:
        return

    marcacoes = ""

    for funcionario in funcionarios:

        user_id = funcionario[0]
        nome = funcionario[1]

        marcacoes += (
            f'<a href="tg://user?id={user_id}">{nome}</a>\n'
        )

        usuarios_aguardando[user_id] = time.time()

    texto = f"""
📢 AVISO

{mensagem}

{marcacoes}

✅ Respondam o grupo.
"""

    try:

        await app.bot.send_message(
            chat_id=GRUPO_ID,
            text=texto,
            parse_mode="HTML"
        )

        asyncio.create_task(
            verificar_respostas(app)
        )

    except Exception as e:

        print(e)

# =========================================
# VERIFICAR RESPOSTAS
# =========================================

async def verificar_respostas(app):

    await asyncio.sleep(600)

    if not usuarios_aguardando:
        return

    marcacoes = ""

    for user_id in usuarios_aguardando:

        cursor.execute(
            "SELECT nome FROM funcionarios WHERE user_id=?",
            (user_id,)
        )

        resultado = cursor.fetchone()

        if resultado:

            nome = resultado[0]

            marcacoes += (
                f'<a href="tg://user?id={user_id}">{nome}</a>\n'
            )

    if marcacoes:

        texto = f"""
⚠️ Ainda não responderam:

{marcacoes}
"""

        try:

            await app.bot.send_message(
                chat_id=GRUPO_ID,
                text=texto,
                parse_mode="HTML"
            )

        except:
            pass

# =========================================
# IA
# =========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        mensagem = update.message.text.strip()

        if not mensagem:
            return

        user = update.message.from_user

        user_id = user.id
        nome = user.first_name

        if user_id in usuarios_aguardando:

            del usuarios_aguardando[user_id]

        criar_usuario(user_id, nome)

        if update.message.chat.type == "private":

            if not eh_admin(user_id):

                await update.message.reply_text(
                    "❌ Você não tem acesso"
                )

                return

        agora = time.time()

        if user_id in ultimo_tempo:

            diferenca = agora - ultimo_tempo[user_id]

            if diferenca < TEMPO_MINIMO:

                await update.message.reply_text(
                    "⏳ Aguarde um momento"
                )

                return

        ultimo_tempo[user_id] = agora

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )

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
                "temperature": 0.8,
                "max_output_tokens": 500,
            }
        )

        texto = resposta.text.strip()

        memoria[user_id].append(
            f"IA: {texto}"
        )

        await asyncio.sleep(
            random.uniform(0.8, 1.8)
        )

        LIMITE_TELEGRAM = 3500

        partes = [
            texto[i:i + LIMITE_TELEGRAM]
            for i in range(0, len(texto), LIMITE_TELEGRAM)
        ]

        for parte in partes:

            await update.message.reply_text(parte)

    except Exception as e:

        logging.error(str(e))

        await update.message.reply_text(
            "❌ Erro temporário na IA"
        )

# =========================================
# MAIN
# =========================================

async def main():

    app = ApplicationBuilder().token(TOKEN).build()

    await configurar_comandos(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("comandos", comandos))
    app.add_handler(CommandHandler("addfuncionario", addfuncionario))
    app.add_handler(CommandHandler("removerfuncionario", removerfuncionario))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("horario", horario))
    app.add_handler(CommandHandler("mensagem", mensagem))
    app.add_handler(CommandHandler("ligar", ligar))
    app.add_handler(CommandHandler("desligar", desligar))
    app.add_handler(CommandHandler("ping", ping))

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
        minutes=1,
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

asyncio.run(main())
