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

# =========================================
# VARIÁVEIS
# =========================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# =========================================
# MEMÓRIA
# =========================================

memoria = {}

MAX_MSG = 6

# =========================================
# SYSTEM PROMPT
# =========================================

SYSTEM_PROMPT = """
Você é uma inteligência artificial extremamente inteligente, natural e humana.

REGRAS:
- Responda sempre em português brasileiro
- Nunca fale como robô
- Seja parecida com ChatGPT
- Converse naturalmente
- Seja inteligente
- Seja amigável
- Demonstre personalidade
- Não faça textões enormes
- Explique bem quando necessário
- Seja moderna
- Use quebra de linha
- Não repita informações
- Seja fluida
- Faça perguntas quando fizer sentido

ESTILO:
- Natural
- Moderna
- Conversa humana
- Inteligente
"""

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 IA ONLINE 🚀"
    )

# =========================================
# RESPOSTA
# =========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        mensagem = update.message.text.strip()

        if not mensagem:
            return

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
                "temperature": 0.8,
                "max_output_tokens": 150,
            }
        )

        texto = resposta.text.strip()

        texto = texto[:1500]

        # salva resposta
        memoria[user_id].append(
            f"IA: {texto}"
        )

        # delay humano
        delay = min(len(texto) / 100, 2)

        await asyncio.sleep(delay)

        # envia
        await update.message.reply_text(texto)

    except Exception as e:

        print("ERRO:", str(e))

        await update.message.reply_text(
            f"❌ Erro:\n{str(e)}"
        )

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

print("🚀 BOT ONLINE")

app.run_polling()
