
import logging
import psycopg2
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


async def conexao_banco():
    conexao = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="fla1357912",
            port="5432"
        )
    return conexao

user_codes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_codes[chat_id] = "" 
    mensagem = 'Digite um código!'
    mesagem_formatada = f'<b>{mensagem}</b>'
    await update.message.reply_text(mesagem_formatada, reply_markup=generate_keyboard(chat_id), parse_mode="HTML")

def generate_keyboard(chat_id):
    code = user_codes.get(chat_id, "")
    keyboard = [
        [InlineKeyboardButton("1", callback_data="1"), InlineKeyboardButton("2", callback_data="2"), InlineKeyboardButton("3", callback_data="3")],
        [InlineKeyboardButton("4", callback_data="4"), InlineKeyboardButton("5", callback_data="5"), InlineKeyboardButton("6", callback_data="6")],
        [InlineKeyboardButton("7", callback_data="7"), InlineKeyboardButton("8", callback_data="8"), InlineKeyboardButton("9", callback_data="9")],
        [InlineKeyboardButton("0", callback_data="0"), InlineKeyboardButton("← Apagar", callback_data="apagar")],
        [InlineKeyboardButton("✔ Enviar", callback_data="enviar")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data

    if chat_id not in user_codes:
        user_codes[chat_id] = ""

    if data.isdigit():  
        user_codes[chat_id] += data
    elif data == "apagar": 
        user_codes[chat_id] = user_codes[chat_id][:-1]
    elif data == "enviar":  
        code = user_codes[chat_id]
        codigo = await consulta_funcionario(code)
        if codigo:

            resposta = f"O código {code} existe no banco de dados. Obrigado, {codigo[0]}"
        else:
            resposta = f"O código {code} não existe no banco de dados."

        await query.message.reply_text(resposta)
        user_codes[chat_id] = ""  
        return

    if user_codes[chat_id]:
        code = user_codes[chat_id]
    else:
        code = "Digite um código:"

    code_display = f"🔢 Código: {code}\u200b"
    await query.message.edit_text(code_display, reply_markup=generate_keyboard(chat_id))

async def consulta_funcionario(code):
    try:
        database = await conexao_banco()
        cursor = database.cursor()
        cursor.execute("SELECT NAME FROM USERS WHERE CODE = %s LIMIT 1;", (code,))
        codigo = cursor.fetchone() 
        cursor.close()
        database.close()
        return codigo
    except Exception as e:
        print(f"Erro ao consultar o banco: {e}")

def main():
    conexao_api = Application.builder().token("8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc").build()
    conexao_api.add_handler(CallbackQueryHandler(button_handler))
    conexao_api.add_handler(CommandHandler('start', start))
    
    print("Bot iniciado...")
    conexao_api.run_polling()

if __name__ == "__main__":
    main()
