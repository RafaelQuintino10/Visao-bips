from datetime import datetime
from datetime import date, datetime, timedelta
import psycopg2


def conexao_banco():
    conexao = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="fla1357912",
            port="5432"
        )
    return conexao

def teste():
    database = conexao_banco()
    cursor = database.cursor()
    grupo = -1002490922945
    grupo_supervisao = -1002458377129
    cursor.execute('select hmsini, hmsfim from tlg_bip')
    horarios = cursor.fetchone()

    hora_inicio_str = horarios[0].strip()  # Está vindo como string
    hora_fim_str = horarios[1].strip()    # Também está como string

    print(hora_inicio_str)
    print(hora_fim_str)
    agora = datetime.now()
    # cursor.execute('''INSERT INTO TLG_BIPNOTIFIC (COD_GRUPO, COD_SUPERVISAO, HORA_ENVIO) VALUES ( %s, %s, %s)
    #                ''',(grupo,grupo_supervisao, agora))
    # database.commit()

    hora_minuto1 = '14:30:00'
    hora_minuto2 = '10:15:00'
    # data_inicial = '2025-02-17 '
    data_inicial = datetime.now().strftime('%Y-%m-%d ')

    
    # Convertendo as strings para objetos datetime (usando uma data fixa)
    data1 = datetime.strptime(data_inicial + hora_inicio_str, '%Y-%m-%d %H:%M:%S')
    data2 = datetime.strptime(data_inicial + hora_fim_str, '%Y-%m-%d %H:%M:%S')

    data2 = data2 + timedelta(days=1)
    print(f'Data inicial: {data1} // Data final: {data2}')
    resposta_funcionario = input('Digite seu código...')
    empr = resposta_funcionario[:3]
    codfun = resposta_funcionario[3:]
    codigo_funcionario = str(empr) + str(codfun)
    print(f'Empresa: {empr} Funcionário: {codfun}')
    print(codigo_funcionario)
    cursor.execute('select * from tlg_Bipnotific where hora_retorno >= %s and hora_retorno <= %s order by hora_envio asc',(data1,data2,))
    resultado = cursor.fetchone()
    print(resultado)
    if resultado is None:
        cursor.execute('''update tlg_bipnotific set empr = %s, codfun = %s, hora_retorno = %s 
        where cod_grupo = %s 
        and hora_envio = (select hora_envio from tlg_bipnotific 
        where cod_grupo = %s order by hora_envio desc limit 1)''',(empr, codfun, agora ,grupo, grupo,))
        database.commit()
        print('Retorno registrado!')
    elif resultado is not None:
        empr_tabela = resultado[4]
        codfun_tabela = resultado[5]
        print('Condição de excessão!')
        codigo_funcionario_tabela = str(empr_tabela) + str(codfun_tabela)
        print(codigo_funcionario_tabela)
        if codigo_funcionario == codigo_funcionario_tabela:
            cursor.execute('''update tlg_bipnotific set empr = %s, codfun = %s, hora_retorno = %s 
            where cod_grupo = %s and codfun is null 
            and hora_envio = (select hora_envio from tlg_bipnotific 
            where cod_grupo = %s order by hora_envio desc limit 1)''',(empr, codfun, agora ,grupo, grupo,))
            database.commit()
            print('Retorno registrado!!')
        else:
            print('Erro! Esse não é o seu código! Tente novamente!')
            teste()
    
teste()

