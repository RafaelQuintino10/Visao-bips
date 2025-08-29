
   
   
   
import psycopg2   
from telegram import Update   
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes   
from telegram.error import ChatMigrated   
   
active_chats = {}   
   
   
async def conexao_banco():   
    conexao = psycopg2.connect(   
            host="localhost",   
            database="postgres",   
            user="postgres",   
            password="fla1357912",   
            port="5432"   
        )   
    return conexao   
   
async def detectar_supergrupo(update: Update, context: ContextTypes.DEFAULT_TYPE):   
    if update.message and update.message.migrate_to_chat_id:   
        antigo_chat_id = update.message.chat.id   
        novo_chat_id = update.message.migrate_to_chat_id   
        print(f"[INFO] Grupo migrado para supergrupo! ID antigo: {antigo_chat_id}, Novo ID: {novo_chat_id}")   
   
        database = await conexao_banco()   
        cursor = database.cursor()   
        cursor.execute(   
            '''UPDATE TLG_GRUPOS SET COD_GRUPO = %s WHERE COD_GRUPO = %s''',   
            (novo_chat_id, antigo_chat_id)   
        )   
        database.commit()   
   
        if antigo_chat_id in active_chats:   
            active_chats[novo_chat_id] = active_chats.pop(antigo_chat_id)   
   
        try:   
            await update.message.reply_text(   
                f"O grupo foi migrado para supergrupo!\n"   
                f"ID antigo: {antigo_chat_id}\n"   
                f"Novo ID: {novo_chat_id}"   
            )   
        except ChatMigrated:   
            await context.bot.send_message(   
                chat_id=novo_chat_id,   
                text=f"O grupo foi migrado para supergrupo!\nID antigo: {antigo_chat_id}\nNovo ID: {novo_chat_id}"   
            )   
   

async def adicionar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:  
                chat_id = update.message.chat.id
                chat_name = update.message.chat.title

                database = await conexao_banco()
                cursor = database.cursor()
                cursor.execute(
                    '''
                    INSERT INTO TLG_GRUPOS (COD_GRUPO, NOMEGRUPO)
                    VALUES (%s, %s) ON CONFLICT (COD_GRUPO) DO NOTHING
                    ''',
                    (chat_id, chat_name)
                )
                database.commit()


                await update.message.reply_text(
                    f"Bot adicionado ao grupo!\nID do grupo: {chat_id}\nNome do grupo: {chat_name}"
                )

   
def main():   
    app = ApplicationBuilder().token("8012171445:AAFK183HpQe5DfDOUvduPUyxqvKThQ1NFlc").build()   
   
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, adicionar_grupo))

    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, detectar_supergrupo))

   
    print("Bot rodando...")   
    app.run_polling()   
   
if __name__ == '__main__':   
    main()  