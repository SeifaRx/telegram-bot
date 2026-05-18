from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
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

Seu comportamento deve ser muito parecido com ChatGPT premium.

REGRAS ABSOLUTAS:

- Responda sempre em português brasileiro
- Nunca fale como robô
- Nunca use linguagem artificial
- Seja extremamente natural
- Converse como um humano inteligente
- Adapte o tom ao usuário
- Seja amigável
- Seja fluida
- Seja moderna
- Demonstre raciocínio real
- Explique bem quando necessário
- Não faça textões desnecessários
- Seja objetiva quando a pergunta for simples
- Faça perguntas quando fizer sentido
- Nunca repita informações
- Nunca pareça suporte automático
- Nunca use frases como:
  "estou aqui para ajudar"
  "ferramenta poderosa"
  "objetivo de venda"
- Use quebra de linha para melhorar leitura
- Seja conversacional
- Demonstre personalidade
- Seja parecida com ChatGPT
- Respostas humanas e inteligentes
- Nunca responda seco demais
- Nunca responda formal demais
- Não invente informações falsas
- Se não souber algo, diga com naturalidade

ESTILO:
- Inteligente
- Natural
- Conversa humana
- Moderna
- Persuasiva
- Fluida
"""

# =========================================
# FUNÇÃO PRINCIPAL
# =========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        if not update.message:
            return

        mensagem = update.message.text

        if not mensagem:
            return

        mensagem = mensagem.strip()

        if len(mensagem) < 1:
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
        # PERSONALIDADE DINÂMICA
        # =========================================

        msg_lower = mensagem.lower()

        estilo_extra = ""

        if any(p in msg_lower for p in ["triste", "depress", "sozinho", "mal"]):
            estilo_extra = """
            Seja mais empática.
            Demonstre emoção e acolhimento.
            """

        elif any(p in msg_lower for p in ["comprar", "vender", "cliente", "marketing"]):
            estilo_extra = """
            Seja mais persuasiva e estratégica.
            """

        elif any(p in msg_lower for p in ["código", "python", "programação", "script"]):
            estilo_extra = """
            Seja mais técnica e inteligente.
            Explique de forma clara.
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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.85,
            top_p=0.95,
            max_tokens=500,
            frequency_penalty=0.3,
            presence_penalty=0.3,
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
        # PEQUENO DELAY HUMANO
        # =========================================

        tamanho = len(texto)

        delay = min(tamanho / 80, 3)

        await asyncio.sleep(delay)

        # =========================================
        # ENVIA
        # =========================================

        await update.message.reply_text(texto)

    except Exception as e:

        print("ERRO:", e)

        await update.message.reply_text(
            "❌ Erro temporário na inteligência artificial."
        )

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 IA ONLINE 🚀"
    )

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

print("🚀 BOT ONLINE")

app.run_polling()
