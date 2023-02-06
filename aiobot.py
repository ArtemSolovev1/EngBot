import csv
from subprocess import call
from gtts import gTTS
from random import randint
import random
from pymongo import MongoClient
from io import BytesIO
import time

import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, CallbackQuery

import time
from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from mongoengine import *
from app import User



API_TOKEN = '5018005832:AAFzS3pcBavrnSzqj-AhQIoGLstD9cetoeY'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

scheduler = AsyncIOScheduler()

# Пользователи
users = {}
# Словарь
words = {}


words_names = {
    'chinese': {
        'diff': ['_easy', '_medium'], 'lang': ['chinese', 'Китайский'], 'flag': '\U0001F1E8\U0001F1F3', 'voice_id': 'zh-CN'          
    },
    'czech': {
        'diff': ['_easy'], 'lang': ['czech', 'Чешский'], 'flag': '\U0001F1E8\U0001F1FF', 'voice_id': 'cs'  
    },
    'eng': {
        'diff': ['_easy', '_medium'], 'lang': ['eng', 'Английский'], 'flag': '\U0001F1EC\U0001F1E7', 'voice_id': 'en'  
    },
    'french': {
        'diff': ['_easy'], 'lang': ['french', 'Французский'], 'flag': '\U0001F1EB\U0001F1F7', 'voice_id': 'fr'  
    },
    'german': {
        'diff': ['_easy', '_medium'], 'lang': ['german', 'Немецкий'], 'flag': '\U0001F1E9\U0001F1EA', 'voice_id': 'de' 
    }
}

db = None

connect(host='mongodb://localhost:27017/qq')

    # 'Легкие' слова
for name in words_names:
    if '_easy' not in words_names[name]['diff'] == '':
        words[words_names[name]['lang'][0] + words_names[name]['diff'][0]] = 0
        continue
    with open('words/' + name + words_names[name]['diff'][0] + '.csv', encoding='utf8') as f:
        reader = csv.reader(f, delimiter=';')
        words[words_names[name]['lang'][0] + words_names[name]['diff'][0]] = list(reader)

    
# 'Средние' слова
for name in words_names:
    if '_medium' not in words_names[name]['diff']:
        continue
    with open('words/' + name + words_names[name]['diff'][1] + '.csv', encoding='utf8') as f:
        reader = csv.reader(f, delimiter=';')
        words[words_names[name]['lang'][0] + words_names[name]['diff'][1]] = list(reader)
        print(len(words[words_names[name]['lang'][0] + words_names[name]['diff'][1]]))



@dp.message_handler(commands=['change_lang'])
async def change_lang(message: types.Message):
    # Получаем id чата
    chat_id = message.from_user.id
    buttons=[]

    for name in words_names:
        # Добавление языков в клавиатуру
        buttons.append([InlineKeyboardButton(
            text=words_names[name]['lang'][1] + words_names[name]['flag'], 
            callback_data='set_lang ' + words_names[name]['lang'][0])],
        )
        print(buttons)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем сообщение и добавляем инлайн клавиатуру
    await message.answer(
        'Выберите язык для изучения.',
        reply_markup=keyboard
    )

@dp.message_handler(commands=['change_diff'])
async def change_dif_handler(message: types.Message):
    await change_dif(message.from_user.id)


async def change_dif(user_id):
    global users

    user = db.users.find_one({'_id': user_id})

    if '_medium' in words_names[user['lang']]['diff']:
        buttons = [
            [InlineKeyboardButton(
                text='Легкий', callback_data=('set_dif easy'))],
            [InlineKeyboardButton(
                text='Средний', callback_data=('set_dif medium'))]
        ]
    else:
        buttons = [
            [InlineKeyboardButton(
                text='Легкий', callback_data=('set_dif easy'))]
        ]

    # Отправляем сообщение и добавляем инлайн клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(
        chat_id=user_id,
        text='Выберите уровень сложности',
        reply_markup=keyboard
    )


   # Инициализация словаря
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    chat_id = message.from_user.id
    User.objects.get(_id=chat_id)

    if not user1:
        user1 = User(_id=chat_id)

    await change_lang(message)
    

@dp.message_handler(commands=['send_stats_a_day'])
async def send_stats_a_day_handler(message: types.Message):
    await send_stats_a_day(message.from_user.id)

async def make_stats_a_day_cron():
    users = db.users.find()
    
    for user in users:
        await send_stats_a_day(user.id)


async def send_stats_a_day(chat_id):
    diff_right_perc = 0
    diff_wrong_perc_text = 0
    
    user = db.users.find_one({ '_id': chat_id })

    if (len(user['current_day_count']) > len(user['last_day_count'])):
        diff_right_perc = (len(user['current_day_count']) - len(user['last_day_count'])) / len(user['current_day_count']) * 100
        diff_right_perc_text = '▲' + str(diff_right_perc) + ' %, '

    elif (len(user['current_day_count']) < len(user['last_day_count'])):
        diff_right_perc = (len(user['last_day_count']) - len(user['current_day_count'])) / len(user['current_day_count']) * 100
        diff_right_perc_text = '▼' + str(diff_right_perc) + ' %, '

    elif (len(user['current_day_count']) == len(user['last_day_count'])):
        diff_right_perc_text = '0,0 %, '


    if (len(user['wrong_answered_last_day']) < len(user['wrong_answered_current_day'])):
        diff_wrong_perc = (len(user['wrong_answered_current_day']) - len(user['wrong_answered_last_day'])) / len(user['wrong_answered_current_day']) * 100
        diff_wrong_perc_text = ' (▲' + str(diff_wrong_perc) + ' %, '

    elif (len(user['current_day_count']) < len(user['last_day_count'])):
        diff_wrong_perc = (len(user['wrong_answered_last_day']) - len(user['wrong_answered_current_day'])) / len(user['wrong_answered_current_day']) * 100
        diff_wrong_perc_text = ' (▼' + str(diff_wrong_perc) + ' %, '
        

        
    right_perc = len(user['current_day_count']) / (len(user['current_day_count']) + len(user['wrong_answered_current_day'])) * 100
    wrong_perc = len(user['wrong_answered_current_day']) / (len(user['current_day_count']) + len(user['wrong_answered_current_day'])) * 100
    
    print(diff_wrong_perc_text)
    
    await bot.send_message(
        chat_id=chat_id,
        text = '**Статистика за день**\n' + 'по сравнению с предыдущим' + '\n\n\U0001f7e2 Изучено слов - ' + str(len(user['current_day_count'])) + str(diff_wrong_perc_text) + str(len(user['last_day_count'])) + ')\n' + 
        '\U0001f534 Кол-во ошибок - ' + str(len(user['wrong_answered_current_day'])) + str(diff_wrong_perc_text) + str(len(user['wrong_answered_last_day'])) + ')'
    )
    
@dp.message_handler(commands=['send_stats_a_week'])
async def send_stats_a_week_handler(message: types.Message):
    await send_stats_a_week(message.from_user.id)

async def make_stats_a_week_cron():
    users = db.users.find()
    
    for user in users:
        await send_stats_a_week(user.id)

async def send_stats_a_week(chat_id):
    diff_right_perc = 0
    diff_wrong_perc_text = 0
    
    user = db.users.find_one({ '_id': chat_id })

    if (len(user['current_week_count']) > len(user['last_week_count'])):
        diff_right_perc = (len(user['current_week_count']) - len(user['last_week_count'])) / len(user['current_week_count']) * 100
        diff_right_perc_text = '▲' + str(diff_right_perc) + ' %, '

    elif (len(user['current_week_count']) < len(user['last_week_count'])):
        diff_right_perc = (len(user['last_week_count']) - len(user['current_week_count'])) / len(user['current_week_count']) * 100
        diff_right_perc_text = '▼' + str(diff_right_perc) + ' %, '

    elif (len(user['current_week_count']) == len(user['last_week_count'])):
        diff_right_perc_text = '0,0 %, '


    if (len(user['wrong_answered_last_week']) < len(user['wrong_answered_current_week'])):
        diff_wrong_perc = (len(user['wrong_answered_current_week']) - len(user['wrong_answered_last_week'])) / len(user['wrong_answered_current_week']) * 100
        diff_wrong_perc_text = ' (▲' + str(diff_wrong_perc) + ' %, '

    elif (len(user['current_week_count']) < len(user['last_week_count'])):
        diff_wrong_perc = (len(user['wrong_answered_last_week']) - len(user['wrong_answered_current_week'])) / len(user['wrong_answered_current_week']) * 100
        diff_wrong_perc_text = ' (▼' + str(diff_wrong_perc) + ' %, '
        
    right_perc = len(user['current_week_count']) / (len(user['current_week_count']) + len(user['wrong_answered_current_week'])) * 100

    wrong_perc = len(user['wrong_answered_current_week']) / (len(user['current_week_count']) + len(user['wrong_answered_current_week'])) * 100
    
    await bot.send_message(
        chat_id=chat_id,
        text = '**Статистика за неделю**\n' + 'по сравнению с предыдущим' + '\n\n\U0001f7e2 Изучено слов - ' + str(len(user['current_week_count'])) + str(diff_wrong_perc_text) + str(len(user['last_week_count'])) + ')\n' + 
        '\U0001f534 Кол-во ошибок - ' + str(len(user['wrong_answered_current_week'])) + str(diff_wrong_perc_text) + str(len(user['wrong_answered_last_week'])) + ')'
    )
    
@dp.message_handler(commands=['send_stats_a_month'])
async def send_stats_a_month_handler(message: types.Message):
    await send_stats_a_month(message.from_user.id)

async def make_stats_a_month_cron():
    users = db.users.find()
    
    for user in users:
        await send_stats_a_month(user.id)

async def send_stats_a_month(chat_id):
    diff_right_perc = 0
    diff_wrong_perc_text = 0
    
    user = db.users.find_one({ '_id': chat_id })

    if (len(user['current_month_count']) > len(user['last_month_count'])):
        diff_right_perc = (len(user['current_month_count']) - len(user['last_month_count'])) / len(user['current_month_count']) * 100
        diff_right_perc_text = '▲' + str(diff_right_perc) + ' %, '

    elif (len(user['current_month_count']) < len(user['last_month_count'])):
        diff_right_perc = (len(user['last_month_count']) - len(user['current_month_count'])) / len(user['current_month_count']) * 100
        diff_right_perc_text = '▼' + str(diff_right_perc) + ' %, '

    elif (len(user['current_month_count']) == len(user['last_month_count'])):
        diff_right_perc_text = '0,0 %, '


    if (len(user['wrong_answered_last_month']) < len(user['wrong_answered_current_month'])):
        diff_wrong_perc = (len(user['wrong_answered_current_month']) - len(user['wrong_answered_last_month'])) / len(user['wrong_answered_current_month']) * 100
        diff_wrong_perc_text = ' (▲' + str(diff_wrong_perc) + ' %, '

    elif (len(user['current_month_count']) < len(user['last_month_count'])):
        diff_wrong_perc = (len(user['wrong_answered_last_month']) - len(user['wrong_answered_current_month'])) / len(user['wrong_answered_current_month']) * 100
        diff_wrong_perc_text = ' (▼' + str(diff_wrong_perc) + ' %, '
        
    right_perc = len(user['current_month_count']) / (len(user['current_month_count']) + len(user['wrong_answered_current_month'])) * 100

    wrong_perc = len(user['wrong_answered_current_month']) / (len(user['current_month_count']) + len(user['wrong_answered_current_month'])) * 100
    
    await bot.send_message(
        chat_id=chat_id,
        text = '**Статистика за месяц**\n' + 'по сравнению с предыдущим' + '\n\n\U0001f7e2 Изучено слов - ' + str(len(user['current_month_count'])) + str(diff_wrong_perc_text) + str(len(user['last_month_count'])) + ')\n' + 
        '\U0001f534 Кол-во ошибок - ' + str(len(user['wrong_answered_current_month'])) + str(diff_wrong_perc_text) + str(len(user['wrong_answered_last_month'])) + ')'
    )
    

@dp.callback_query_handler()
async def callback_handler(query: types.CallbackQuery):
    global users

    chat_id = query.from_user.id
    answer_data = query.data
    User.objects.get(_id=chat_id)
    # user = db.users.find_one({'_id': chat_id})

    # Сообщение переданное нажатой кнопкой
    # query = update.callback_query
    # db.users.update_one({'_id': chat_id}, {'$set': {
    #     'status': 'selection_words',
    # }})
    user1 = User.objects(_id=chat_id).update_one(status='selection_words')
    user1.save()

    # Разбиваем сообщение на состовляющие,л в качестве разделителя используем пробел ['set_obj', 0]
    command = answer_data.split()

    if command[0] == 'set_dif':
        if command[1] == 'easy':
            user1 = User(diff='easy', status='selection_words')
            user1.save()

        elif command[1] == 'medium':
            user1 = User(diff='medium', status='selection_words')
            user1.save()

        random_idx = randint(0, len(words[user1['lang'] + '_' + command[1]]) - 1)
        
        await words_learning(chat_id, random_idx)

    elif command[0] == 'set_lang':
        for name in words_names:
            if command[1] == words_names[name]['lang'][0]:
                # db.users.update_one({'_id': chat_id}, {'$set': {
                #     'lang': words_names[name]['lang'][0]
                # }})
                user1 = User.objects(_id=chat_id).update_one(lang=words_names[name]['lang'][0], status='selection_words')
                user1.save()

                text = 'Вы выбрали ' + words_names[name]['lang'][1] + ' язык'
        await bot.send_message(chat_id=chat_id, text=text)
        # Отвечаем клиенту, что мы обработали ответ и ошибки нет
        # callback.answer()
        await change_dif(query.from_user.id)


async def words_learning(chat_id, random_idx):
    user1 = User.objects.get(_id=chat_id)
    
    if user1['status'] == 'error_correction':
        if len(user1['wrong_answered_words']) != 0:
            random_idx = random.choice(user1['wrong_answered_words'])
        else:
            # db.users.update_one ({'_id': chat_id}, {'$set':{
            #     'status': 'words_learning'
            # }})
            user1 = User.objects(_id=chat_id).update_one(status='words_learning')
            user1.save()

            random_idx = randint(0, len(words[user1['lang']+'_'+user1['diff']])-1)    

    # Присваивание рандомного индекса как текущего
    # db.users.update_one ({'_id': chat_id}, {'$set':{
    #     'current_task_idx': random_idx
    # }})
    user1 = User(current_task_idx=random_idx)
    user1.save()
    # Подбор 3-х вариантов ответа 2 неправильных и 1 правильный 
    answers = [
        words[user1['lang']+'_'+user1['diff']][randint(0, len(words[user1['lang']+'_'+user1['diff']])-1)][1], 
        words[user1['lang']+'_'+user1['diff']][randint(0, len(words[user1['lang']+'_'+user1['diff']])-1)][1], 
        words[user1['lang']+'_'+user1['diff']][random_idx][1] # Правильный ответ
    ]

    # Перемешивание вариантов ответов
    random.shuffle(answers)

    # Формирование кнопок для создания клавиатуры из вариантов ответов
    answers_keyboard = [[answers[0]], [answers[1]], [answers[2]]]

    # Создание клавиатуры
    kb = [
        [KeyboardButton(text=answers[0])],
        [KeyboardButton(text=answers[1])],
        [KeyboardButton(text=answers[2])]
    ]
    reply_kb_markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        keyboard=kb,
        one_time_keyboard=True)

    myText = words[user1['lang']+'_'+user1['diff']][random_idx][0]
    for name in words_names:
        if user1['lang'] == words_names[name]['lang'][0]:
            language = words_names[name]['voice_id']
    sound = BytesIO()

    output = gTTS(text=myText, lang=language, slow=False)
    output.write_to_fp(sound)

    sound.seek(0)

    output.save('sounds/' + words[user1['lang']+'_'+user1['diff']][random_idx][0] + '.ogg')
    await bot.send_voice(chat_id = chat_id, voice=sound)

    # Вывод клавиатуры
    await bot.send_message(
        chat_id=chat_id,
        text=words[user1['lang'] + '_' + user1['diff']][random_idx][0],
        reply_markup=reply_kb_markup
    )
    # db.users.update_one ({'_id': chat_id}, {'$set':{
    #     'start_time': time.time()
    # }})
    user1 = User.objects(_id=chat_id).update_one(start_time = time.time())
    user1.save()


@dp.message_handler()
async def echo(message: types.Message):
    global users
    
    chat_id = message.from_user.id
    # user = db.users.find_one({ '_id': chat_id })
    user1 = User.objects.get(_id=chat_id)

    if user1['status'] == 'error_correction':
        user_answer = message.text
        end_time = time.time()
        # user = db.users.find_one({ '_id': chat_id })
        if len(user1['wrong_answered_words']) != 0:
            # Проверка соответствует ли ответ пользователя нужному значению
            if str(words[user1['lang']+'_'+user1['diff']][user1['current_task_idx']][1]) == user_answer:
                # db.users.update_one({ '_id': chat_id }, { '$addToSet':{ 
                #     'right_idx'+'_'+user1['lang']: user1['current_task_idx'],
                #     'learned_words': user1['current_task_idx'],
                #     # Добавление правильно отвеченных слов в список 
                # }})
                user1 = User.objects(_id=chat_id).update_one(set__right_idx = user1['current_task_idx'])
                user1.save()
                # TODO
                # db.users.update_one({ '_id': chat_id }, { '$push':{ 
                #     'right_answ_time': end_time - user1['start_time']
                # }})
                user1 = User.objects(_id=chat_id).update_one(push__right_answ_time = end_time - user1['start_time'])
                user1.save()
                await message.answer('Верно!')
                # db.users.update_one({ '_id': chat_id }, { '$pull':{ 
                #     'wrong_answered_words': user1['current_task_idx']
                # }})
                user1 = User.objects(_id=chat_id).update_one(pull__wrong_answered_words = user1['current_task_idx'])
                user1.save()

                random_idx = random.choice(user1['wrong_answered_words'])
                await words_learning(message.from_user.id, random_idx)
            else:
                # db.users.update_one({ '_id': chat_id }, { '$addToSet':{ 
                #     'wrong_answered_words': user['current_task_idx'],
                #     'wrong_idx'+'_'+user['lang']: user['current_task_idx']
                # }})
                user1 = User.objects(_id=chat_id).update_one(pull__wrong_answered_words = user1['current_task_idx'])
                # db.users.update_one({ '_id': chat_id }, { '$push':{ 
                #     'wrong_answ_time': end_time - user['start_time']
                # }})
                user1 = User.objects(_id=chat_id).update_one(pull__wrong_answ_time = end_time - user1['start_time'])
                user1.save()
                # Вывод правильного ответа для усваивания материала пользователем
                await message.answer(
                    'Неверно! Правильный ответ - '+ words[user['lang']+'_'+user['diff']][user['current_task_idx']][1]
                )
                random_idx = random.choice(user['wrong_answered_words'])
                await words_learning(message.from_user.id, random_idx)

    if user['status'] == 'selection_words':
        random_idx = randint(0, len(words[user['lang']+'_'+user['diff']])-1)
        await words_learning(message.from_user.id, random_idx)

        # Вывод клавиатуры ORM Mongo
        await message.answer(
            text='Выберите правильный ответ.'
        )
        # db.users.update_one ({'_id': chat_id}, {'$set':{
        #     'status': 'words_learning'
        # }})
        # db.users.update_one({ '_id': chat_id }, { '$set':{ 
        #     'start_time': time.time()
        # }})
        user1 = User.objects(_id=chat_id).update_one(set__status = 'words_learning', set__start_time = time.time())
        user1.save()

    elif user['status'] == 'words_learning':
        # Считывание ответа пользователя
        user_answer = message.text
        end_time = time.time()
        user = db.users.find_one({ '_id': chat_id })
        # Проверка соответствует ли ответ пользователя нужному значению
        if str(words[user['lang']+'_'+user['diff']][user['current_task_idx']][1]) == user_answer:
            db.users.update_one({ '_id': chat_id }, { '$addToSet':{ 
                'right_idx'+'_'+user['lang']: user['current_task_idx'],
                'learned_words': user['current_task_idx'],
                'current_week_count': user['current_task_idx'],
                'current_day_count': user['current_task_idx']
                # Добавление правильно отвеченных слов в список 
            }})
            # db.users.update_one({ '_id': chat_id }, { '$push':{ 
            #     'right_answ_time': end_time - user['start_time']
            # }})
            user1 = User.objects(_id=chat_id).update_one(push__right_answ_time = end_time - user1['start_time'])
            user1.save()
            # Вывод 'верно'
            await message.answer('Верно!')

            # db.users.update_one({ '_id': chat_id }, { '$addToSet':{ 
            #     'current_day_count': user['current_task_idx'],
            #     'current_week_count': user['current_task_idx'],
            #     'current_month_count': user['current_task_idx']
            #     # Добавление правильно отвеченных слов в список 
            # }})
            user1 = User.objects(_id=chat_id).update_one(set__current_day_count = user1['current_task_idx'], set__current_week_count = user1['current_task_idx'], set__current_month_count = user1['current_task_idx'])
            user1.save()

            random_idx = randint(0, len(words[user['lang'] + '_' + user['diff']])-1)
            
            await words_learning(message.from_user.id, random_idx)
        else:
            db.users.update_one({ '_id': chat_id }, { '$addToSet':{ 
                'wrong_answered_words': user['current_task_idx'],
                'wrong_idx'+'_'+user['lang']: user['current_task_idx'],
                'wrong_answered_current_day': user['current_task_idx'],
                'wrong_answered_current_week': user['current_task_idx'],
                'wrong_answered_current_month': user['current_task_idx'],
            }})
            # db.users.update_one({ '_id': chat_id }, { '$push':{ 
            #     'wrong_answ_time': end_time - user['start_time']
            # }})
            user1 = User.objects(_id=chat_id).update_one(push__wrong_answ_time = end_time - user1['start_time'])
            user1.save()
            # Вывод правильного ответа для усваивания материала пользователем
            await message.answer(
                'Неверно! Правильный ответ - '+ words[user['lang']+'_'+user['diff']][user['current_task_idx']][1]
            )
            if len(user['wrong_answered_words']) == 10:
                text = ''
                for word in user['wrong_answered_words']:
                    text = text + words[user['lang'] + '_' + user['diff']][word][0] + ' - ' + words[user['lang']+'_'+user['diff']][word][1] + '\n'
                await message.answer(
                    chat_id=chat_id,
                    text='Вот список слов, на которые был дан неверный ответ:\n\n' + 
                    text + 
                    words[user['lang']+'_'+user['diff']][user['current_task_idx']][0] + ' - ' + 
                    words[user['lang']+'_'+user['diff']][user['current_task_idx']][1],
                )
                # db.users.update_one({ '_id': chat_id }, { '$set': {
                #     'status': 'error_correction'
                # }})
                user1 = User.objects(_id=chat_id).update_one(set__status = 'error_correction')
                user1.save()


                random_idx = random.choice(user['wrong_answered_words'])
                await words_learning(message.from_user.id, random_idx)
            else:
                random_idx = randint(0, len(words[user['lang']+'_'+user['diff']])-1)
                await words_learning(message.from_user.id, random_idx)


if __name__ == '__main__':
    scheduler.start()
    
    scheduler.add_job(make_stats_a_day_cron, "interval", days = 1)
    scheduler.add_job(make_stats_a_week_cron, "interval", weeks = 1)
    scheduler.add_job(make_stats_a_month_cron, "interval", days = 30)
    
    executor.start_polling(dp, skip_updates=True)