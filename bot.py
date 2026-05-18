from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from telegram.constants import ChatAction

import google.generativeai as genai

import os
import asyncio
from datetime import datetime

# =========================================
# VARIÁVEIS
# =========================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# SEU ID TELEGRAM
ADMIN_ID = 5651378630

# =========================================
# VERIFICAÇÕES
# =========================================

if not TOKEN:
    raise Exception("TOKEN não encontrada.")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY não encontrada.")

# =========================================
# GEMINI
# =========================================

genai.configure(api_key=GEMINI_API_KEY)

# modelo mais econômico
model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# =========================================
# MEMÓRIA
# =========================================

memoria = {}

MAX_MSG = 4

# =========================================
# CONTROLE
# =========================================

TOTAL_MSG = 0

ALERTA_1 = 600
ALERTA_2 = 850

alerta_1_enviado = False
alerta_2_enviado = False

ULTIMO_DIA = datetime.now().day

# =========================================
# SYSTEM PROMPT
# =========================================

SYSTEM_PROMPT = """
Você é uma inteligência artificial extremamente inteligente e natural.

REGRAS:
- Responda em português brasileiro
- Seja humana
- Nunca fale como robô
- Seja parecida com ChatGPT
- Converse naturalmente
- Seja inteligente
- Seja amigável
- Não faça textões
- Explique bem quando necessário
- Use quebra de linha
- Seja moderna
- Demonstre personalidade
- Não repita informações
- Faça perguntas quando fizer sentido
"""

# =========================================
# /START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
🤖 IA ONLINE 🚀

COMANDOS DISPONÍVEIS:

/start → iniciar bot
/comandos → lista de comandos
/limites → ver uso atual da IA
/resetar → resetar contador manualmente

Só mandar mensagem normalmente para conversar com a IA.
"""

    await update.message.reply_text(texto)

# =========================================
# /COMANDOS
# =========================================

async def comandos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
📌 COMANDOS:

/start → iniciar bot

/comandos → mostrar comandos

/limites → mostrar uso atual da IA

/resetar → resetar contador manualmente
"""

    await update.message.reply_text(texto)

# =========================================
# /LIMITES
# =========================================

async def limites(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global TOTAL_MSG

    restante_1 = ALERTA_1 - TOTAL_MSG
    restante_2 = ALERTA_2 - TOTAL_MSG

    texto = f"""
📊 STATUS DA IA

Mensagens usadas hoje:
{TOTAL_MSG}

⚠️ Primeiro alerta:
{ALERTA_1}

🚨 Segundo alerta:
{ALERTA_2}

📉 Faltam para alerta 1:
{restante_1}

📉 Faltam para alerta 2:
{restante_2}
"""

    await update.message.reply_text(texto)

# =========================================
# /RESETAR
# =========================================

async def resetar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global TOTAL_MSG
    global alerta_1_enviado
    global alerta_2_enviado

    # somente admin
    if update.message.from_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Apenas admin."
        )

        return

    TOTAL_MSG = 0

    alerta_1_enviado = False
    alerta_2_enviado = False

    await update.message.reply_text(
        "✅ Contador resetado."
    )

# =========================================
# RESPOSTA IA
# =========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global TOTAL_MSG
    global ULTIMO_DIA
    global alerta_1_enviado
    global alerta_2_enviado

    try:

        if not update.message:
            return

        mensagem = update.message.text.strip()

        if not mensagem:
            return

        # =========================================
        # RESET DIÁRIO
        # =========================================

        dia_atual = datetime.now().day

        if dia_atual != ULTIMO_DIA:

            TOTAL_MSG = 0

            alerta_1_enviado = False
            alerta_2_enviado = False

            ULTIMO_DIA = dia_atual

        # =========================================
        # CONTADOR
        # =========================================

        TOTAL_MSG += 1

        # =========================================
        # ALERTAS ADMIN
        # =========================================

        if TOTAL_MSG >= ALERTA_1 and not alerta_1_enviado:

            alerta_1_enviado = True

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ O bot já usou bastante limite da IA."
            )

        if TOTAL_MSG >= ALERTA_2 and not alerta_2_enviado:

            alerta_2_enviado = True

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="🚨 ATENÇÃO: limite da IA está quase acabando."
            )

        user_id = update.message.from_user.id

        # digitando
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )

        # memória
        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {mensagem}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MSG:]

        # histórico
        historico = "\n".join(memoria[user_id])

        prompt = f"""
{SYSTEM_PROMPT}

CONVERSA:
{historico}

IA:
"""

        # IA
        resposta = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 100,
            }
        )

        texto = resposta.text.strip()

        texto = texto[:1000]

        memoria[user_id].append(
            f"IA: {texto}"
        )

        # delay humano
        delay = min(len(texto) / 120, 1.5)

        await asyncio.sleep(delay)

        # envia
        await update.message.reply_text(texto)

    except Exception as e:

        print("ERRO:", str(e))

        await update.message.reply_text(
            "❌ Erro temporário na IA."
        )

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("comandos", comandos)
)

app.add_handler(
    CommandHandler("limites", limites)
)

app.add_handler(
    CommandHandler("resetar", resetar)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

print("🚀 BOT ONLINE")

app.run_polling()
