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

# IDs DOS ADMINS
ADMIN_IDS = [5651378630]

# ID DO GRUPO
GRUPO_ID = -1002913144849

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# ==================================================
# GEMINI
# ==================================================

genai.configure(
    api_key=GEMINI_API_KEY
)

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

mensagem_manha = "Verificar tarefas da manhã."

mensagem_tarde = "Verificar tarefas da tarde."

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

📌 COMANDOS

/addfuncionario ID Nome

/removerfuncionario ID

/listar

/manha tarefa da manhã

/tarde tarefa da tarde

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
        "✅ Tarefa da manhã salva."
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
        "✅ Tarefa da tarde salva."
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
    tarefa = None

    if hora_atual == horario_manha:

        periodo = "🌅 TAREFAS DA MANHÃ"

        tarefa = mensagem_manha

    elif hora_atual == horario_tarde:

        periodo = "🌇 TAREFAS DA TARDE"

        tarefa = mensagem_tarde

    else:
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

    texto = f"""
📋 {periodo}

📝 TAREFA:
{tarefa}

"""

    for funcionario in funcionarios:

        user_id = funcionario[0]

        nome = funcionario[1]

        tarefas_pendentes[user_id] = {
            "periodo": periodo,
            "tarefa": tarefa,
            "data": datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        }

        texto += (
            f'👤 <a href="tg://user?id={user_id}">{nome}</a>\n'
        )

    texto += """

✅ Responda:
- feito
- concluído
- ok
"""

    try:

        await context.bot.send_message(
            chat_id=GRUPO_ID,
            text=texto,
            parse_mode="HTML"
        )

        logging.info(
            "Tarefas enviadas."
        )

    except Exception as e:

        logging.error(
            f"Erro ao enviar tarefa: {e}"
        )

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
        # CONFIRMAÇÃO TAREFA
        # ==================================================

        palavras_confirmacao = [

            "feito",
            "concluido",
            "concluído",
            "ok",
            "finalizado",
            "terminei",
            "pronto"
        ]

        if user_id in tarefas_pendentes:

            dados = tarefas_pendentes[user_id]

            data_hoje = datetime.now(
                TIMEZONE
            ).strftime("%Y-%m-%d")

            if dados["data"] != data_hoje:

                del tarefas_pendentes[user_id]

                return

            if any(
                palavra in texto_lower
                for palavra in palavras_confirmacao
            ):

                del tarefas_pendentes[user_id]

                cursor.execute(
                    """
                    SELECT nome
                    FROM funcionarios
                    WHERE user_id=?
                    """,
                    (user_id,)
                )

                resultado = cursor.fetchone()

                nome = (
                    resultado[0]
                    if resultado
                    else str(user_id)
                )

                await update.message.reply_text(
                    f"""
✅ Tarefa concluída!

👏 Bom trabalho, {nome}

📋 {dados['periodo']}

📝 {dados['tarefa']}
"""
                )

                # AVISA ADM

                for admin in ADMIN_IDS:

                    try:

                        await context.bot.send_message(
                            chat_id=admin,
                            text=f"""
📌 FUNCIONÁRIO FINALIZOU

👤 {nome}

📝 Resposta:
{texto}

📋 Tarefa:
{dados['tarefa']}

🕒 Horário:
{datetime.now(TIMEZONE).strftime('%H:%M:%S')}
"""
                        )

                    except Exception as e:

                        logging.error(e)

                return

        # ==================================================
        # IA NO GRUPO SOMENTE CHAMANDO
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
        # PRIVADO SOMENTE ADMIN
        # ==================================================

        if (
            update.effective_chat.type == "private"
            and not eh_admin(user_id)
        ):

            return

        # ==================================================
        # MEMÓRIA IA
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
Você é uma IA extremamente inteligente.

REGRAS:

- Responda em português
- Seja natural
- Seja moderna
- Use emojis quando necessário
- Seja organizada
- Não faça textos gigantes
- Nunca corte respostas

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
            "Definir tarefa manhã"
        ),

        BotCommand(
            "tarde",
            "Definir tarefa tarde"
        ),

        BotCommand(
            "horario_manha",
            "Definir horário manhã"
        ),

        BotCommand(
            "horario_tarde",
            "Definir horário tarde"
        ),
    ]

    await app.bot.set_my_commands(
        comandos
    )

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

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    # ==================================================
    # AGENDADOR
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
