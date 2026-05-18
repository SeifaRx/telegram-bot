from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

from groq import Groq
import os

TOKEN = os.getenv("TOKEN")

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

memoria = {}

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    mensagem = update.message.text

    if user_id not in memoria:
        memoria[user_id] = []

    memoria[user_id].append(f"Usuário: {mensagem}")

    historico = "\n".join(memoria[user_id][-6:])

    prompt = f"""
Você é uma IA extremamente inteligente.

REGRAS:
- Responda sempre em português brasileiro
- Seja humana
- Seja natural
- Seja inteligente

CONVERSA:
{historico}
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
        max_tokens=200
    )

    texto = resposta.choices[0].message.content

    memoria[user_id].append(f"Bot: {texto}")

    await update.message.reply_text(texto)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT,
        responder
    )
)

print("🚀 BOT ONLINE")

app.run_polling()
