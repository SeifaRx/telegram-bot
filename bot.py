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

# SEU ID TELEGRAM
ADMIN_ID = 5651378630

# ID DO GRUPO
GRUPO_ID = -1001234567890

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# =========================================
# GEMINI
# =========================================

genai.configure(
    api_key=GEMINI_API_KEY
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
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
# MEMÓRIA IA
# =========================================

memoria = {}

MAX_MSG = 12

ultimo_tempo = {}

tarefas_pendentes = {}

ultimo_envio = ""

# =========================================
# PROMPT IA
# =========================================

SYSTEM_PROMPT = """
Você é uma IA extremamente inteligente.

REGRAS:

- Responda sempre em português
- Seja humana
- Seja moderna
- Seja útil
- Seja natural
- Nunca corte frases
- Não faça textos gigantes
- Use emojis quando fizer sentido
- Seja parecida com ChatGPT
"""

# =========================================
# FUNÇÕES
# =========================================

def eh_admin(user_id):

    return user_id == ADMIN_ID

def comando_liberado(update):

    # SOMENTE PRIVADO
    if update.effective_chat.type != "private":
        return False

    # SOMENTE ADMIN
    if update.effective_user.id != ADMIN_ID:
        return False

    return True

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

    if not comando_liberado(update):
        return

    texto = """
🤖 BOT ONLINE

📌 COMANDOS

/addfuncionario ID Nome

/removerfuncionario ID

/listar

/horario manha 08:00

/horario tarde 15:00

/tarefa manha Fazer relatório

/tarefa tarde Atualizar sistema

/ligar

/desligar

/status
"""

    await update.message.reply_text(texto)

# =========================================
# STATUS
# =========================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

    horario_manha = pegar_config(
        "horario_manha",
        "Não definido"
    )

    horario_tarde = pegar_config(
        "horario_tarde",
        "Não definido"
    )

    tarefa_manha = pegar_config(
        "tarefa_manha",
        "Não definida"
    )

    tarefa_tarde = pegar_config(
        "tarefa_tarde",
        "Não definida"
    )

    ativo = pegar_config(
        "ativo",
        "0"
    )

    sistema = (
        "🟢 Ligado"
        if ativo == "1"
        else "🔴 Desligado"
    )

    texto = f"""
📊 STATUS BOT

☀️ Horário manhã:
{horario_manha}

🌤 Horário tarde:
{horario_tarde}

📌 Tarefa manhã:
{tarefa_manha}

📌 Tarefa tarde:
{tarefa_tarde}

⚙️ Sistema:
{sistema}
"""

    await update.message.reply_text(texto)

# =========================================
# ADD FUNCIONÁRIO
# =========================================

async def addfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
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
# REMOVER FUNCIONÁRIO
# =========================================

async def removerfuncionario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
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

# =========================================
# LISTAR
# =========================================

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

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

        texto += (
            f"👤 {f[1]}\n"
            f"🆔 {f[0]}\n\n"
        )

    await update.message.reply_text(texto)

# =========================================
# HORÁRIO
# =========================================

async def horario(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

    try:

        periodo = context.args[0].lower()

        hora = context.args[1]

        salvar_config(
            f"horario_{periodo}",
            hora
        )

        await update.message.reply_text(
            f"✅ Horário da {periodo} salvo!"
        )

    except:

        await update.message.reply_text(
            """
Use:

/horario manha 08:00

/horario tarde 15:00
"""
        )

# =========================================
# TAREFA
# =========================================

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

    try:

        periodo = context.args[0].lower()

        texto = " ".join(context.args[1:])

        salvar_config(
            f"tarefa_{periodo}",
            texto
        )

        await update.message.reply_text(
            f"✅ Tarefa da {periodo} salva!"
        )

    except:

        await update.message.reply_text(
            """
Use:

/tarefa manha Fazer relatório

/tarefa tarde Atualizar sistema
"""
        )

# =========================================
# LIGAR
# =========================================

async def ligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

    salvar_config("ativo", "1")

    await update.message.reply_text(
        "🟢 Sistema ativado"
    )

# =========================================
# DESLIGAR
# =========================================

async def desligar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not comando_liberado(update):
        return

    salvar_config("ativo", "0")

    await update.message.reply_text(
        "🔴 Sistema desligado"
    )

# =========================================
# ENVIAR AVISO
# =========================================

async def enviar_aviso(app):

    global ultimo_envio

    ativo = pegar_config(
        "ativo",
        "0"
    )

    if ativo != "1":
        return

    agora = datetime.now(TIMEZONE)

    horario_atual = agora.strftime("%H:%M")

    horario_manha = pegar_config(
        "horario_manha"
    )

    horario_tarde = pegar_config(
        "horario_tarde"
    )

    periodo = None

    saudacao = None

    tarefa_texto = None

    # =====================================
    # MANHÃ
    # =====================================

    if horario_atual == horario_manha:

        periodo = "manha"

        saudacao = "☀️ Bom dia"

        tarefa_texto = pegar_config(
            "tarefa_manha",
            "Responder tarefa"
        )

    # =====================================
    # TARDE
    # =====================================

    elif horario_atual == horario_tarde:

        periodo = "tarde"

        saudacao = "🌤 Boa tarde"

        tarefa_texto = pegar_config(
            "tarefa_tarde",
            "Responder tarefa"
        )

    else:
        return

    controle = (
        f"{agora.strftime('%Y-%m-%d')}"
        f"{horario_atual}"
    )

    if ultimo_envio == controle:
        return

    ultimo_envio = controle

    cursor.execute(
        "SELECT * FROM funcionarios"
    )

    funcionarios = cursor.fetchall()

    if not funcionarios:
        return

    tarefas_pendentes.clear()

    marcacoes = ""

    for funcionario in funcionarios:

        user_id = funcionario[0]

        nome = funcionario[1]

        tarefas_pendentes[user_id] = periodo

        marcacoes += (
            f'<a href="tg://user?id={user_id}">'
            f'{nome}</a>\n'
        )

    texto = f"""
📢 {saudacao}

📌 TAREFA DA {periodo.upper()}:

{tarefa_texto}

✅ Respondam:
- feito
- concluído
- ok
- terminei

{marcacoes}
"""

    await app.bot.send_message(
        chat_id=GRUPO_ID,
        text=texto,
        parse_mode="HTML"
    )

    asyncio.create_task(
        cobrar_ausentes(app, periodo)
    )

# =========================================
# COBRAR AUSENTES
# =========================================

async def cobrar_ausentes(app, periodo):

    await asyncio.sleep(600)

    if not tarefas_pendentes:
        return

    marcacoes = ""

    for user_id in tarefas_pendentes:

        cursor.execute(
            """
            SELECT nome
            FROM funcionarios
            WHERE user_id=?
            """,
            (user_id,)
        )

        resultado = cursor.fetchone()

        if resultado:

            nome = resultado[0]

            marcacoes += (
                f'<a href="tg://user?id={user_id}">'
                f'{nome}</a>\n'
            )

    if not marcacoes:
        return

    texto = f"""
⚠️ Funcionários sem responder tarefa da {periodo}:

{marcacoes}
"""

    await app.bot.send_message(
        chat_id=GRUPO_ID,
        text=texto,
        parse_mode="HTML"
    )

# =========================================
# CONFIRMAR TAREFA
# =========================================

async def verificar_tarefa(update, context):

    user_id = update.effective_user.id

    if user_id not in tarefas_pendentes:
        return False

    texto = update.message.text.lower()

    respostas_ok = [

        "feito",
        "concluido",
        "concluído",
        "ok",
        "terminei",
        "pronto",
        "finalizado",
        "finalizei",
    ]

    confirmou = any(
        palavra in texto
        for palavra in respostas_ok
    )

    if not confirmou:
        return False

    periodo = tarefas_pendentes[user_id]

    del tarefas_pendentes[user_id]

    nome = update.effective_user.first_name

    await update.message.reply_text(
        f"✅ Tarefa da {periodo} confirmada!"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"📌 {nome} concluiu "
            f"a tarefa da {periodo}."
        )
    )

    return True

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

        # =================================
        # CONFIRMAR TAREFA
        # =================================

        concluiu = await verificar_tarefa(
            update,
            context
        )

        if concluiu:
            return

        # =================================
        # IA NO GRUPO
        # =================================

        responder_ia = False

        # PRIVADO

        if update.effective_chat.type == "private":

            responder_ia = True

        # GRUPO

        else:

            if (
                "ia" in mensagem.lower()
                or "bot" in mensagem.lower()
            ):

                responder_ia = True

        if not responder_ia:
            return

        # =================================
        # ANTI FLOOD
        # =================================

        agora = time.time()

        if user_id in ultimo_tempo:

            diferenca = (
                agora - ultimo_tempo[user_id]
            )

            if diferenca < 1.5:

                await update.message.reply_text(
                    "⏳ Aguarde..."
                )

                return

        ultimo_tempo[user_id] = agora

        # =================================
        # DIGITANDO
        # =================================

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING
        )

        # =================================
        # MEMÓRIA
        # =================================

        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {mensagem}"
        )

        memoria[user_id] = (
            memoria[user_id][-MAX_MSG:]
        )

        historico = "\n".join(
            memoria[user_id]
        )

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
                "max_output_tokens": 1200,
            }
        )

        texto = resposta.text.strip()

        memoria[user_id].append(
            f"IA: {texto}"
        )

        await asyncio.sleep(
            random.uniform(1, 2)
        )

        limite = 3500

        partes = [
            texto[i:i + limite]
            for i in range(
                0,
                len(texto),
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
        BotCommand("status", "Ver status"),
        BotCommand("addfuncionario", "Adicionar funcionário"),
        BotCommand("removerfuncionario", "Remover funcionário"),
        BotCommand("listar", "Listar funcionários"),
        BotCommand("horario", "Definir horário"),
        BotCommand("tarefa", "Definir tarefa"),
        BotCommand("ligar", "Ativar"),
        BotCommand("desligar", "Desativar"),
    ]

    await app.bot.set_my_commands(
        comandos
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("status", status)
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
            "horario",
            horario
        )
    )

    app.add_handler(
        CommandHandler(
            "tarefa",
            tarefa
        )
    )

    app.add_handler(
        CommandHandler(
            "ligar",
            ligar
        )
    )

    app.add_handler(
        CommandHandler(
            "desligar",
            desligar
        )
    )

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
        kwargs={"app": app}
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
