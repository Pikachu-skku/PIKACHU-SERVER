# -*- coding: utf-8 -*-
"""Untitled1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15NfL6xCqGeMuskvqz_ARApWPAIbnq3Yb
"""

''' Colab 환경에서는 필요

!pip install --upgrade setuptools

!pip3 install python-telegram-bot

!pip install firebase_admin

'''

import asyncio
import random
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time

from telegram.ext import (
    CommandHandler,
    Application
)

import nest_asyncio

nest_asyncio.apply()

'''

GPSs => [
    (Telegram_id) => [
        GPS => [위도, 경도],
        last_time => 0000, # -1이 될 경우 긴급상황 메시지가 전송된 것
        status => (boolean) # true : 외출 상황, false : 외출 상황 아님,
        disconnected => (boolean) # true : 긴급 상황, false : 긴급 상황 아님
    ]
]

FRIENDS => [
    (Telegram id) => [(Friend 1 Telegram id), (Friend 2 Telegram id)]
]

REGISTER => [
    (Telegram id) => [
        status => (boolean) # True : 인증 완료, False : 인증 완료 안 됨
        code => (integer) # 6자리 숫자 원래 코드
        sent_code => (integer) #  휴대폰에서 보낸 6자리 코드
    ]
]

'''

print("[System] Start Pikachu server service")

# 파이어베이스 설정

cred = credentials.Certificate("skku-pikachu-firebase.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://skku-pikachu-default-rtdb.firebaseio.com/'
})

print("[System/Telegram] Setting... ")

token = "5417501156:AAGiZWxuIX0N7Ujr5iFFuiVB6lr8S5sNt9c" # TODO 토큰 알아오기

updater = Application.builder().token(token).build()

bot = updater.bot


'''

LOOP

'''


async def start_loop():

    g_db = db.reference("GPSs")
    f_db = db.reference("FRIENDS")

    print("[System/Looper] Start loop")
    async with bot:
        while True:
            print("A")
            
            '''

                핸드폰 상태 파악

            '''

            datas = g_db.get()


            for tele_id in datas.keys():

                if not datas[tele_id]["status"]: # 외출 상황인지 확인
                    continue

                if datas[tele_id]["last_time"] is -1: # 메시지 이미 보냈으면 무시
                    continue

                if datas[tele_id]["last_time"] + 60 * 10 <= time.time(): # 10분 이상 지났을 때

                    

                    g_db(tele_id + '/disconnected').set(True) # 데이터 베이스에 위험 표시 ON

                    friends = f_db(tele_id).get()

                    if friends is not None:
                        
                        for friend in friends.keys():
                            
                            await bot.sendMessage(chat_id=friend, text="현재 " + tele_id + "님이 10분동안 연결이 안 됩니다! 도와주세요.")
                            await bot.sendMessage(chat_id=friend, text="GPS 위도 : " + str(datas[tele_id]["GPS"][0]) + ", GPS 경도 : " + str(datas[tele_id]["GPS"][1]))

                    g_db(tele_id + '/last_time').set(-1) # 데이터 베이스에 위험 표시 ON

                elif datas[tele_id]["disconnected"]: # 10분 이상 안 지났는데 disconnected 가 계속 이루어지면 

                    

                    g_db(tele_id + '/disconnected').set(False) # 데이터 베이스에 위험 표시 ON

                    friends = f_db(tele_id).get()

                    if friends is not None:
                        
                        for friend in friends.keys():

                            await bot.sendMessage(chat_id=friend, text="" + tele_id + "님의 연결이 회복되었습니다. 감사합니다.")

                '''

                텔레그램 인증 절차

                핸드폰에서 데이터베이스 생성 -> 서버에서 code 업데이트 -> 핸드폰에서 sent_code 업데이트 -> 서버에서 대조 후 맞으면 status 업데이트 -> 핸드폰에서 GPSs랑 Friends 등록

                '''   


            register_datas = db.reference('REGISTER').get()

            if register_datas is None:
                continue

            for tele_id in register_datas:

                if not register_datas[tele_id]['status'] and register_datas[tele_id]['code'] == 0: # 핸드폰에서 시도를 하면 인증번호를 만들고 보내기

                    code = random.randint(1, 999999)
                    register_datas[tele_id]['code'] == code
                    await bot.sendMessage(chat_id = tele_id, text = "인증번호 [" + str(code) + "]")
                    db.reference('REGISTER/' + tele_id + "/code").set(code)

                if not register_datas[tele_id]['status'] and register_datas[tele_id]['code'] is not 0: # 핸드폰에서 인증번호를 보냈으면 비교하고 맞으면 status 업데이트하기
                    if register_datas[tele_id]['code'] == register_datas[tele_id]['sent_code']:

                        db.reference('REGISTER/' + tele_id + "/status").set(True)

                    elif register_datas[tele_id]['sent_code'] is not -1:

                        db.reference('REGISTER/' + tele_id + "/sent_code").set(-1)


'''

텔레그램 CommandHandler 설정

명령어 종류 : register, delete, friends

'''


g_db = db.reference("GPSs")
f_db = db.reference("FRIENDS")

async def register_friend(update, context): # 사용자가 친구를 등록

    friend_id = context.args[0]

    await context.bot.send_message(chat_id=update.effective_chat.id, text= friend_id + "를 응급 연락처에 저장합니다. 사용자님은 이 사실을 /delete를 통해 취소할 수 있습니다.")

    friends = f_db(str(update.effective_chat.id)).get()

    if friends is None:
        friends = dict()


    friends[friend_id] = 0
    f_db(str( update.effective_chat.id)).set(friends)

updater.add_handler(CommandHandler('register', register_friend))


async def delete_friend(update, context): # 사용자가 친구를 자신의 긴급연락처에 존재하는 것을 거절

    friend_id = context.args[0]

    friends_in_me = f_db(str(update.effective_chat.id)).get()

    if friend_id not in friends_in_me.keys():

        await context.bot.send_message(chat_id=update.effective_chat.id, text= friend_id + "님은 사용자와 친구가 아닙니다.")

    else:

        await context.bot.send_message(chat_id=update.effective_chat.id, text= friend_id + "님과 친구를 취소합니다.")

        del friends_in_me[friend_id] # 나의 연락처에 친구 삭제

        f_db(str(update.effective_chat.id)).set(friends_in_me)


updater.add_handler(CommandHandler('delete', delete_friend))


async def friend_list(update, context): # 자신의 친구 조회

    friends = f_db(str(update.effective_chat.id)).get()

    await context.bot.send_message(chat_id=update.effective_chat.id, text= "응급 연락처에 존재하는 친구 목록을 보내드립니다.")

    if friends is None:
        return

    if len(friends.keys()) == 0:
        return

    for friend_id in friends.keys():

        await context.bot.send_message(chat_id=update.effective_chat.id, text= friend_id)
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text= "끝")


updater.add_handler(CommandHandler('friends', friend_list))

async def get_my_id(update, context): # 자신의 아이디 조회
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text= update.effective_chat.id)


updater.add_handler(CommandHandler('myid', get_my_id))

async def run_tele_bot():
    print("[System/Telegram] Start Telegram Bot")
    updater.run_polling()

async def run():

    await asyncio.gather(run_tele_bot(), start_loop())

    print("[System] Bye")

asyncio.run(run())