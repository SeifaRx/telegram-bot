from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

from groq import Groq
import os

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(
    api_key=GROQ_API_KEY
)

# =========================
# MEMÓRIA
# =========================

memoria = {}

MAX_MSG = 10

# =========================
# RESPOSTA
# =========================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        mensagem = update.message.text

        if not mensagem:
            return

        user_id = update.message.from_user.id

        # cria memória
        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(f"Usuário: {mensagem}")

        # limita memória
        memoria[user_id] = memoria[user_id][-MAX_MSG:]

        historico = "\n".join(memoria[user_id])

        # prompt inteligente
        prompt = f"""
Você é uma inteligência artificial extremamente inteligente, rápida e natural.

REGRAS:
- Responda sempre em português brasileiro
- Seja humana e amigável
- Nunca responda em inglês
- Dê respostas completas
- Nunca corte respostas no meio
- Explique muito bem
- Seja inteligente e detalhada
- Continue escrevendo até finalizar completamente
- Responda como ChatGPT premium
- Seja natural em conversas

CONVERSA:
{historico}

RESPOSTA:
"""

        resposta = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1200
        )

        texto = resposta.choices[0].message.content

        # salva resposta
        memoria[user_id].append(f"Bot: {texto}")

        # divide mensagens grandes
        partes = [texto[i:i+4000] for i in range(0, len(texto), 4000)]

        for parte in partes:
            await update.message.reply_text(parte)

    except Exception as e:

        print("ERRO:", e)

        await update.message.reply_text(
            "❌ Erro temporário na IA."
        )

# =========================
# APP
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

print("🚀 BOT ONLINE")

app.run_polling()
