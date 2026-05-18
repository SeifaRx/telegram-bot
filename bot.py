from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from telegram.constants import ChatAction

from groq import Groq

import os
import asyncio

# =========================================
# CONFIG
# =========================================

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# =========================================
# VERIFICA VARIÁVEIS
# =========================================

if not TOKEN:
    raise Exception("TOKEN do Telegram não encontrado.")

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY não encontrada.")

# =========================================
# CLIENTE GROQ
# =========================================

client = Groq(
    api_key=GROQ_API_KEY
)

# =========================================
# MEMÓRIA
# =========================================

memoria = {}

MAX_MSG = 20

# =========================================
# SYSTEM PROMPT
# =========================================

SYSTEM_PROMPT = """
Você é uma inteligência artificial extremamente avançada, inteligente e natural.

Seu comportamento deve ser parecido com ChatGPT.

REGRAS:

- Responda sempre em português brasileiro
- Nunca fale como robô
- Seja natural
- Seja humana
- Seja inteligente
- Converse como uma pessoa real
- Não faça textões desnecessários
- Explique bem quando necessário
- Seja objetiva quando precisar
- Use linguagem moderna
- Demonstre personalidade
- Seja amigável
- Nunca use frases artificiais
- Não pareça suporte automático
- Use quebra de linha para melhorar leitura
- Seja conversacional
- Faça perguntas quando fizer sentido
- Nunca repita informações
- Não invente informações falsas

ESTILO:
- Inteligente
- Moderna
- Natural
- Conversa humana
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

        mensagem = update.message.text

        if not mensagem:
            return

        mensagem = mensagem.strip()

        if mensagem == "":
            return

        user_id = update.message.from_user.id

        # =========================================
        # EFEITO DIGITANDO
        # =========================================

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )

        # =========================================
        # CRIA MEMÓRIA
        # =========================================

        if user_id not in memoria:
            memoria[user_id] = []

        # =========================================
        # SALVA USUÁRIO
        # =========================================

        memoria[user_id].append({
            "role": "user",
            "content": mensagem
        })

        # =========================================
        # LIMITA MEMÓRIA
        # =========================================

        memoria[user_id] = memoria[user_id][-MAX_MSG:]

        # =========================================
        # ESTILO DINÂMICO
        # =========================================

        mensagem_lower = mensagem.lower()

        estilo_extra = ""

        if any(p in mensagem_lower for p in ["triste", "sozinho", "mal", "depress"]):

            estilo_extra = """
            Seja mais empática e acolhedora.
            """

        elif any(p in mensagem_lower for p in ["vendas", "marketing", "cliente", "comprar"]):

            estilo_extra = """
            Seja mais persuasiva e estratégica.
            """

        elif any(p in mensagem_lower for p in ["python", "código", "script", "programação"]):

            estilo_extra = """
            Seja mais técnica e clara.
            """

        else:

            estilo_extra = """
            Seja natural e conversacional.
            """

        # =========================================
        # MONTA MENSAGENS
        # =========================================

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + estilo_extra
            }
        ]

        messages.extend(memoria[user_id])

        # =========================================
        # CHAMA IA
        # =========================================

        resposta = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            temperature=0.8,
            top_p=0.95,
            max_tokens=400,
        )

        texto = resposta.choices[0].message.content.strip()

        # =========================================
        # EVITA TEXTÃO
        # =========================================

        if len(texto) > 1500:
            texto = texto[:1500]

        # =========================================
        # SALVA RESPOSTA
        # =========================================

        memoria[user_id].append({
            "role": "assistant",
            "content": texto
        })

        # =========================================
        # DELAY HUMANO
        # =========================================

        delay = min(len(texto) / 100, 2)

        await asyncio.sleep(delay)

        # =========================================
        # ENVIA
        # =========================================

        await update.message.reply_text(texto)

    except Exception as e:

        print("ERRO COMPLETO:")
        print(str(e))

        await update.message.reply_text(
            f"❌ Erro na IA:\n{str(e)}"
        )

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(TOKEN).build()

# comando /start
app.add_handler(
    CommandHandler("start", start)
)

# mensagens
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

print("🚀 BOT ONLINE")

# =========================================
# INICIA BOT
# =========================================

app.run_polling()
