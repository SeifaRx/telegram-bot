from telegram import Update, BotCommand
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
import sqlite3
import random
import logging
import time

from datetime import datetime

# =========================================
# LOGS
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================
# VARIÁVEIS
# =========================================

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# COLOQUE SEU ID DO TELEGRAM
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

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite"
)

# =========================================
# SQLITE
# =========================================

conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    user_id INTEGER PRIMARY KEY,
    nome TEXT,
    mensagens INTEGER DEFAULT 0,
    modo TEXT DEFAULT 'normal',
    criado_em TEXT
)
""")

conn.commit()

# =========================================
# MEMÓRIA
# =========================================

memoria = {}

MAX_MSG = 6

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
# ANTI SPAM
# =========================================

ultimo_tempo = {}

TEMPO_MINIMO = 1.5

# =========================================
# SYSTEM PROMPT
# =========================================

SYSTEM_PROMPT = """
Você é uma inteligência artificial extremamente inteligente, natural e organizada.

REGRAS IMPORTANTES:

- Responda sempre em português brasileiro
- Fale como uma pessoa real
- Nunca fale como robô
- Seja parecida com ChatGPT
- Seja inteligente e útil
- Entenda o contexto da conversa

ESTILO DAS RESPOSTAS:

- Se a pergunta for simples:
responda curto e direto

- Se a pergunta precisar:
explique mais detalhadamente

- Nunca faça textões desnecessários
- Nunca enrole
- Seja objetiva quando possível
- Seja detalhada quando necessário

ORGANIZAÇÃO:

- Organize respostas visualmente
- Use espaços entre tópicos
- Use listas quando fizer sentido
- Use:
1.
2.
3.

- Separe informações importantes
- Deixe fácil de ler
- Não mande tudo em um bloco gigante

EMOJIS:

- Pode usar emojis quando combinar
- Não exagere
- Use para melhorar visualmente

EXEMPLOS DE FORMATAÇÃO:

✅ Correto:

📌 Opções:

1. Primeira opção

2. Segunda opção

3. Terceira opção

❌ Errado:
texto gigante sem espaço e sem organização

PERSONALIDADE:

- Seja amigável
- Seja moderna
- Demonstre personalidade
- Varie as respostas
- Não repita frases
- Converse naturalmente

IMPORTANTE:

- Se o usuário pedir algo rápido:
responda rápido

- Se pedir explicação:
explique muito bem

- Adapte o tamanho da resposta automaticamente
"""

# =========================================
# ADMIN
# =========================================

def eh_admin(user_id):

    return user_id == ADMIN_ID

# =========================================
# DATABASE
# =========================================

def criar_usuario(user_id, nome):

    cursor.execute(
        "SELECT * FROM usuarios WHERE user_id=?",
        (user_id,)
    )

    usuario = cursor.fetchone()

    if not usuario:

        cursor.execute("""
        INSERT INTO usuarios
        (user_id, nome, mensagens, criado_em)
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            nome,
            0,
            str(datetime.now())
        ))

        conn.commit()

def adicionar_msg(user_id):

    cursor.execute("""
    UPDATE usuarios
    SET mensagens = mensagens + 1
    WHERE user_id=?
    """, (user_id,))

    conn.commit()

def pegar_modo(user_id):

    cursor.execute("""
    SELECT modo FROM usuarios
    WHERE user_id=?
    """, (user_id,))

    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    return "normal"

# =========================================
# COMANDOS TELEGRAM
# =========================================

async def configurar_comandos(app):

    comandos = [

        BotCommand("start", "Iniciar bot"),

        BotCommand("comandos", "Ver comandos"),

        BotCommand("limites", "Ver limites da IA"),

        BotCommand("stats", "Ver estatísticas"),

        BotCommand("perfil", "Seu perfil"),

        BotCommand("limpar", "Limpar memória"),

        BotCommand("modo", "Alterar modo"),

        BotCommand("ping", "Status do bot"),
    ]

    await app.bot.set_my_commands(comandos)

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto = """
🤖 IA ONLINE 🚀

📌 COMANDOS:

/comandos
/limites
/stats
/perfil
/limpar
/modo
/ping

💬 Converse normalmente com a IA.
"""

    await update.message.reply_text(texto)

# =========================================
# COMANDOS
# =========================================

async def comandos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto = """
📌 COMANDOS DISPONÍVEIS

/start → iniciar bot

/comandos → ver comandos

/limites → uso da IA

/stats → estatísticas

/perfil → seu perfil

/limpar → limpar memória

/modo normal

/modo coach

/modo engraçado

/modo frio

/ping → status do bot
"""

    await update.message.reply_text(texto)

# =========================================
# PING
# =========================================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    await update.message.reply_text(
        "🟢 BOT ONLINE"
    )

# =========================================
# LIMITES
# =========================================

async def limites(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    texto = f"""
📊 USO DA IA

💬 Mensagens hoje:
{TOTAL_MSG}

⚠️ Primeiro alerta:
{ALERTA_1}

🚨 Segundo alerta:
{ALERTA_2}
"""

    await update.message.reply_text(texto)

# =========================================
# STATS
# =========================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    cursor.execute(
        "SELECT COUNT(*) FROM usuarios"
    )

    usuarios = cursor.fetchone()[0]

    texto = f"""
📈 ESTATÍSTICAS

👥 Usuários:
{usuarios}

💬 Mensagens hoje:
{TOTAL_MSG}
"""

    await update.message.reply_text(texto)

# =========================================
# PERFIL
# =========================================

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    user_id = update.message.from_user.id

    cursor.execute("""
    SELECT nome, mensagens, modo, criado_em
    FROM usuarios
    WHERE user_id=?
    """, (user_id,))

    usuario = cursor.fetchone()

    if not usuario:
        return

    texto = f"""
👤 PERFIL

📛 Nome:
{usuario[0]}

💬 Mensagens:
{usuario[1]}

🎭 Modo:
{usuario[2]}

📅 Criado em:
{usuario[3]}
"""

    await update.message.reply_text(texto)

# =========================================
# LIMPAR MEMÓRIA
# =========================================

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    user_id = update.message.from_user.id

    memoria[user_id] = []

    await update.message.reply_text(
        "🧠 Memória limpa com sucesso."
    )

# =========================================
# MODOS
# =========================================

async def modo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not eh_admin(update.message.from_user.id):
        return

    user_id = update.message.from_user.id

    args = context.args

    if not args:

        await update.message.reply_text(
            """
🎭 MODOS DISPONÍVEIS

/modo normal

/modo coach

/modo engraçado

/modo frio
"""
        )

        return

    novo_modo = args[0].lower()

    modos_validos = [
        "normal",
        "coach",
        "engraçado",
        "frio"
    ]

    if novo_modo not in modos_validos:

        await update.message.reply_text(
            "❌ Modo inválido."
        )

        return

    cursor.execute("""
    UPDATE usuarios
    SET modo=?
    WHERE user_id=?
    """, (
        novo_modo,
        user_id
    ))

    conn.commit()

    await update.message.reply_text(
        f"✅ Modo alterado para: {novo_modo}"
    )

# =========================================
# IA
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

        user = update.message.from_user

        user_id = user.id

        nome = user.first_name

        # =========================================
        # PRIVADO
        # =========================================

        chat_type = update.message.chat.type

        if chat_type == "private":

            if not eh_admin(user_id):

                await update.message.reply_text(
                    "❌ Você não tem acesso a este bot."
                )

                return

        # =========================================
        # ANTI SPAM
        # =========================================

        agora = time.time()

        if user_id in ultimo_tempo:

            diferenca = agora - ultimo_tempo[user_id]

            if diferenca < TEMPO_MINIMO:

                await update.message.reply_text(
                    "⏳ Aguarde um momento."
                )

                return

        ultimo_tempo[user_id] = agora

        # =========================================
        # RESET DIÁRIO
        # =========================================

        dia_atual = datetime.now().day

        if dia_atual != ULTIMO_DIA:

            TOTAL_MSG = 0

            alerta_1_enviado = False
            alerta_2_enviado = False

            ULTIMO_DIA = dia_atual

        TOTAL_MSG += 1

        # =========================================
        # ALERTAS
        # =========================================

        if TOTAL_MSG >= ALERTA_1 and not alerta_1_enviado:

            alerta_1_enviado = True

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ O limite da IA está chegando perto."
            )

        if TOTAL_MSG >= ALERTA_2 and not alerta_2_enviado:

            alerta_2_enviado = True

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="🚨 O limite da IA está quase acabando."
            )

        # =========================================
        # DATABASE
        # =========================================

        criar_usuario(user_id, nome)

        adicionar_msg(user_id)

        # =========================================
        # DIGITANDO
        # =========================================

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )

        # =========================================
        # MEMÓRIA
        # =========================================

        if user_id not in memoria:
            memoria[user_id] = []

        memoria[user_id].append(
            f"Usuário: {mensagem}"
        )

        memoria[user_id] = memoria[user_id][-MAX_MSG:]

        historico = "\n".join(memoria[user_id])

        # =========================================
        # MODO
        # =========================================

        modo_usuario = pegar_modo(user_id)

        estilo = ""

        if modo_usuario == "coach":
            estilo = "Seja motivadora, estratégica e inspiradora."

        elif modo_usuario == "engraçado":
            estilo = "Seja divertida, descontraída e levemente engraçada."

        elif modo_usuario == "frio":
            estilo = "Seja objetiva, curta e direta."

        else:
            estilo = "Seja natural e inteligente."

        # =========================================
        # PROMPT
        # =========================================

        prompt = f"""
{SYSTEM_PROMPT}

ESTILO:
{estilo}

CONVERSA:
{historico}

IA:
"""

        # =========================================
        # GEMINI
        # =========================================

        resposta = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 250,
            }
        )

        texto = resposta.text.strip()

        texto = texto[:3000]

        memoria[user_id].append(
            f"IA: {texto}"
        )

        # =========================================
        # DELAY HUMANO
        # =========================================

        delay = random.uniform(
            0.8,
            1.8
        )

        await asyncio.sleep(delay)

        # =========================================
        # ENVIA
        # =========================================

        await update.message.reply_text(texto)

    except Exception as e:

        logging.error(str(e))

        await update.message.reply_text(
            "❌ Erro temporário na IA."
        )

# =========================================
# MAIN
# =========================================

async def main():

    app = ApplicationBuilder().token(TOKEN).build()

    await configurar_comandos(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("comandos", comandos))
    app.add_handler(CommandHandler("limites", limites))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("modo", modo))
    app.add_handler(CommandHandler("ping", ping))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    print("🚀 BOT ONLINE")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

# =========================================
# START
# =========================================

asyncio.run(main())
