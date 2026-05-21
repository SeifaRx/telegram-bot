from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
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
import time
import re

from datetime import datetime
from zoneinfo import ZoneInfo

# ==================================================
# CONFIG
# ==================================================

TOKEN = os.getenv("TOKEN")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADMIN_IDS = [5651378630]

GRUPO_ID = -1002913144849

TIMEZONE = ZoneInfo("America/Sao_Paulo")

# ==================================================
# GEMINI
# ==================================================

genai.configure(
    api_key=GEMINI_API_KEY
)

model = genai.GenerativeModel(

    model_name="gemini-2.5-flash-lite",

    system_instruction="""
Você é uma inteligência artificial extremamente inteligente,
natural, moderna e organizada.

REGRAS:

- Responda sempre em português brasileiro
- Nunca fale inglês
- Seja natural
- Seja inteligente
- Seja parecida com ChatGPT
- Responda curto quando possível
- Explique melhor apenas quando necessário
- Nunca corte respostas
- Nunca deixe frases incompletas
- Não use markdown exagerado
- Não use:
#
##
###
***
- Organize respostas
- Use emojis apenas quando necessário
- Evite textos gigantes
- Evite respostas robóticas
- Use listas simples quando necessário

FORMATAÇÃO:

✅ CERTO:

📌 Opção 1
📌 Opção 2

1. Primeiro
2. Segundo

❌ ERRADO:

# TITULO
## SUBTITULO
*** TEXTO
"""
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
# MEMÓRIA
# ==================================================

memoria = {}

MAX_MEMORIA = 12

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

ultimo_uso = {}

# ==================================================
# FUNÇÕES
# ==================================================

def eh_admin(user_id):

    return user_id in ADMIN_IDS

# ==================================================
# LIMPAR TEXTO IA
# ==================================================

def limpar_texto(texto):

    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)

    texto = re.sub(r"#+", "", texto)

    texto = re.sub(r"`+", "", texto)

    texto = re.sub(r"\*", "•", texto)

    texto = re.sub(r"\n{3,}", "\n\n", texto)

    texto = texto.strip()

    return texto

# ==================================================
# DIVIDIR TEXTO
# ==================================================

def dividir_texto(texto, limite=3500):

    partes = []

    while len(texto) > limite:

        corte = texto.rfind("\n", 0, limite)

        if corte == -1:
            corte = texto.rfind(". ", 0, limite)

        if corte == -1:
            corte = limite

        partes.append(texto[:corte])

        texto = texto[corte:].strip()

    partes.append(texto)

    return partes

# ==================================================
# BLOQUEAR COMANDOS NO GRUPO
# ==================================================

async def bloquear_grupo(update):

    if update.effective_chat.id == GRUPO_ID:

        await update.message.reply_text(
            "❌ Use comandos apenas no privado do bot."
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
🤖 IA ONLINE 🚀

📌 COMANDOS

/addfuncionario ID Nome

/removerfuncionario ID

/listar

/manha tarefa da manhã

/tarde tarefa da tarde

/horario_manha 08:00

/horario_tarde 15:00

/limpar

/ping
"""

    await update.message.reply_text(texto)

# ==================================================
# LIMPAR MEMÓRIA
# ==================================================

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await bloquear_grupo(update):
        return

    user_id = update.effective_user.id

    if not eh_admin(user_id):
        return

    memoria[user_id] = []

    await update.message.reply_text(
        "🧠 Memória da IA limpa."
    )

# ==================================================
# PING
# ==================================================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    inicio = time.time()

    msg = await update.message.reply_text(
        "🏓 Verificando..."
    )

    fim = round(
        (time.time() - inicio) * 1000
    )

    await msg.edit_text(
        f"🏓 BOT ONLINE\n⚡ {fim}ms"
    )

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
# REMOVER
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
# MANHÃ
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
# TARDE
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

    try:

        horario_manha = context.args[0]

        await update.message.reply_text(
            f"✅ Horário manhã salvo: {horario_manha}"
        )

    except:

        await update.message.reply_text(
            "Use:\n/horario_manha 08:00"
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

    try:

        horario_tarde = context.args[0]

        await update.message.reply_text(
            f"✅ Horário tarde salvo: {horario_tarde}"
        )

    except:

        await update.message.reply_text(
            "Use:\n/horario_tarde 15:00"
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
            "data": agora.strftime("%Y-%m-%d")
        }

        texto += (
            f'👤 <a href="tg://user?id={user_id}">{nome}</a>\n'
        )

    texto += """

✅ Responda:
- ok
- feito
- concluído
"""

    try:

        await context.bot.send_message(
            chat_id=GRUPO_ID,
            text=texto,
            parse_mode="HTML"
        )

    except Exception as e:

        logging.error(e)

# ==================================================
# IA
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

        texto_lower = texto.lower().strip()

        agora = time.time()

        if user_id in ultimo_uso:

            if agora - ultimo_uso[user_id] < 1:
                return

        ultimo_uso[user_id] = agora

        palavras_confirmacao = [

            "feito",
            "ok",
            "pronto",
            "concluído",
            "concluido",
            "terminei",
            "finalizei",
        ]

        if user_id in tarefas_pendentes:

            confirmou = False

            for palavra in palavras_confirmacao:

                if palavra in texto_lower:

                    confirmou = True
                    break

            if confirmou:

                del tarefas_pendentes[user_id]

                await update.message.reply_text(
                    "✅ Tarefa confirmada."
                )

                return

        ativar_ia = False

        if chat_id == GRUPO_ID:

            if (
                "ia" in texto_lower
                or "bot" in texto_lower
                or update.message.reply_to_message
            ):

                ativar_ia = True

        else:

            ativar_ia = True

        if not ativar_ia:
            return

        if (
            update.effective_chat.type == "private"
            and not eh_admin(user_id)
        ):

            return

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING
        )

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
Você é uma IA extremamente inteligente e organizada.

REGRAS IMPORTANTES:

- Responda em português brasileiro
- Seja natural
- Seja moderna
- Seja inteligente
- Responda igual ChatGPT
- Evite markdown exagerado
- Não use:
#
##
###
***
- Organize bonito
- Use emojis apenas quando necessário
- Não faça textos gigantes
- Responda curto quando possível
- Responda longo apenas quando necessário
- Nunca corte respostas
- Não use símbolos exagerados
- Use listas simples quando precisar

FORMATAÇÃO CORRETA:

✅ Certo:

📌 Opção 1
📌 Opção 2

OU

1. Primeiro
2. Segundo

❌ Errado:

# TITULO
## SUBTITULO
*** TEXTO

CONVERSA:
{historico}

IA:
"""

        resposta = model.generate_content(

            prompt,

            generation_config={

                "temperature": 0.7,

                "top_p": 0.9,

                "top_k": 40,

                "max_output_tokens": 1400,
            }
        )

        resposta_texto = limpar_texto(
            resposta.text.strip()
        )

        memoria[user_id].append(
            f"IA: {resposta_texto}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MEMORIA:]

        partes = dividir_texto(
            resposta_texto
        )

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

        BotCommand(
            "limpar",
            "Limpar memória"
        ),

        BotCommand(
            "ping",
            "Ver ping"
        ),
    ]

    await app.bot.set_my_commands(
        comandos
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("limpar", limpar))

    app.add_handler(CommandHandler("ping", ping))

    app.add_handler(CommandHandler("addfuncionario", addfuncionario))

    app.add_handler(CommandHandler("removerfuncionario", removerfuncionario))

    app.add_handler(CommandHandler("listar", listar))

    app.add_handler(CommandHandler("manha", manha))

    app.add_handler(CommandHandler("tarde", tarde))

    app.add_handler(CommandHandler("horario_manha", horario_m))

    app.add_handler(CommandHandler("horario_tarde", horario_t))

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

if __name__ == "__main__":

    asyncio.run(main())
