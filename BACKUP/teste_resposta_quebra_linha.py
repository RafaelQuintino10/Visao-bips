from datetime import datetime, timedelta
import random
import psycopg2
import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext, ContextTypes, CommandHandler



async def teste(update: Update,  context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envio teste!")


async def handle (update: Update,  context: CallbackContext):
    resposta = update.message.text
    print(resposta)
    if ' ' in resposta or '\n' in resposta:
         await update.message.reply_text("Erro! Envie o código sem espaços ou quebra de linha!")
    else:
         await update.message.reply_text("Confirmado!")
def main() -> None:


    try:
        conexao_api = Application.builder().token("8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc").build()
        #Token bot visão bips
        # conexao_api = Application.builder().token("8092812812:AAFKtbKrUh1c1Rj0S1_LQ3EJWd-Rzgs_3Ps").build()
        conexao_api.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
        conexao_api.add_handler(CommandHandler('start', teste))

        # conexao_api.job_queue.run_once(restaurar_monitoramento, when=2)
        print("Iniciando o monitoramento...")
        conexao_api.run_polling()
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")

if __name__ == '__main__':
    main()
