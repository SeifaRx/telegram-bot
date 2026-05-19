# ======================================================
# BOT TELEGRAM IA + FUNCIONÁRIOS + ALERTAS + GEMINI
# ======================================================

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

# ======================================================
# LOGS
# ======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ======================================================
# CONFIG
# ======================================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADMIN_ID = 5651378630
GRUPO_ID = -1002913144849

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# ======================================================
# GEMINI
# ======================================================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# ======================================================
# DATABASE
# ======================================================

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

# ======================================================
# MEMÓRIA
# ======================================================

memoria = {}

MAX_MSG = 12

usuarios_aguardando = {}

ultimo_tempo = {}

tarefas = {}

ultimo_envio = None

# ======================================================
# ALERTAS
# ======================================================

palavras_alerta = [
    "urgente",
    "erro",
    "falha",
    "problema",
    "emergencia",
]

# ======================================================
# PROMPT
# ======================================================

SYSTEM_PROMPT = """
Você é uma IA extremamente inteligente, moderna e humana.

REGRAS:

- Responda em português brasileiro
- Seja natural
- Seja útil
- Seja moderna
- Nunca responda igual robô
- Use emojis quando fizer sentido
- Seja organizada
- Nunca corte respostas
- Use contexto da conversa
- Seja amigável
- Responda igual ChatGPT
"""

# ======================================================
# FUNÇÕES
# ======================================================

def eh_admin(user_id):
    return user_id == ADMIN_ID

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

# ======================================================
# START
# ======================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
🤖 BOT ONLINE

📌 COMANDOS

/addfuncionario ID Nome
/removerfuncionario ID
/listar
/tarefa ID tarefa
/pendentes
/concluir ID
/alerta mensagem
/status
/ligar
/desligar
"""

    await update.message.reply_text(texto)

# ======================================================
# STATUS
# ======================================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ativo = pegar_config("ativo", "0")

    status_texto = (
        "🟢 Ativo"
        if ativo == "1"
        else "🔴 Desligado"
    )

    agora = datetime.now(TIMEZONE).strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    texto = f"""
📊 STATUS

🕒 {agora}

⚙️ Sistema:
{status_texto}

👥 Funcionários:
{len(usuarios_aguardando)}

📋 Tarefas:
{len(tarefas)}
"""

    await update.message.reply_text(texto)

# ======================================================
# ADD FUNCIONÁRIO
# ======================================================

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

# ======================================================
# REMOVER FUNCIONÁRIO
# ======================================================

async def removerfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.effective_user.id):
        return

    try:

        user_id = int(context.args[0])

        cursor.execute(
            "DELETE FROM funcionarios WHERE user_id=?",
            (user_id,)
        )

        conn.commit()

        await update.message.reply_text(
            "🗑 Funcionário removido"
        )

    except:

        await update.message.reply_text(
            "Use:\n/removerfuncionario ID"
        )

# ======================================================
# LISTAR
# ======================================================

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

    for funcionario in funcionarios:

        texto += (
            f"👤 {funcionario[1]}\n"
            f"🆔 {funcionario[0]}\n\n"
        )

    await update.message.reply_text(texto)

# ======================================================
# TAREFA
# ======================================================

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.effective_user.id):
        return

    try:

        user_id = int(context.args[0])

        texto = " ".join(context.args[1:])

        tarefas[user_id] = texto

        await context.bot.send_message(
            chat_id=GRUPO_ID,
            text=(
                f"📌 NOVA TAREFA\n\n"
                f'<a href="tg://user?id={user_id}">Funcionário</a>\n\n'
                f"📝 {texto}"
            ),
            parse_mode="HTML"
        )

        await update.message.reply_text(
            "✅ Tarefa enviada"
        )

    except:

        await update.message.reply_text(
            "Use:\n/tarefa ID tarefa"
        )

# ======================================================
# PENDENTES
# ======================================================

async def pendentes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not tarefas:

        await update.message.reply_text(
            "✅ Nenhuma tarefa pendente"
        )

        return

    texto = "📋 TAREFAS PENDENTES\n\n"

    for user_id, tarefa_texto in tarefas.items():

        cursor.execute(
            "SELECT nome FROM funcionarios WHERE user_id=?",
            (user_id,)
        )

        resultado = cursor.fetchone()

        nome = resultado[0] if resultado else "Funcionário"

        texto += f"👤 {nome}\n📝 {tarefa_texto}\n\n"

    await update.message.reply_text(texto)

# ======================================================
# CONCLUIR
# ======================================================

async def concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        user_id = int(context.args[0])

        if user_id in tarefas:

            del tarefas[user_id]

            await update.message.reply_text(
                "✅ Tarefa concluída"
            )

        else:

            await update.message.reply_text(
                "❌ Nenhuma tarefa"
            )

    except:

        await update.message.reply_text(
            "Use:\n/concluir ID"
        )

# ======================================================
# ALERTA
# ======================================================

async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.effective_user.id):
        return

    texto = " ".join(context.args)

    if not texto:

        await update.message.reply_text(
            "Use:\n/alerta mensagem"
        )

        return

    await context.bot.send_message(
        chat_id=GRUPO_ID,
        text=f"🚨 ALERTA\n\n{texto}"
    )

# ======================================================
# LIGAR
# ======================================================

async def ligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    salvar_config("ativo", "1")

    await update.message.reply_text(
        "🟢 Sistema ativado"
    )

# ======================================================
# DESLIGAR
# ======================================================

async def desligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    salvar_config("ativo", "0")

    await update.message.reply_text(
        "🔴 Sistema desligado"
    )

# ======================================================
# AVISO AUTOMÁTICO
# ======================================================

async def enviar_aviso(context: ContextTypes.DEFAULT_TYPE):

    global ultimo_envio

    ativo = pegar_config("ativo", "0")

    if ativo != "1":
        return

    agora = datetime.now(TIMEZONE)

    horario = agora.strftime("%H:%M")

    horarios = ["08:00", "13:00"]

    if horario not in horarios:
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

        marcacoes += (
            f'<a href="tg://user?id={user_id}">{nome}</a>\n'
        )

    texto = f"""
📢 BOM DIA EQUIPE

Respondam confirmando suas tarefas 🚀

{marcacoes}
"""

    await context.bot.send_message(
        chat_id=GRUPO_ID,
        text=texto,
        parse_mode="HTML"
    )

# ======================================================
# IA
# ======================================================

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

        # ======================================================
        # CONFIRMAÇÃO
        # ======================================================

        if user_id in usuarios_aguardando:

            del usuarios_aguardando[user_id]

            await update.message.reply_text(
                f"✅ Presença confirmada, {nome}!"
            )

        # ======================================================
        # TAREFA CONCLUÍDA
        # ======================================================

        if user_id in tarefas:

            palavras = [
                "feito",
                "concluido",
                "pronto",
                "finalizado",
                "terminei",
            ]

            if any(
                p in mensagem.lower()
                for p in palavras
            ):

                del tarefas[user_id]

                await update.message.reply_text(
                    f"✅ Tarefa confirmada, {nome}!"
                )

                return

        # ======================================================
        # ALERTA AUTOMÁTICO
        # ======================================================

        if any(
            p in mensagem.lower()
            for p in palavras_alerta
        ):

            await context.bot.send_message(
                chat_id=GRUPO_ID,
                text=(
                    f"🚨 ALERTA DETECTADO\n\n"
                    f"👤 {nome}\n"
                    f"💬 {mensagem}"
                )
            )

        # ======================================================
        # IA NO GRUPO
        # ======================================================

        responder_ia = False

        if update.effective_chat.type == "private":

            responder_ia = True

        else:

            if (
                context.bot.username.lower()
                in mensagem.lower()
            ):

                responder_ia = True

            elif update.message.reply_to_message:

                if (
                    update.message.reply_to_message.from_user.id
                    == context.bot.id
                ):

                    responder_ia = True

        if not responder_ia:
            return

        # ======================================================
        # ANTI FLOOD
        # ======================================================

        agora = time.time()

        if user_id in ultimo_tempo:

            diferenca = agora - ultimo_tempo[user_id]

            if diferenca < 1:
                return

        ultimo_tempo[user_id] = agora

        # ======================================================
        # DIGITANDO
        # ======================================================

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING
        )

        # ======================================================
        # MEMÓRIA
        # ======================================================

        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {mensagem}"
        )

        memoria[user_id] = memoria[user_id][-12:]

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
                "max_output_tokens": 1800,
            }
        )

        texto = resposta.text.strip()

        memoria[user_id].append(
            f"IA: {texto}"
        )

        limite = 3500

        partes = [
            texto[i:i + limite]
            for i in range(0, len(texto), limite)
        ]

        for parte in partes:

            await asyncio.sleep(
                random.uniform(0.5, 1.2)
            )

            await update.message.reply_text(parte)

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(
            "❌ Erro temporário."
        )

# ======================================================
# MAIN
# ======================================================

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
        BotCommand("pendentes", "Pendências"),
        BotCommand("ligar", "Ativar"),
        BotCommand("desligar", "Desativar"),
    ]

    await app.bot.set_my_commands(comandos)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("addfuncionario", addfuncionario))
    app.add_handler(CommandHandler("removerfuncionario", removerfuncionario))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("tarefa", tarefa))
    app.add_handler(CommandHandler("pendentes", pendentes))
    app.add_handler(CommandHandler("concluir", concluir))
    app.add_handler(CommandHandler("alerta", alerta))
    app.add_handler(CommandHandler("ligar", ligar))
    app.add_handler(CommandHandler("desligar", desligar))

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

# ======================================================
# START
# ======================================================

if __name__ == "__main__":

    asyncio.run(main())
