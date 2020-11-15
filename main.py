from config import api_id, api_hash
from pyrogram import Client
from pyrogram.types.input_media import InputPhoneContact
import sys
import asyncio
import time
from datetime import datetime
import os 
import csv
import pandas as pd


app = Client(
    "account",
    api_id=api_id,
    api_hash=api_hash
)


"""
Функция получает имя пользователя по номеру телефона
return: имя пользователя telegram или None
"""
async def get_user_name(phone_number):
    add_phone = await app.add_contacts(
                        [
                            InputPhoneContact(phone_number, "Foo")
                        ]
                    )
    contacts = await app.get_contacts()
    if contacts:
        username = contacts[0].username
        await app.delete_contacts([username])
        print('Получен ник {} от телефона {}'.format(username, phone_number))
        return username
    else:
        return None

"""
Функция получает онлайн статус пользователя telegram
return: последний статус:
    - “online”, пользователь в сети прямо сейчас. 
    - "offline”, пользователь в оффлайне. 
    - "recently”, пользователь со скрытым статусом, который был онлайн между 1 секундой и 2-3 днями назад. 
    - “within_week”, пользователь со скрытым статусом, который был онлайн между 2-3 и 7 днями назад. 
    - “within_month”, пользователь со скрытым статусом, который был онлайн между 6-7 и месяцем назад. 
    - "long_time_ago”, заблокированный пользователь или пользователь со скрытым статусом, который был онлайн более месяца назад.
"""
async def get_status_user(username):
    status = await app.get_users(username)
    status = status['status']
    return status

"""
Функция формирует csv файлы с метками времени пользователей
Например:
timestamp,online
1605393931.625457,False
1605393936.767714,False
1605393941.859685,True
"""
async def write_csv_timestamp(dict_data, username, keys):
    with open('{}_time_status.csv'.format(username), 'a', encoding='utf-8', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, keys, delimiter=',')
        flag_csv_empty = os.stat('{}_time_status.csv'.format(username)).st_size == 0
        if flag_csv_empty:
            writer.writeheader()
        writer.writerows([dict_data])

"""
Функция формирует csv файлы с промежутками онлайн статуса пользователей и временем нахождения в сети
Например:
entry,exit,session_duration
14-11-2020 22:45:41,14-11-2020 22:45:46,5.0
14-11-2020 22:46:17,14-11-2020 22:46:37,20.0
14-11-2020 22:52:48,14-11-2020 22:53:03,15.0
"""
async def write_csv_online_status(dict_data, username, keys):
    with open('{}_online.csv'.format(username), 'a', encoding='utf-8', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, keys, delimiter=',')
        flag_csv_empty = os.stat('{}_online.csv'.format(username)).st_size == 0
        if flag_csv_empty:
            writer.writeheader()
        writer.writerows([dict_data])

"""
Функция преобразовывает csv файлы с метками времени пользователей в csv файлы с промежутками онлайн статуса пользователей и временем нахождения в сети
"""
async def parse_csv_time_status(username):
    dict_status = {
            'entry' : None,
            'exit' : None,
            'session_duration' : None
        }
    while True:
        df = pd.read_csv('{}_time_status.csv'.format(username), sep=',')
        df.columns = ['timestamp', 'online']
        count_true = False
        for index in range(len(df.index)):
            if (df.loc[index, 'online'] == True) and count_true == False:
                count_true = True
                dict_status['entry'] = datetime.fromtimestamp(df.loc[index, "timestamp"]).strftime('%d-%m-%Y %H:%M:%S')
            if count_true and (df.loc[index, 'online'] == False):
                count_true = False
                dict_status['exit'] = datetime.fromtimestamp(df.loc[index, "timestamp"]).strftime('%d-%m-%Y %H:%M:%S')
                session_duration = time.mktime(datetime.strptime(dict_status['exit'], '%d-%m-%Y %H:%M:%S').timetuple()) - time.mktime(datetime.strptime(dict_status['entry'], '%d-%m-%Y %H:%M:%S').timetuple())
            if dict_status['entry'] and dict_status['exit']:
                dict_status['session_duration'] = session_duration
                # print(username)
                # print(dict_status)
                keys = ['entry', 'exit', 'session_duration']
                try:
                    df1 = pd.read_csv('{}_online.csv'.format(username), sep=',')
                    if not any(df1.entry == dict_status['entry']):
                        print(any(df1.entry == dict_status['entry']))
                        await write_csv_online_status(dict_status, username, keys)
                    del df1
                except FileNotFoundError:
                    await write_csv_online_status(dict_status, username, keys)
                dict_status = {
                    'entry' : None,
                    'exit' : None,
                    'session_duration' : None
                }
        del df
        await asyncio.sleep(2)


"""
!TODO
Функция преобразовывает ищет пересечения онлайн статусов пользователей
"""
async def parce_csv_intersection(username):
    pass


"""
Функция для постоянного мониторинга онлайн статуса пользователей telegram
"""
async def status_user_monitor(username):
    keys = ['timestamp', 'online']
    dict_timestamp_status = {
        'timestamp' : None,
        'online' : None
    }
    while True:
        now_time = datetime.now()
        status = await get_status_user(username)
        print('{} {} - {}'.format(now_time.strftime("%d-%m-%Y %H:%M:%S"), username, status))
        if status == 'online':
            dict_timestamp_status['timestamp'] = now_time.timestamp()
            dict_timestamp_status['online'] = True
            await write_csv_timestamp(dict_timestamp_status, username, keys)
        elif status == 'offline':
            dict_timestamp_status['timestamp'] = now_time.timestamp()
            dict_timestamp_status['online'] = False
            await write_csv_timestamp(dict_timestamp_status, username, keys)
        await asyncio.sleep(1)


def menu():
    print("Что вы знаете о человеке?")
    print("1. Номер телефона")
    print("2. Имя пользователя в telegram")
    print("3. Выход")
    input_check = input("Выберите пункт: ")
    return(input_check)

async def main(loop):
    await app.start()
    item_menu = int(menu())
    if item_menu == 1:
        #phone_number = input('Введите номер телефона без +:\n')
        phone_number1 = "79126916010"
        phone_number2 = "79827919063"
        username1 = await get_user_name(phone_number1)
        username2 = await get_user_name(phone_number2)
        if username1 and username2:
            print('Мониторим...')
            #Cоздание задач для параллельного выплнения действий
            loop.create_task(status_user_monitor(username1))
            loop.create_task(status_user_monitor(username2))
            loop.create_task(parse_csv_time_status(username1))
            loop.create_task(parse_csv_time_status(username2))
        else:
            print('Номера телефона ещё нет в telegram или пользователь сменил настройки конфиденциальности!')
    elif item_menu == 2:
        name_user = input('Введите имя пользователя в telegram:\n')
    elif item_menu == 3:
        sys.exit(0)
    
        

 

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main(loop))
    loop.run_forever()