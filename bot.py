from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import google.generativeai as genai

import os
import asyncio
import sqlite3
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# ==================================================
# CONFIG
# ==================================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# SEU ID TELEGRAM
ADMIN_IDS = [5651378630]

# ID DO GRUPO
GRUPO_ID = -1002913144849

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# ==================================================
# GEMINI
# ==================================================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

# ==================================================
# LOGS
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==================================================
# DATABASE
# ==================================================

conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS funcionarios(
    user_id INTEGER PRIMARY KEY,
    nome TEXT
)
""")

conn.commit()

# ==================================================
# MEMÓRIA IA
# ==================================================

memoria = {}

MAX_MEMORIA = 10

# ==================================================
# CONFIGURAÇÕES
# ==================================================

mensagem_manha = "Bom dia 🚀"

mensagem_tarde = "Boa tarde 🚀"

horario_manha = "08:00"

horario_tarde = "15:00"

# ==================================================
# CONTROLE
# ==================================================

tarefas_pendentes = {}

ultimo_envio = ""

# ==================================================
# FUNÇÕES
# ==================================================

def eh_admin(user_id):
    return user_id in ADMIN_IDS

# ==================================================
# BLOQUEAR COMANDOS NO GRUPO
# ==================================================

async def bloquear_grupo(update):

    if update.effective_chat.id == GRUPO_ID:

        await update.message.reply_text(
            "❌ Use comandos apenas no privado."
        )

        return True

    return False

# ==================================================
# START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    texto = """
🤖 BOT ONLINE

COMANDOS:

/addfuncionario ID Nome

/removerfuncionario ID

/listar

/manha mensagem

/tarde mensagem

/horario_manha 08:00

/horario_tarde 15:00
"""

    await update.message.reply_text(texto)

# ==================================================
# ADD FUNCIONÁRIO
# ==================================================

async def addfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    try:

        user_id = int(context.args[0])

        nome = " ".join(context.args[1:])

        cursor.execute(
            """
            INSERT OR REPLACE INTO funcionarios
            VALUES (?, ?)
            """,
            (user_id, nome)
        )

        conn.commit()

        await update.message.reply_text(
            f"✅ Funcionário {nome} adicionado."
        )

    except:

        await update.message.reply_text(
            "Use:\n/addfuncionario ID Nome"
        )

# ==================================================
# REMOVER FUNCIONÁRIO
# ==================================================

async def removerfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await bloquear_grupo(update):
        return

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
            "🗑 Funcionário removido."
        )

    except:

        await update.message.reply_text(
            "Use:\n/removerfuncionario ID"
        )

# ==================================================
# LISTAR
# ==================================================

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    cursor.execute(
        "SELECT * FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:

        await update.message.reply_text(
            "❌ Nenhum funcionário."
        )

        return

    texto = "📋 FUNCIONÁRIOS\n\n"

    for f in funcionarios:

        texto += f"👤 {f[1]}\n🆔 {f[0]}\n\n"

    await update.message.reply_text(texto)

# ==================================================
# CONFIG MANHÃ
# ==================================================

async def manha(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global mensagem_manha

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    mensagem_manha = " ".join(context.args)

    await update.message.reply_text(
        "✅ Mensagem da manhã salva."
    )

# ==================================================
# CONFIG TARDE
# ==================================================

async def tarde(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global mensagem_tarde

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    mensagem_tarde = " ".join(context.args)

    await update.message.reply_text(
        "✅ Mensagem da tarde salva."
    )

# ==================================================
# HORÁRIO MANHÃ
# ==================================================

async def horario_m(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global horario_manha

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    horario_manha = context.args[0]

    await update.message.reply_text(
        f"✅ Horário manhã salvo: {horario_manha}"
    )

# ==================================================
# HORÁRIO TARDE
# ==================================================

async def horario_t(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global horario_tarde

    if await bloquear_grupo(update):
        return

    if not eh_admin(update.effective_user.id):
        return

    horario_tarde = context.args[0]

    await update.message.reply_text(
        f"✅ Horário tarde salvo: {horario_tarde}"
    )

# ==================================================
# ENVIAR TAREFAS
# ==================================================

async def enviar_tarefas(context: ContextTypes.DEFAULT_TYPE):

    global ultimo_envio

    agora = datetime.now(TIMEZONE)

    hora_atual = agora.strftime("%H:%M")

    periodo = None
    mensagem = None

    if hora_atual == horario_manha:

        periodo = "🌅 MANHÃ"

        mensagem = mensagem_manha

    elif hora_atual == horario_tarde:

        periodo = "🌇 TARDE"

        mensagem = mensagem_tarde

    if not periodo:
        return

    controle = f"{agora.date()}-{hora_atual}"

    if ultimo_envio == controle:
        return

    ultimo_envio = controle

    cursor.execute(
        "SELECT * FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:
        return

    marcacoes = ""

    for funcionario in funcionarios:

        user_id = funcionario[0]

        nome = funcionario[1]

        tarefas_pendentes[user_id] = periodo

        marcacoes += (
            f'<a href="tg://user?id={user_id}">{nome}</a>\n'
        )

    texto = f"""
📢 {periodo}

{mensagem}

{marcacoes}

Respondam:
✅ feito
✅ concluído
✅ ok
"""

    try:

        await context.bot.send_message(
            chat_id=GRUPO_ID,
            text=texto,
            parse_mode="HTML"
        )

        logging.info("Tarefa enviada.")

    except Exception as e:

        logging.error(f"Erro ao enviar tarefa: {e}")

# ==================================================
# IA + RESPOSTAS
# ==================================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        texto = update.message.text

        if not texto:
            return

        user_id = update.effective_user.id

        chat_id = update.effective_chat.id

        texto_lower = texto.lower()

        # ==================================================
        # CONFIRMAR TAREFA
        # ==================================================

        palavras = [
            "feito",
            "concluido",
            "concluído",
            "ok"
        ]

        if user_id in tarefas_pendentes:

            if any(p in texto_lower for p in palavras):

                del tarefas_pendentes[user_id]

                await update.message.reply_text(
                    "✅ Tarefa concluída confirmada."
                )

                # AVISA ADMIN

                for admin in ADMIN_IDS:

                    await context.bot.send_message(
                        chat_id=admin,
                        text=f"""
📌 Tarefa concluída

👤 Funcionário:
{user_id}

💬 Resposta:
{texto}
"""
                    )

                return

        # ==================================================
        # IA NO GRUPO
        # ==================================================

        ativar_ia = False

        if chat_id == GRUPO_ID:

            if (
                "ia" in texto_lower
                or "bot" in texto_lower
            ):
                ativar_ia = True

        else:

            ativar_ia = True

        if not ativar_ia:
            return

        # ==================================================
        # PRIVADO
        # ==================================================

        if (
            update.effective_chat.type == "private"
            and not eh_admin(user_id)
        ):

            await update.message.reply_text(
                "❌ Sem acesso."
            )

            return

        # ==================================================
        # MEMÓRIA
        # ==================================================

        if user_id not in memoria:

            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {texto}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MEMORIA:]

        historico = "\n".join(
            memoria[user_id]
        )

        prompt = f"""
Você é uma IA inteligente e natural.

REGRAS:

- Responda em português
- Seja objetiva
- Seja humana
- Use emojis quando necessário
- Não faça textos gigantes
- Nunca corte frases

CONVERSA:
{historico}

IA:
"""

        resposta = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 1000,
            }
        )

        resposta_texto = resposta.text.strip()

        memoria[user_id].append(
            f"IA: {resposta_texto}"
        )

        # ==================================================
        # DIVIDIR MENSAGEM
        # ==================================================

        limite = 3500

        partes = [

            resposta_texto[i:i + limite]

            for i in range(
                0,
                len(resposta_texto),
                limite
            )
        ]

        for parte in partes:

            await update.message.reply_text(
                parte
            )

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(
            "❌ Erro temporário."
        )

# ==================================================
# MAIN
# ==================================================

async def main():

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    comandos = [

        BotCommand("start", "Iniciar"),

        BotCommand(
            "addfuncionario",
            "Adicionar funcionário"
        ),

        BotCommand(
            "removerfuncionario",
            "Remover funcionário"
        ),

        BotCommand(
            "listar",
            "Listar funcionários"
        ),

        BotCommand(
            "manha",
            "Mensagem manhã"
        ),

        BotCommand(
            "tarde",
            "Mensagem tarde"
        ),

        BotCommand(
            "horario_manha",
            "Horário manhã"
        ),

        BotCommand(
            "horario_tarde",
            "Horário tarde"
        ),
    ]

    await app.bot.set_my_commands(
        comandos
    )

    # COMANDOS

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "addfuncionario",
            addfuncionario
        )
    )

    app.add_handler(
        CommandHandler(
            "removerfuncionario",
            removerfuncionario
        )
    )

    app.add_handler(
        CommandHandler(
            "listar",
            listar
        )
    )

    app.add_handler(
        CommandHandler(
            "manha",
            manha
        )
    )

    app.add_handler(
        CommandHandler(
            "tarde",
            tarde
        )
    )

    app.add_handler(
        CommandHandler(
            "horario_manha",
            horario_m
        )
    )

    app.add_handler(
        CommandHandler(
            "horario_tarde",
            horario_t
        )
    )

    # IA

    app.add_handler(

        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    # ==================================================
    # SCHEDULER
    # ==================================================

    scheduler = AsyncIOScheduler(
        timezone=TIMEZONE
    )

    scheduler.add_job(
        enviar_tarefas,
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

# ==================================================
# START
# ==================================================

if __name__ == "__main__":

    asyncio.run(main())
