# BOT BIPs
# 12/02/25 - Implementação do teclado

from datetime import datetime, timedelta
import random
import psycopg2
import asyncio
import logging
import sys
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext, ContextTypes, CallbackQueryHandler

active_chats = {}
user_codes = {}

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


async def conexao_banco():
    conexao = psycopg2.connect(
        host="192.168.88.237",
        database='visao_ponto_db',
        user='postgres',
        password='QamN0*9yxe7!',
        port='5432'
    )
    return conexao 


ultima_hora_inicio = None
ultima_hora_fim = None
horarios = []
ultima_checagem = datetime.now()
codigofuncionario_posto = None
nomefuncionario_posto = None 
resposta_valida = False

async def gerar_horarios(inicio, fim, chat_name):
    print(f"Gerando horários aleatórios entre {inicio.time()} e {fim.time()}...")
    horarios = []
    try:
        if fim <= inicio:
            fim += timedelta(days=1)

        while inicio <= fim:
            horarios.append(inicio.strftime("%H:%M:%S"))
            inicio += timedelta(minutes=random.randint(15,25)) # INTERVALO DA ALEATORIEDADE DOS HORÁRIOS EM MINUTOS
    except Exception as e:
        print(f"Erro ao gerar horários: {e}")
    print(f"Horários gerados pro grupo {chat_name}: {horarios}")
    return horarios


async def consulta_banco(chat_id):
    try:
        database = await conexao_banco()
        cursor = database.cursor()
        cursor.execute('''SELECT HMSINI, HMSFIM
                          FROM TLG_BIP
                          WHERE COD_GRUPO = %s''',
                          (chat_id,))
        tlg_bip_horarios = cursor.fetchone()
        if tlg_bip_horarios:
            formato_hora = '%H:%M:%S'
            inicio = datetime.strptime(tlg_bip_horarios[0].strip(), formato_hora)
            fim = datetime.strptime(tlg_bip_horarios[1].strip(), formato_hora)
            print(f"Hora de início: {inicio.time()} // Hora de fim: {fim.time()}")
            return inicio, fim
        else:
            print("Nenhum horário encontrado no banco.")
            return None, None
    except Exception as e:
        print(f"Erro ao buscar horários no banco: {e}")
        return None, None

async def start_bot(chat_id, chat_name, context):
    global ultima_hora_inicio, ultima_hora_fim, horarios, ultima_checagem
    nova_hora_inicio, nova_hora_fim = await consulta_banco(chat_id)
    database = await conexao_banco()
    cursor = database.cursor()
    cursor.execute(''' 
            INSERT INTO TLG_GRUPOS (COD_GRUPO, NOMEGRUPO) 
            VALUES (%s, %s) ON CONFLICT (COD_GRUPO) DO NOTHING 
        ''', (chat_id, chat_name))
    
    database.commit()
    print(f'Conexão estabelecida com: {chat_name} // Chat id: {chat_id}')

    if nova_hora_inicio and nova_hora_fim:
        horarios = await gerar_horarios(nova_hora_inicio, nova_hora_fim, chat_name)
        ultima_hora_inicio, ultima_hora_fim = nova_hora_inicio, nova_hora_fim
    
    else:
        horarios = []  

    active_chats[chat_id] = {"horarios": horarios, "ultima_hora_inicio": nova_hora_inicio, "ultima_hora_fim": nova_hora_fim, "ultima_checagem": datetime.now()}

    cursor.execute('''SELECT * FROM TLG_BIP WHERE COD_GRUPO = %s ORDER BY HMSINI ASC LIMIT 1''', (chat_id,))
    tlg_bip_dados = cursor.fetchone()

    while True:
        agora = datetime.now()
        # print(f'Última checagem pro grupo {chat_name}: {active_chats[chat_id]['ultima_checagem']}')
        if (agora - active_chats[chat_id]['ultima_checagem']).total_seconds() > 120:
            print("Checando por atualizações no banco...")
            nova_hora_inicio, nova_hora_fim = await consulta_banco(chat_id)

            if nova_hora_inicio != active_chats[chat_id]['ultima_hora_inicio'] or nova_hora_fim != active_chats[chat_id]['ultima_hora_fim']:
                if nova_hora_inicio and nova_hora_fim:
                    print("Horários atualizados no banco. Gerando nova lista de horários...")
                    horarios = await gerar_horarios(nova_hora_inicio, nova_hora_fim, chat_name)
                    active_chats[chat_id]["horarios"] = horarios
                    active_chats[chat_id]["ultima_hora_inicio"] = nova_hora_inicio
                    active_chats[chat_id]["ultima_hora_fim"] = nova_hora_fim
                else:
                    print("Horários inválidos no banco. Tentando novamente em 10 minutos...")
            else:
                print("Nenhuma alteração nos horários detectada.")

            active_chats[chat_id]["ultima_checagem"] = agora

        if agora.strftime("%H:%M:%S") in active_chats[chat_id]['horarios']:
            print("Enviando mensagem: Por favor, retorne o BIP.")
            # await context.bot.send_message(chat_id=chat_id, text=tlg_bip_dados[6])
            keyboard = await generate_keyboard(chat_id)
            await context.bot.send_message(chat_id=chat_id ,text=tlg_bip_dados[6], reply_markup=keyboard)


            cursor.execute('''INSERT INTO TLG_BIPNOTIFIC (ID_BIP, COD_GRUPO, COD_SUPERVISAO, HORA_ENVIO) VALUES (%s, %s, %s, %s)''',(tlg_bip_dados[0], tlg_bip_dados[1], tlg_bip_dados[2], agora))
            database.commit()

            await asyncio.sleep(10*60) # TOLERÂNCIA DE RESPOSTA.
            cursor.execute('SELECT HORA_ENVIO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id,))
            hora_envio_explicita = cursor.fetchone()[0]
            print(hora_envio_explicita)

            cursor.execute('''SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1''',(chat_id,))

            resposta_func = cursor.fetchone()[4]
            print(f"Última resposta do funcionário: {resposta_func}")
            if resposta_func is not None:
                print('Resposta encontrada! Seguindo pro próximo horário...')

            else:
                data_atual = datetime.now().strftime("%Y-%m-%d")
                cursor.execute('SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s AND HORA_ENVIO >= %s AND HORA_RETORNO IS NOT NULL ORDER BY HORA_RETORNO DESC LIMIT 1',(chat_id,data_atual,))
                ultima_resposta = cursor.fetchone()
                if ultima_resposta is not None:
                    empr = ultima_resposta[4]
                    codfun = ultima_resposta[5]
                    hora_retorno = ultima_resposta[8]
                    if codfun is not None and empr is not None:
                        codigo = str(empr) + str(codfun)
                        print(codigo)
                    cursor.execute('SELECT NAME FROM PUBLIC.USER WHERE CODE = %s', (codigo,))
                    funcionario = cursor.fetchone()
                    if funcionario:
                        print(funcionario[0])
                        # msg_supervisao = f'Funcionário {funcionario[0]} no grupo {chat_name} não responde desde às {hora_retorno}!'
                        msg_supervisao = f'Perda de BIP: {funcionario[0]} no grupo {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                        await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                    else:
                        print(f"Sem resposta registrada desde às {hora_envio_explicita.time()}")
                        # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {hora_envio_explicita.time()}!'
                        msg_supervisao = f'Perda de BIP no grupo: {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                        await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)

                else:
                    print(f"Sem resposta registrada desde às {active_chats[chat_id]["ultima_hora_inicio"].time().strftime("%H:%M")}")
                    # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}!'
                    msg_supervisao = f'Perda de BIP no grupo: {chat_name}. Atenção! Por favor, verificar!'
                    await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
        else:
            print(f"Fora do horário: {agora.strftime("%H:%M:%S")}")
        await asyncio.sleep(1)

        if agora.strftime("%H:%M:%S") == active_chats[chat_id]["horarios"][-1]:
            print(f"Último horário para o grupo {chat_name}: {active_chats[chat_id]['horarios'][-1]}")
            novos_horarios = await gerar_horarios(active_chats[chat_id]["ultima_hora_inicio"], active_chats[chat_id]["ultima_hora_fim"], chat_name)
            active_chats[chat_id]["horarios"] = novos_horarios
            print(f"Nova lista de horários para o grupo {chat_name}: \n{novos_horarios}")

async def generate_keyboard(chat_id):
    code = user_codes.get(chat_id, "")
    keyboard = [
        [InlineKeyboardButton("1", callback_data="1"), InlineKeyboardButton("2", callback_data="2"), InlineKeyboardButton("3", callback_data="3")],
        [InlineKeyboardButton("4", callback_data="4"), InlineKeyboardButton("5", callback_data="5"), InlineKeyboardButton("6", callback_data="6")],
        [InlineKeyboardButton("7", callback_data="7"), InlineKeyboardButton("8", callback_data="8"), InlineKeyboardButton("9", callback_data="9")],
        [InlineKeyboardButton("0", callback_data="0"), InlineKeyboardButton("← Apagar", callback_data="apagar")],
        [InlineKeyboardButton("✔ Enviar", callback_data="enviar")]
    ]
    return InlineKeyboardMarkup(keyboard)



async def button_handler(update: Update, context: CallbackContext):
    global codigofuncionario_posto, nomefuncionario_posto, resposta_valida


    query = update.callback_query
    await query.answer()
    database = await conexao_banco()
    cursor = database.cursor()
    
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
            cod_empr = code[:3]
            cod_fun = code[3:]
            fun_timelog = datetime.now()
            print(f'Empresa: {cod_empr} // Funcionário: {cod_fun}')
            cursor.execute('''
           SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s  AND CODFUN IS NULL ORDER BY HORA_ENVIO DESC LIMIT 1
            ''', (chat_id,))
            ultimo_bip_enviado = cursor.fetchone()
            print(f'Último bip enviado: {ultimo_bip_enviado}')

            data_atual = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('SELECT HORA_RETORNO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s AND HORA_ENVIO >= %s  ORDER BY HORA_ENVIO DESC LIMIT 1',(chat_id,data_atual,))
            ultimo_bip_hora_retorno = cursor.fetchone()[0]
            print(f'Última hora retorno : {ultimo_bip_hora_retorno}')

            if ultimo_bip_hora_retorno is None:

                if ultimo_bip_enviado:
                    id_bip = ultimo_bip_enviado[1]
                    id_notifica = ultimo_bip_enviado[0]
                    try:
                        cursor.execute('SELECT NAME, CODE FROM PUBLIC.USER WHERE CODE =%s', (str(code),))
                        funcionario_codigo = cursor.fetchone()
                        print(f'Funcionário: {funcionario_codigo}')
                        if funcionario_codigo is not None:
                            if codigofuncionario_posto is None:
                                codigofuncionario_posto = code
                                nomefuncionario_posto = funcionario_codigo[0].split()[0]
                                reposta_valida = True
                            elif codigofuncionario_posto != code:
                                reposta_valida = False
                                resposta = "Código inválido! Digite o código correto..."
                                await  query.message.reply_text(chat_id=int(chat_id),text=resposta)
                            elif codigofuncionario_posto == code:
                                reposta_valida = True

                            if reposta_valida == True:
                                cursor.execute('''UPDATE TLG_BIPNOTIFIC SET EMPR = %s, CODFUN = %s, HORA_RETORNO = %s WHERE ID_BIP = %s AND ID_NOTIFICA = %s
                                ''', (cod_empr, cod_fun, fun_timelog, id_bip, id_notifica))

                                database.commit()
                                

                            if codigofuncionario_posto is not None and reposta_valida == True:
                                resposta = f"Obrigado {nomefuncionario_posto}, recebido!"
                                await query.message.reply_text(resposta)
                        else:
                            resposta = "Código inválido! Digite o código correto..."
                            keyboard = await generate_keyboard(chat_id)
                            await query.message.edit_text(resposta, reply_markup=keyboard)
                    except Exception as e:
                        print(f"Erro ao consultar tabela user: {e}")
                else:
                    resposta = "Nenhuma notificação encontrada para este grupo."
                    await query.message.reply_text(resposta)

            else:
                print('Retorno já registrado!')
        else:
            resposta = f"Código inválido! Tente novamente..."
            
            keyboard = await generate_keyboard(chat_id)
            await query.message.reply_text(resposta, reply_markup=keyboard)

        
        user_codes[chat_id] = ""  
        return

    if user_codes[chat_id]:
        code = user_codes[chat_id]
    else:
        code = "Digite um código:"

    code_display = f"🔢 Código: {code}\u200b"
    keyboard = await generate_keyboard(chat_id)
    await query.message.edit_text(code_display, reply_markup=keyboard)

async def consulta_funcionario(code):
    try:
        database = await conexao_banco()
        cursor = database.cursor()
        cursor.execute("SELECT NAME FROM PUBLIC.USER WHERE CODE = %s LIMIT 1;", (code,))
        codigo = cursor.fetchone() 
        cursor.close()
        database.close()
        return codigo
    except Exception as e:
        print(f"Erro ao consultar o banco: {e}")




async def ao_ser_adicionado(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    chat_name = update.message.chat.title

    if chat_id not in active_chats:
        active_chats[chat_id] = asyncio.create_task(start_bot(chat_id, chat_name, context))
        print(f'Bot iniciado no chat {chat_name}. Monitoramento iniciado!')
        await context.bot.send_message(chat_id=chat_id, text=f'Monitoramento iniciado para o chat {chat_name}!')


async def restaurar_monitoramento(context: ContextTypes.DEFAULT_TYPE):
    conexao = await conexao_banco()
    cursor = conexao.cursor()
    cursor.execute('SELECT COD_GRUPO FROM TLG_BIP')
    grupos = cursor.fetchall()
    print(grupos)
    for chat_id in grupos:
        chat_id = int(chat_id[0])
        # print(chat_id)
        try:
            if chat_id not in active_chats:

                chat = await context.bot.get_chat(chat_id)
                chat_name = chat.title

                active_chats[chat_id] = asyncio.create_task(start_bot(chat_id, chat_name, context))
                print(f'Restaurando monitoramento para o grupo {chat_name} // {chat_id}.')
        except Exception as e:
                print(f"Erro ao restaurar monitoramento para o chat {chat_name} //{chat_id}: {e}")

def main() -> None:

    try:
        
        #Token bot visão bips
        conexao_api = Application.builder().token("8092812812:AAFKtbKrUh1c1Rj0S1_LQ3EJWd-Rzgs_3Ps").build()
        # conexao_api = Application.builder().token("8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc").build()
        conexao_api.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, ao_ser_adicionado))
        conexao_api.add_handler(CallbackQueryHandler(button_handler))


        conexao_api.job_queue.run_once(restaurar_monitoramento, when=2)
        print("Iniciando o monitoramento...")
        conexao_api.run_polling()
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")

if __name__ == '__main__':
    main()

