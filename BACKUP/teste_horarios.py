from datetime import datetime, timedelta
import random
import psycopg2
import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext, ContextTypes

active_chats = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_visao_bips.log", encoding="utf-8"),
    ],
)

def print(*args, **kwargs):
    logging.info(" ".join(map(str, args)))

def conexao_banco():
    conexao = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="fla1357912",
            port="5432"
        )
    return conexao


# def consulta_banco(chat_id):
#     try:
#         database = conexao_banco()
#         cursor = database.cursor()
#         cursor.execute('''SELECT HMSINI, HMSFIM
#                           FROM TLG_BIP
#                           WHERE COD_GRUPO = %s''',
#                           (chat_id,))
#         tlg_bip_horarios = cursor.fetchone()
#         if tlg_bip_horarios:
#             formato_hora = '%H:%M:%S'
#             inicio = datetime.strptime(tlg_bip_horarios[0].strip(), formato_hora)
#             fim = datetime.strptime(tlg_bip_horarios[1].strip(), formato_hora)
#             print(f"Hora de início: {inicio.time()} // Hora de fim: {fim.time()}")
#             return inicio, fim
#         else:
#             print("Nenhum horário encontrado no banco.")
#             return None, None
#     except Exception as e:
#         print(f"Erro ao buscar horários no banco: {e}")
#         return None, None
    
# chat_id = -2490922945
# consulta_banco(chat_id)

def teste():
    try:
        database = conexao_banco()
        cursor = database.cursor()
    except Exception as e:
        print(f"Erro ao buscar horários no banco: {e}")
    