



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

database = conexao_banco()
cursor = database.cursor()

message = input('Dgite seu código: ')

lista_empresas = {'406','407','410'}

if message[:3] in lista_empresas and len(message)<5 or message[:3] not in lista_empresas:
    print('Condição código inválido!')

elif message[:3] in lista_empresas and len(message)>=5:
    print('Condição código válido!')
    cod_empr = message[:3]
    cod_fun = message[3:]
    codigo = str(cod_empr) + str(cod_fun)
cursor.execute('Select name from users where code = %s', (codigo,))

resultado = cursor.fetchone()

print(f"Obrigado, {resultado[0]}")