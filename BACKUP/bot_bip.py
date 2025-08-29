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

async def conexao_banco():
    conexao = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="fla1357912",
            port="5432"
        )
    return conexao

ultima_hora_inicio = None
ultima_hora_fim = None
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
            inicio += timedelta(minutes=random.randint(4,6)) # INTERVALO DA ALEATORIEDADE DOS HORÁRIOS EM MINUTOS
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
        print(f'tlg_Bip_resultado{tlg_bip_horarios}')
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
    print(chat_id)
    nova_hora_inicio, nova_hora_fim = await consulta_banco(chat_id)
    database = await conexao_banco()
    cursor = database.cursor()
    # cursor.execute('''
    #         INSERT INTO TLG_GRUPOS (COD_GRUPO, NOMEGRUPO)
    #         VALUES (%s, %s) ON CONFLICT (COD_GRUPO) DO NOTHING
    #     ''', (chat_id, chat_name))

    # database.commit()
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
            await context.bot.send_message(chat_id=chat_id, text=tlg_bip_dados[6])
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
                    cursor.execute('SELECT NAME FROM users WHERE CODE = %s', (codigo,))
                    funcionario = cursor.fetchone()
                    if funcionario:
                        print(funcionario[0])
                        # msg_supervisao = f'Funcionário {funcionario[0]} no grupo {chat_name} não responde desde às {hora_retorno}!'
                        msg_supervisao = f'Perda de BIP: {funcionario[0]} no grupo {chat_name} // {hora_envio_explicita.time()}!'
                        await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
                    else:
                        print(f"Sem resposta registrada desde às {hora_envio_explicita.time()}")
                        # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {hora_envio_explicita.time()}!'
                        msg_supervisao = f'Perda de BIP no grupo: {chat_name} // {hora_envio_explicita.time()}!'
                        await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)

                else:
                    print(f"Sem resposta registrada desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}")
                    # msg_supervisao = f'Sem resposta registrada no grupo {chat_name} desde às {active_chats[chat_id]["ultima_hora_inicio"].time()}!'
                    msg_supervisao = f'Perda de BIP no grupo: {chat_name}. Atenção! Por favor, verificar!'
                    await context.bot.send_message(chat_id=int(tlg_bip_dados[2]),text=msg_supervisao)
        # else:
            # print(f"Fora do horário: {agora.strftime("%H:%M:%S")}")
        await asyncio.sleep(1)

        if agora.strftime("%H:%M:%S") == active_chats[chat_id]["horarios"][-1]:
            print(f"Último horário para o grupo {chat_name}: {active_chats[chat_id]['horarios'][-1]}")
            novos_horarios = await gerar_horarios(active_chats[chat_id]["ultima_hora_inicio"], active_chats[chat_id]["ultima_hora_fim"], chat_name)
            active_chats[chat_id]["horarios"] = novos_horarios
            print(f"Nova lista de horários para o grupo {chat_name}: \n{novos_horarios}")



async def handle_tips_code(update: Update, context: CallbackContext) -> None:
    database = await conexao_banco()
    message = update.message.text
    chat_id = update.message.chat_id
    print("Mensagem recebida:", message)
    chat_name = update.message.chat.title
    cursor = database.cursor()
    cursor.execute('SELECT COD_SUPERVISAO FROM TLG_BIP WHERE COD_GRUPO = %s ', (chat_id,))
    cod_supervisao = cursor.fetchone()[0]
    # print(f'Código supervisão: {cod_supervisao}')
    if message.isdigit() and len(message) >=4:
        cod_empr = message[:3]
        cod_fun = message[3:]
        codigo = str(cod_empr) + str(cod_fun)
        # print(codigo)
        fun_timelog = datetime.now()

        try:
            cursor.execute('''
           SELECT * FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s  AND CODFUN IS NULL ORDER BY HORA_ENVIO DESC LIMIT 1
            ''', (chat_id,))
            resposta_funcionario = cursor.fetchone()
            # print(resposta_funcionario)

            if resposta_funcionario:
                id_bip = resposta_funcionario[1]
                id_notifica = resposta_funcionario[0]
                try:
                    cursor.execute('SELECT NAME, CODE FROM USERS WHERE CODE =%s', (str(codigo),))
                    funcionario_codigo = cursor.fetchone()
                    if funcionario_codigo[1]:

                        cursor.execute('''UPDATE TLG_BIPNOTIFIC SET EMPR = %s, CODFUN = %s, HORA_RETORNO = %s WHERE ID_BIP = %s AND ID_NOTIFICA = %s
                        ''', (cod_empr, cod_fun, fun_timelog, id_bip, id_notifica))

                        database.commit()
                        # cursor.execute('SELECT NAME FROM users WHERE CODE =%s', (str(codigo),))
                        # nome_funcionario = cursor.fetchone()[0]
                        resposta = f"Obrigado {funcionario_codigo[0]}, recebido!"
                    else:
                        resposta = "Código inválido!"
                        # await context.bot.send_message(chat_id=int(cod_supervisao),text=f"Código de resposta inválido no grupo {chat_name}. Favor verificar.")
                except Exception as e:
                    print(f"Erro ao consultar tabela user: {e}")

            else:
                resposta = "Nenhuma notificação encontrada para este grupo."

        except Exception as e:
            print(f"Erro ao processar código: {e}")
            resposta = f"Erro ao processar código: {e}"
        finally:
            if database:
                database.close()
    # else:
    #     resposta = "Código enviado!"
    #     await context.bot.send_message(chat_id=int(cod_supervisao),text=f"Código de resposta inválido no grupo {chat_name}. Favor verificar.")

    await update.message.reply_text(resposta)



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
        print(chat_id)
        try:
            if chat_id not in active_chats:

                chat = await context.bot.get_chat(chat_id)
                print(chat)
                chat_name = chat.title
                print(chat_name)

                active_chats[chat_id] = asyncio.create_task(start_bot(chat_id, chat_name, context))
                print(f'Restaurando monitoramento para o grupo {chat_name} // {chat_id}.')
        except Exception as e:
                print(f"Erro ao restaurar monitoramento para o chat {chat_name} //{chat_id}: {e}")


def main() -> None:

    try:

        #Token bot visão bips

        conexao_api = Application.builder().token('8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc').build()
        # conexao_api = Application.builder().token("8092812812:AAFKtbKrUh1c1Rj0S1_LQ3EJWd-Rzgs_3Ps").build()
        conexao_api.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tips_code))
        conexao_api.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, ao_ser_adicionado))

        conexao_api.job_queue.run_once(restaurar_monitoramento, when=2)
        print("Iniciando o monitoramento...")
        conexao_api.run_polling()
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")

if __name__ == '__main__':
    main()

