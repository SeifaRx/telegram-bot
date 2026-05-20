# ==================================================
# IMPORTS
# ==================================================

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
import random
import time

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

    model_name="gemini-2.5-flash",

    system_instruction="""
Você é uma inteligência artificial extremamente inteligente,
natural e moderna.

Seu comportamento deve ser parecido com ChatGPT premium.

REGRAS IMPORTANTES:

- Responda sempre em português brasileiro
- Nunca responda em inglês
- Seja extremamente inteligente
- Entenda contexto
- Seja humana
- Seja natural
- Evite respostas robóticas
- Responda curto quando possível
- Explique detalhadamente quando necessário
- Nunca faça textões desnecessários
- Organize respostas
- Use listas quando necessário
- Use emojis apenas quando fizer sentido
- Nunca corte frases
- Nunca deixe respostas incompletas
- Seja útil
- Seja persuasiva quando necessário
- Seja criativa
- Seja rápida
- Seja parecida com ChatGPT
- Sempre adapte o tamanho da resposta ao contexto
- Se a pergunta for simples, responda curto
- Se a pergunta exigir detalhes, explique melhor

FORMATAÇÃO:

- Organize respostas
- Use espaços entre tópicos
- Evite blocos gigantes
- Use:

1.
2.
3.

quando fizer sentido.
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

MAX_MEMORIA = 20

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
# BLOQUEAR GRUPO
# ==================================================

async def bloquear_grupo(update):

    if update.effective_chat.id == GRUPO_ID:

        await update.message.reply_text(
            "❌ Use comandos no privado."
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

/manha tarefa

/tarde tarefa

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
            f"✅ {nome} adicionado."
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

    horario_manha = context.args[0]

    await update.message.reply_text(
        f"✅ Horário manhã: {horario_manha}"
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
        f"✅ Horário tarde: {horario_tarde}"
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

    for funcionario in funcionarios:

        user_id = funcionario[0]

        nome = funcionario[1]

        tarefas_pendentes[user_id] = {

            "periodo": periodo,
            "tarefa": tarefa,
            "data": agora.strftime("%Y-%m-%d")
        }

        texto = f"""
📋 {periodo}

👤 <a href="tg://user?id={user_id}">{nome}</a>

📝 TAREFA:
{tarefa}

✅ Responda:
- feito
- ok
- concluído
- pronto
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

        # ==================================================
        # ANTI FLOOD
        # ==================================================

        agora = time.time()

        if user_id in ultimo_uso:

            if agora - ultimo_uso[user_id] < 2:

                return

        ultimo_uso[user_id] = agora

        # ==================================================
        # CONFIRMAÇÃO
        # ==================================================

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

        # ==================================================
        # IA NO GRUPO
        # ==================================================

        ativar_ia = False

        if chat_id == GRUPO_ID:

            if (
                update.message.reply_to_message
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

            return

        # ==================================================
        # DIGITANDO
        # ==================================================

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING
        )

        # ==================================================
        # MEMÓRIA
        # ==================================================

        if user_id not in memoria:

            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {texto}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MEMORIA:]

        contexto = """

Resumo da conversa:
"""

        for item in memoria[user_id][-8:]:

            contexto += f"\n{item}"

        prompt = f"""
{contexto}

Mensagem atual:
{texto}

Responda da melhor forma possível.
"""

        # ==================================================
        # GEMINI
        # ==================================================

        resposta = model.generate_content(

            prompt,

            generation_config={

                "temperature": 0.9,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
        )

        if not resposta.candidates:

            await update.message.reply_text(
                "❌ Não consegui responder."
            )

            return

        partes_resposta = []

        for candidate in resposta.candidates:

            if candidate.content.parts:

                for part in candidate.content.parts:

                    if hasattr(part, "text"):

                        partes_resposta.append(
                            part.text
                        )

        resposta_texto = "\n".join(
            partes_resposta
        ).strip()

        if not resposta_texto:

            resposta_texto = (
                "❌ Resposta vazia."
            )

        memoria[user_id].append(
            f"IA: {resposta_texto}"
        )

        # ==================================================
        # DELAY HUMANO
        # ==================================================

        await asyncio.sleep(
            min(
                len(resposta_texto) / 120,
                4
            )
        )

        # ==================================================
        # DIVIDIR
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

    app.add_handler(CommandHandler("start", start))
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

# ==================================================
# START
# ==================================================

if __name__ == "__main__":

    asyncio.run(main())
