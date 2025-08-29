# # BOT BIPs
# # 13/02/25 - Implementação do teclado - Retornado conforme 
# # orientação do Carlos devido a delay do teclado numérico
# # 03/03/25 - 281 - Adicionado o CHAT_ID na validação de grupos
# # 06/03/25 - Implementação da rotina de validação do funcionário no 1° envio
# # 16/07/25 - Implementação da rotina de troca de funcionários
# # 08/08/25 - Implementação da rotina de envio de perdas (3 alertas)

from datetime import datetime, timedelta
import random
import psycopg2
import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext, ContextTypes, CommandHandler

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


# async def conexao_banco():
#     conexao = psycopg2.connect(
#         host="192.168.88.237",
#         database='visao_ponto_db',
#         user='postgres',
#         password='QamN0*9yxe7!',
#         port='5432'
#     )
#     return conexao 

async def conexao_banco():
    conexao = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="fla1357912",
            port="5432"
        )
    return conexao

data_inicial = datetime.now().strftime('%Y-%m-%d ')
horarios = []
ultima_checagem = datetime.now()


async def gerar_horarios(inicio, fim, chat_name):
    print(f"Gerando horários aleatórios entre {inicio.time()} e {fim.time()}...")

    horarios = []
    try:
        if fim <= inicio:
            fim += timedelta(days=1)

        while inicio <= fim:
            horarios.append(inicio.strftime("%H:%M:%S"))
            inicio += timedelta(minutes=random.randint(5,10)) # INTERVALO DA ALEATORIEDADE DOS HORÁRIOS EM MINUTOS
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
                          WHERE FLAG_ALTERA = 1 AND COD_GRUPO = %s''',
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
    global ultima_hora_inicio, ultima_hora_fim, horarios, ultima_checagem, data_inicial
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

    cursor.execute('''SELECT * FROM TLG_BIP WHERE FLAG_ALTERA = 1 AND COD_GRUPO = %s ORDER BY HMSINI ASC LIMIT 1''', (chat_id,))
    tlg_bip_dados = cursor.fetchone()

    while True:
        agora = datetime.now()
        agora_V2 = datetime.now().strftime("%H:%M:%S")

        # 20:00 - 06:00
        # 19:56 - 19:58 - Gerar

        if nova_hora_inicio and nova_hora_fim:
            # print(f'Nova hora inicio: {nova_hora_inicio.strftime("%H:%M:%S")}  // Nova hora fim: {nova_hora_fim.strftime("%H:%M:%S")} - GR: {chat_name}')
            # print(f'agora: {agora_V2}')
            if agora_V2 == "17:58:00":
                data_inicial = agora.strftime('%Y-%m-%d ')
                # print(f"Data inicial resetada para: {data_inicial}")

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
            print(f"Enviando mensagem: Por favor, retorne o BIP. Grupo: {chat_name}")
            # mensagem_formatada = f'<b>{tlg_bip_dados[6]}</b>'
            await context.bot.send_message(chat_id=chat_id, text=tlg_bip_dados[6], parse_mode='HTML')
            cursor.execute('''INSERT INTO TLG_BIPNOTIFIC (ID_BIP, COD_GRUPO, COD_SUPERVISAO, HORA_ENVIO) VALUES (%s, %s, %s, %s)''',(tlg_bip_dados[0], tlg_bip_dados[1], tlg_bip_dados[2], agora))
            database.commit()

            await asyncio.sleep(60) # TOLERÂNCIA DE RESPOSTA 1.
            cursor.execute('SELECT HORA_ENVIO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id,))
            hora_envio_explicita = cursor.fetchone()[0]
            print(hora_envio_explicita)

            cursor.execute('''SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1''',(chat_id,))

            resposta_func = cursor.fetchone()[4]
            print(f"Última resposta do funcionário: {resposta_func}")
            if resposta_func is not None:
                print('Resposta encontrada! Seguindo pro próximo horário...')

            else:
                cursor.execute('select hmsini, hmsfim from tlg_bip where cod_grupo =%s',(chat_id,))
                horarios = cursor.fetchone()

                hora_inicio_str = horarios[0].strip()  
                hora_fim_str = horarios[1].strip()    

                print(hora_inicio_str)
                print(hora_fim_str)
                agora = datetime.now()
                
                
                data1 = datetime.strptime(data_inicial + hora_inicio_str, '%Y-%m-%d %H:%M:%S')
                data2 = datetime.strptime(data_inicial + hora_fim_str, '%Y-%m-%d %H:%M:%S')

                if data1 > data2:
                    data2 += timedelta(days=1)
                print(f'Data inicial 01: {data1} // Data final: {data2}')
                
                cursor.execute('select codfun from tlg_Bipnotific where cod_grupo = %s and hora_retorno >= %s and hora_retorno <= %s order by hora_envio asc',(chat_id, data1,data2,))
                resultado_codfun = cursor.fetchone()
                print(f'Primeira resposta: {resultado_codfun}')
                if resultado_codfun is not None:
                    print('Entrando na condição x')
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
                        #cursor.execute('SELECT NAME FROM PUBLIC.USER WHERE CODE = %s', (codigo,))
                        # cursor.execute('SELECT NAME FROM USERS WHERE CODE = %s', (codigo,))
                        cursor.execute('SELECT NAME FROM public.user WHERE CODE = %s', (codigo,))
                        funcionario = cursor.fetchone()
                        if funcionario:
                            print(funcionario[0])
                            # msg_supervisao = f'Funcionário {funcionario[0]} no grupo {chat_name} não responde desde às {hora_retorno}!'
                            msg_supervisao = f'Perda de BIP: {funcionario[0]} no grupo {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')
                        else:
                            print('Entrando na condição y')
                            print(f"Sem resposta registrada desde às {hora_envio_explicita.time()}")
                            # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {hora_envio_explicita.time()}!'
                            msg_supervisao = f'Perda de BIP no grupo: {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')

                elif resultado_codfun is None:
                    print(f"Sem resposta registrada desde às {active_chats[chat_id]['ultima_hora_inicio'].time().strftime('%H:%M')}")
                    # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}!'
                    msg_supervisao = f'Perda de BIP no grupo: {chat_name}. Atenção! Por favor, verificar!'
                    await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                    await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')

            await asyncio.sleep(60) # TOLERÂNCIA DE RESPOSTA 2.
            cursor.execute('SELECT HORA_ENVIO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id,))
            hora_envio_explicita = cursor.fetchone()[0]
            print(hora_envio_explicita)

            cursor.execute('''SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1''',(chat_id,))

            resposta_func = cursor.fetchone()[4]
            print(f"Última resposta do funcionário: {resposta_func}")
            if resposta_func is not None:
                print('Resposta encontrada! Seguindo pro próximo horário...')

            else:
                cursor.execute('select hmsini, hmsfim from tlg_bip where cod_grupo =%s',(chat_id,))
                horarios = cursor.fetchone()

                hora_inicio_str = horarios[0].strip()  
                hora_fim_str = horarios[1].strip()    

                print(hora_inicio_str)
                print(hora_fim_str)
                agora = datetime.now()
                
                
                data1 = datetime.strptime(data_inicial + hora_inicio_str, '%Y-%m-%d %H:%M:%S')
                data2 = datetime.strptime(data_inicial + hora_fim_str, '%Y-%m-%d %H:%M:%S')

                if data1 > data2:
                    data2 += timedelta(days=1)
                print(f'Data inicial 01: {data1} // Data final: {data2}')
                
                cursor.execute('select codfun from tlg_Bipnotific where cod_grupo = %s and hora_retorno >= %s and hora_retorno <= %s order by hora_envio asc',(chat_id, data1,data2,))
                resultado_codfun = cursor.fetchone()
                print(f'Primeira resposta: {resultado_codfun}')
                if resultado_codfun is not None:
                    print('Entrando na condição x')
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
                        #cursor.execute('SELECT NAME FROM PUBLIC.USER WHERE CODE = %s', (codigo,))
                        # cursor.execute('SELECT NAME FROM USERS WHERE CODE = %s', (codigo,))
                        cursor.execute('SELECT NAME FROM public.user WHERE CODE = %s', (codigo,))
                        funcionario = cursor.fetchone()
                        if funcionario:
                            print(funcionario[0])
                            # msg_supervisao = f'Funcionário {funcionario[0]} no grupo {chat_name} não responde desde às {hora_retorno}!'
                            msg_supervisao = f'Perda de BIP: {funcionario[0]} no grupo {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')
                        else:
                            print('Entrando na condição y')
                            print(f"Sem resposta registrada desde às {hora_envio_explicita.time()}")
                            # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {hora_envio_explicita.time()}!'
                            msg_supervisao = f'Perda de BIP no grupo: {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')

                elif resultado_codfun is None:
                    print(f"Sem resposta registrada desde às {active_chats[chat_id]['ultima_hora_inicio'].time().strftime('%H:%M')}")
                    # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}!'
                    msg_supervisao = f'Perda de BIP no grupo: {chat_name}. Atenção! Por favor, verificar!'
                    await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                    await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')

            await asyncio.sleep(60) # TOLERÂNCIA DE RESPOSTA 3.
            cursor.execute('SELECT HORA_ENVIO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id,))
            hora_envio_explicita = cursor.fetchone()[0]
            print(hora_envio_explicita)

            cursor.execute('''SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s ORDER BY HORA_ENVIO DESC LIMIT 1''',(chat_id,))

            resposta_func = cursor.fetchone()[4]
            print(f"Última resposta do funcionário: {resposta_func}")
            if resposta_func is not None:
                print('Resposta encontrada! Seguindo pro próximo horário...')

            else:
                cursor.execute('select hmsini, hmsfim from tlg_bip where cod_grupo =%s',(chat_id,))
                horarios = cursor.fetchone()

                hora_inicio_str = horarios[0].strip()  
                hora_fim_str = horarios[1].strip()    

                print(hora_inicio_str)
                print(hora_fim_str)
                agora = datetime.now()
                
                
                data1 = datetime.strptime(data_inicial + hora_inicio_str, '%Y-%m-%d %H:%M:%S')
                data2 = datetime.strptime(data_inicial + hora_fim_str, '%Y-%m-%d %H:%M:%S')

                if data1 > data2:
                    data2 += timedelta(days=1)
                print(f'Data inicial 01: {data1} // Data final: {data2}')
                
                cursor.execute('select codfun from tlg_Bipnotific where cod_grupo = %s and hora_retorno >= %s and hora_retorno <= %s order by hora_envio asc',(chat_id, data1,data2,))
                resultado_codfun = cursor.fetchone()
                print(f'Primeira resposta: {resultado_codfun}')
                if resultado_codfun is not None:
                    print('Entrando na condição x')
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
                        #cursor.execute('SELECT NAME FROM PUBLIC.USER WHERE CODE = %s', (codigo,))
                        # cursor.execute('SELECT NAME FROM USERS WHERE CODE = %s', (codigo,))
                        cursor.execute('SELECT NAME FROM public.user WHERE CODE = %s', (codigo,))
                        funcionario = cursor.fetchone()
                        if funcionario:
                            print(funcionario[0])
                            # msg_supervisao = f'Funcionário {funcionario[0]} no grupo {chat_name} não responde desde às {hora_retorno}!'
                            msg_supervisao = f'Perda de BIP: {funcionario[0]} no grupo {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')
                        else:
                            print('Entrando na condição y')
                            print(f"Sem resposta registrada desde às {hora_envio_explicita.time()}")
                            # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {hora_envio_explicita.time()}!'
                            msg_supervisao = f'Perda de BIP no grupo: {chat_name} // {hora_envio_explicita.time().strftime("%H:%M")}!'
                            await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                            await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')

                elif resultado_codfun is None:
                    print(f"Sem resposta registrada desde às {active_chats[chat_id]['ultima_hora_inicio'].time().strftime('%H:%M')}")
                    # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}!'
                    msg_supervisao = f'Perda de BIP no grupo: {chat_name}. Atenção! Por favor, verificar!'
                    await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                    await context.bot.send_message(chat_id=int(chat_id),text='Não recebi o bip! Favor, retornar!!!')


        # else:
            # print(f"Fora do horário: {agora.strftime("%H:%M:%S")}")


        await asyncio.sleep(1)


async def handle_tips_code(update: Update, context: CallbackContext) -> None:
    database = await conexao_banco()
    message = update.message.text.strip()
    chat_id = update.message.chat_id
    cursor = database.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d")

    cursor.execute('SELECT COD_SUPERVISAO FROM TLG_BIP WHERE COD_GRUPO = %s ', (chat_id,))

    lista_empresas = {'406','407','410'}

    if message.replace(" ", "").replace("\n", "").isdigit() or message.upper() == 'SIM' or message.upper() == 'NÃO' or message.upper() == 'NAO':
        if ' ' in message or '\n' in message:
            await context.bot.send_message(chat_id=chat_id, text='Código Inválido! Tente novamente...')
            return

        if message.upper() == 'SIM' or message.upper() == 'NÃO' or message.upper() == 'NAO':
            if context.chat_data.get('aguardando_confirmacao'):
                codigo = context.chat_data.get('codigo')
                if not codigo:
                    await context.bot.send_message(chat_id=chat_id, text='Código não encontrado. Envie novamente.')
                    return

                if message.upper() == 'SIM':
                    cursor.execute("SELECT USP_TLG_BIP_RESPOSTA(%s, %s, %s)", (codigo, chat_id, 'SIM'))
                    resultado = cursor.fetchone()[0]
                    database.commit()
                    await context.bot.send_message(chat_id=chat_id, text=resultado)
                else:
                    await context.bot.send_message(chat_id=chat_id, text='Digite o seu código...')

                context.chat_data['aguardando_confirmacao'] = False
            else:
                await context.bot.send_message(chat_id=chat_id, text='Você precisa enviar um código primeiro.')
            return

        if message[:3] in lista_empresas and len(message) >= 5:
            cod_empr = message[:3]
            cod_fun = message[3:]
            codigo = cod_empr + cod_fun
            context.chat_data['codigo'] = codigo
            print(f'Código: {codigo}')
            try:
                cursor.execute('SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s  AND CODFUN IS NULL ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id,))
                resposta_funcionario = cursor.fetchone()

                cursor.execute('SELECT HORA_RETORNO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s AND HORA_ENVIO >= %s ORDER BY HORA_ENVIO DESC LIMIT 1', (chat_id, data_atual,))
                ultimo_bip_hora_retorno = cursor.fetchone()[0]

                if resposta_funcionario and ultimo_bip_hora_retorno is None:
                    cursor.execute("SELECT USP_TLG_BIP_RESPOSTA(%s, %s, %s)", (codigo, chat_id, ''))
                    resultado = cursor.fetchone()[0]
                    database.commit()
                    await context.bot.send_message(chat_id=chat_id, text=resultado)

                    if resultado.split()[-1] == 'SIM/NÃO':
                        context.chat_data['aguardando_confirmacao'] = True
                else:
                    print("Retorno já registrado ou sem resposta.")
            except Exception as e:
                print(f"Erro ao processar código: {e}")
        else:
            await context.bot.send_message(chat_id=chat_id, text='Código Inválido! Tente novamente...')
    elif message.replace(" ", "").replace("\n", "") and message.upper().split('/')[-1] == 'TROCA':
        codigo_troc = message.split('/')[0]
        if codigo_troc[:3] in lista_empresas and len(codigo_troc) >= 5:
            cod_empr = codigo_troc[:3]
            cod_fun = codigo_troc[3:]
            codigo = str(cod_empr) + str(cod_fun)
            context.chat_data['codigo'] = codigo
            print(f'Código ao ser trocado: {codigo}')
            cursor.execute("SELECT USP_TLG_BIP_RESPOSTA(%s, %s, %s)", (codigo, chat_id, 'TRO'))
            resultado = cursor.fetchone()[0]
            database.commit()
            await context.bot.send_message(chat_id=chat_id, text=resultado)

            if resultado.split()[-1] == 'SIM/NÃO':
                context.chat_data['aguardando_confirmacao'] = True
        else:
            await context.bot.send_message(chat_id=chat_id, text='Código Inválido! Tente novamente.')




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
    # chat_id = -1001397692235
    # chat_name = 'Green P1'
    # active_chats[chat_id] = asyncio.create_task(start_bot(chat_id, chat_name, context))
    # print(f'Restaurando monitoramento para o grupo {chat_name} // {chat_id}.')
    for chat_id in grupos:
        chat_id = int(chat_id[0])
        # print(chat_id)    -1448932374
        try:
            if chat_id not in active_chats:

                chat = await context.bot.get_chat(chat_id)
                chat_name = chat.title
                print(chat_name)

                active_chats[chat_id] = asyncio.create_task(start_bot(chat_id, chat_name, context))
                print(f'Restaurando monitoramento para o grupo {chat_name} // {chat_id}.')
        except Exception as e:
                print(f"Erro ao restaurar monitoramento para o chat {chat_name} //{chat_id}: {e}")


def main() -> None:

    try:
        
        #Token bot visão bips
        conexao_api = Application.builder().token("8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc").build()
        # Novo token visão bip!
        # conexao_api = Application.builder().token("7920327954:AAETrVcvg1wiS5PCwVI_aXJLPR4uVp5sgNw").build()
        conexao_api.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tips_code))
        conexao_api.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, ao_ser_adicionado))
        # conexao_api.add_handler(CommandHandler('trocar', corrigir_fun))
        # conexao_api.add_handler(CommandHandler('troca', troca_func))
        

        conexao_api.job_queue.run_once(restaurar_monitoramento, when=2)
        print("Iniciando o monitoramento...")
        conexao_api.run_polling()
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")

if __name__ == '__main__':                
    main()

