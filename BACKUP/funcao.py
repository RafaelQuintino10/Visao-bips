async def handle_tips_code(update: Update, context: CallbackContext) -> None:
    global var_temp, cod_empr_global, cod_fun_global, funcionario_global, data_inicial
    database = await conexao_banco()
    message = update.message.text
    chat_id = update.message.chat_id
    # print(len(message))
    cursor = database.cursor()

    cursor.execute('SELECT COD_SUPERVISAO FROM TLG_BIP WHERE COD_GRUPO = %s ', (chat_id,))

    data_atual = datetime.now().strftime("%Y-%m-%d")



    if message.replace(" ", "").replace("\n", "").isdigit() or message.upper() == 'SIM' or message.upper() == 'NÃO':
       
        if  ' ' in message or '\n' in message:
            await context.bot.send_message(chat_id=int(chat_id), text='Código Inválido! (QUEBRA DE LINHA) Tente novamente...')
            return
        
        lista_empresas = {'406','407','410'}

        if message[:3].upper() is not 'SIM' or message[:3].upper() is not 'NÃO':

            if message[:3] in lista_empresas and len(message)<5 or message[:3] not in lista_empresas:
                print('Condição código inválido!')
                await context.bot.send_message(chat_id=int(chat_id), text='Código Inválido! (FORA DA LISTA DE EMPRESAS) Tente novamente...')

            elif message[:3] in lista_empresas and len(message)>=5:
                print('Condição código válido!')
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
                    data_atual = datetime.now().strftime("%Y-%m-%d")
                    cursor.execute('SELECT HORA_RETORNO FROM TLG_BIPNOTIFIC WHERE COD_GRUPO = %s AND HORA_ENVIO >= %s  ORDER BY HORA_ENVIO DESC LIMIT 1',(chat_id,data_atual,))
                    ultimo_bip_hora_retorno = cursor.fetchone()[0]

                    if ultimo_bip_hora_retorno is None:

                        if resposta_funcionario:
                            try:
                                
                                    # Primeiro disparo!
                                    cursor.execute("Select USP_TLG_BIP_RESPOSTA(%s,%s,%s)",(codigo,chat_id,''))
                                    resultado = cursor.fetchone()[0]
                                    database.commit()
                                    print(f'Resultado consulta:{resultado}')
                                    await context.bot.send_message(chat_id=chat_id, text=resultado)

                                    print(f'Resultado fatiado: {resultado.split()[-1]}')
                                    if resultado.split()[-1] == 'SIM/NÃO':
                                        print('Var_temp atribuindo 1')
                                        # var_temp = 1
                                        # context.user_data['codigo'] = codigo
                                        print(f'Resposta da validação 1: {message}')
                                        # if message.upper() == 'SIM' and agora > "18:00" and agora < "06:00" :
                                        if message.upper() == 'SIM':
                                            print(f'Código-fun: {codigo}\nGrupo: {chat_id}')
                                            cursor.execute("Select USP_TLG_BIP_RESPOSTA(%s,%s,%s)",(codigo ,chat_id,'SIM'))
                                            database.commit()
                                            resultado = cursor.fetchone()[0]
                                            resposta = f"{resultado}" #\n(Se NÃO é você, clique em /trocar)"
                                            await context.bot.send_message(chat_id=int(chat_id),text=resposta)
                                            print(f'Resposta da validação 2: {message}')
                                        elif message.upper() == 'NÃO' or message.upper() == 'NAO':
                                        # elif message.upper() == 'NÃO' and agora > "20:00" and agora < "06:00" :
                                            await context.bot.send_message(chat_id=int(chat_id),text='Digite o seu código...')
                                            print(f'Resposta da validação 3: {message}')
                                        
                                        
                                
                            except Exception as e:
                                print(f"Erro ao consultar tabela user: {e}")

                        else:
                            resposta = "Nenhuma notificação encontrada para este grupo."
                    else:
                        print('Retorno já registrado!')


                except Exception as e:
                    print(f"Erro ao processar código: {e}")
                    # resposta = f"Erro ao processar código: {e}"
                finally:
                    if database:
                        database.close()
    if var_temp == 1:
        agora = datetime.now()
        if message.isalpha():
            print(f'Resposta da validação 1: {message}')
            # if message.upper() == 'SIM' and agora > "18:00" and agora < "06:00" :
            if message.upper() == 'SIM':
                print(f'Código-fun: {context.user_data['codigo']}\nGrupo: {chat_id}')
                cursor.execute("Select USP_TLG_BIP_RESPOSTA(%s,%s,%s)",(context.user_data['codigo'] ,chat_id,'SIM'))
                database.commit()
                resultado = cursor.fetchone()[0]
                resposta = f"{resultado}" #\n(Se NÃO é você, clique em /trocar)"
                await context.bot.send_message(chat_id=int(chat_id),text=resposta)
                print(f'Resposta da validação 2: {message}')
            elif message.upper() == 'NÃO' or message.upper() == 'NAO':
            # elif message.upper() == 'NÃO' and agora > "20:00" and agora < "06:00" :
                await context.bot.send_message(chat_id=int(chat_id),text='Digite o seu código...')
                print(f'Resposta da validação 3: {message}')

    if message.replace(" ", "").replace("\n", "") and message.upper().split('/')[-1] == 'TROCA':
        codigo_troc = message.split('/')[0]
        if  ' ' in message or '\n' in message:
            await context.bot.send_message(chat_id=int(chat_id), text='Código Inválido! Tente novamente...')
            return
        
        lista_empresas = {'406','407','410'}

        if codigo_troc[:3] in lista_empresas and len(message)<5 or codigo_troc[:3] not in lista_empresas:
            print('Condição código inválido!')
            await context.bot.send_message(chat_id=int(chat_id), text='Código Inválido! Tente novamente...')

        elif codigo_troc[:3] in lista_empresas and len(message)>=5:
            print('Condição código válido!')
            cod_empr = codigo_troc[:3]
            cod_fun = codigo_troc[3:]
            codigo = str(cod_empr) + str(cod_fun)
        print(f'Código funcionário no momento da troca: {codigo_troc}')
        print(f'Chat id no momento da troca: {chat_id}// {type(chat_id)}')
        cursor.execute("Select USP_TLG_BIP_RESPOSTA(%s,%s,%s)",(codigo,chat_id,'TRO'))
        resultado = cursor.fetchone()[0]
        database.commit()
        await context.bot.send_message(chat_id=chat_id, text=resultado)
        if resultado.split()[-1] == 'SIM/NÃO':
            print('Var_temp atribuindo 1')
            var_temp = 1
            context.user_data['codigo'] = codigo
   veja. a função é essa. Estamos usando var_tempo em outro if como variável global, ajutes pra não termos que usar isso e usarmos a validação por grupo 