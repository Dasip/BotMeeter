import config, db
from datetime import datetime, timedelta
from apscheduler.events import *
from apscheduler.schedulers.background import BackgroundScheduler
from dialogs import *
from db import *
from utility import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackQueryHandler

# Два массива отвечают за то, на какой стадии диалога с ботом находится юзер из конкретного чата
# chat_id: <str>
CHAT_STATUS = {}

# chat_id: <int>
CHAT_PHASE = {}

# user_id: <dict>
TMP_USR_INF = {}

# chat_id: <list>
TMP_KEYBOARD_MESS = {}

SCHEDULER = BackgroundScheduler()


def listener(event):
    if event.exception:
        print(event.exception)
    else:
        print("WORKED FINE")


def add_message_to_clearance(chat_id, message):
    if chat_id in TMP_KEYBOARD_MESS.keys():
        TMP_KEYBOARD_MESS[chat_id].append(message)
    else:
        TMP_KEYBOARD_MESS[chat_id] = [message]


def clear_keyboards(chat_id):
    for i in TMP_KEYBOARD_MESS[chat_id]:
        i.edit_reply_markup(reply_markup=None)
    TMP_KEYBOARD_MESS[chat_id] = []


def clear_list_of_keyboards(chat_id):
    TMP_KEYBOARD_MESS[chat_id] = []


def delete_keyboard(query):
    # Убираем клаву с прошлого сообщения бота
    query.edit_message_text(
        text=query.message.text
    )


def add_scheduled_task(task_name, args, delta, jitter, tid):
    time_now = datetime.now() + delta
    SCHEDULER.add_job(task_name, "cron", year=time_now.year,
                  month=time_now.month, day=time_now.day, hour=time_now.hour, minute=time_now.minute,
                  second=time_now.second, id=str(tid), args=args, jitter=jitter)


def generate_bio(user_id):
    info = get_info_on(user_id)
    noun1 = "он" if info["gender"] == GENDER_CALLS["MALE_CALL"] else "она"
    noun2 = "его" if info["gender"] == GENDER_CALLS["MALE_CALL"] else "ее"

    part_city = "{} - город, в котором {} живет.".format(info["city"].capitalize(), noun1)
    part_interest = "{} главные интересы: {}".format(noun2.capitalize(), info["interest"])
    return "\n{}\n{}".format(part_city, part_interest)


def regulate_profile(update: Update, context, query=None, current_call=None):
    chid = update.effective_message.chat_id
    user = update.effective_user
    us_id = update.effective_user.id

    if CHAT_PHASE[chid] == 1:

        replies = {GENDER_CALLS["MALE_CALL"]: "В мужском", GENDER_CALLS["FEMALE_CALL"]: "В женском",
                   LEAVE_NOW_CALL: "Оставить как есть"}
        reply = replies[current_call]

        # убираем клаву
        delete_keyboard(query)

        # Подтверждаем для пользователя его выбор
        context.bot.send_message(
            chat_id=chid,
            text=reply
        )

        # Записываем изменения для пользователя
        if current_call in GENDER_CALLS.values():
            TMP_USR_INF[us_id]["gender"] = current_call

        message = MESSAGE_NAME
        user_info = get_info_on(us_id)
        if user_info == None:
            message += "Текущее использующееся имя: {} {}".format(user.first_name, user.last_name)
        else:
            message += "Текущее использующееся имя: {}".format(user_info["name"])

        # Начинаем следующую фазу - имя
        new_message = context.bot.send_message(
            chat_id=chid,
            text=message,
            reply_markup=generate_name_keys(get_info_on(us_id))
        )
        add_message_to_clearance(chid, new_message)
        CHAT_PHASE[chid] = 2

    elif CHAT_PHASE[chid] == 2:
        if query != None:
            delete_keyboard(query)
            clear_list_of_keyboards(chid)
            if get_info_on(us_id) == None:
                TMP_USR_INF[us_id]["name"] = "{} {}".format(user.first_name, user.last_name)
        else:
            clear_keyboards(chid)
            TMP_USR_INF[us_id]["name"] = update.effective_message.text

        message = MESSAGE_CITY
        user_info = get_info_on(us_id)
        if user_info != None:
            message += "\n\nТекущий город: {}".format(user_info["city"])

        new_message = context.bot.send_message(
            chat_id=chid,
            text=message,
            reply_markup=generate_city_keys(get_info_on(us_id))
        )
        add_message_to_clearance(chid, new_message)
        CHAT_PHASE[chid] = 3

    elif CHAT_PHASE[chid] == 3:

        if query != None:
            delete_keyboard(query)
            clear_list_of_keyboards(chid)
            if current_call != LEAVE_NOW_CALL:
                TMP_USR_INF[us_id]["city"] = current_call
        else:
            clear_keyboards(chid)
            TMP_USR_INF[us_id]["city"] = update.effective_message.text

        message = MESSAGE_INTEREST
        user_info = get_info_on(us_id)
        if user_info != None:
            if user_info["interest"] != "":
                message += "\n\nТвои текущие интересы: {}".format(user_info["interest"])
            else:
                message += "\n\nСейчас ты - человек-загадка"

        new_message = context.bot.send_message(
            chat_id=chid,
            text=message,
            reply_markup=generate_bio_keys(get_info_on(us_id))
        )

        add_message_to_clearance(chid, new_message)
        CHAT_PHASE[chid] = 4

    elif CHAT_PHASE[chid] == 4:
        if query != None:
            delete_keyboard(query)
            clear_list_of_keyboards(chid)
            if current_call != LEAVE_NOW_CALL:
                TMP_USR_INF[us_id]["interest"] = ""
        else:
            clear_keyboards(chid)
            TMP_USR_INF[us_id]["interest"] = update.effective_message.text

        text = MESSAGE_PROFILE_SUCCESS

        context.bot.send_message(
            chat_id=chid,
            text=text
        )

        TMP_USR_INF[us_id]["user_id"] = user.id
        if get_info_on(user.id) == None:
            ok = db.add_new_user(TMP_USR_INF[us_id])
        else:
            ok = db.patch_one_user(TMP_USR_INF[us_id])

        if ok:
            TMP_USR_INF.pop(us_id)
        CHAT_STATUS[chid] = STATUS["FREE"]
        CHAT_PHASE[chid] = 0

        start_working(update, context, chid)


def regulate_contest(update: Update, context, query=None, current_call=None):
    chid = update.effective_message.chat_id
    us_id = update.effective_user.id

    if query != None:
        delete_keyboard(query)

    if current_call == CONTEST_CALLS["YES"]:
        context.bot.send_message(
            chat_id=chid,
            text=MESSAGE_SEARCH_OK
        )
        user_info = get_info_on(us_id)
        TMP_USR_INF[chid] = {"tid": us_id, "prev_pair": user_info["prev_pair"]}
        ok = add_to_pool(TMP_USR_INF[chid])
        if ok == None:
            TMP_USR_INF[chid] = {}
            CHAT_STATUS[chid] = STATUS["POOL"]
            CHAT_PHASE[chid] = 1
        else:
            connect_pair(update, context, us_id, ok["tid"])
            connect_pair(update, context, ok["tid"], us_id)

    elif current_call == CONTEST_CALLS["NO"]:
        context.bot.send_message(
            chat_id=chid,
            text=MESSAGE_SEARCH_NOT
        )


def regulate_quest(update: Update, context, query, current_call):
    chid = update.effective_message.chat_id
    us_id = update.effective_user.id

    delete_keyboard(query)

    if current_call == ENDING_CALLS["YES"]:
        CHAT_STATUS[chid] = STATUS["EVAL"]
        context.bot.send_message(
            text=MESSAGE_QUEST_YES,
            chat_id=chid,
            reply_markup=generate_eval_keys()
        )

    elif current_call == ENDING_CALLS["PLANNING"]:
        context.bot.send_message(
            text=MESSAGE_QUEST_PLAN,
            chat_id=chid
        )
        delta = timedelta(seconds=3)
        add_scheduled_task(start, (update, context,), delta, 4, us_id)


    elif current_call == ENDING_CALLS["NO"]:
        context.bot.send_message(
            text=MESSAGE_QUEST_NO,
            chat_id=chid
        )

        delta = timedelta(seconds=3)
        add_scheduled_task(start, (update, context,), delta, 4, us_id)


def regulate_eval(update: Update, context, query, current_call):
    chid = update.effective_message.chat_id
    us_id = update.effective_user.id

    delete_keyboard(query)
    if current_call == EVAL_CALLS["BEST"]:
        context.bot.send_message(
            chat_id=chid,
            text="Я рад, что все прошло так замечательно! Надеюсь, следующая встреча тебе понравится не меньше!"
        )

    elif current_call == EVAL_CALLS["GOOD"]:
        context.bot.send_message(
            chat_id=chid,
            text="Я рад, что все прошло довольно неплохо, и надеюсь, что следующая встреча пройдет лучше!"
        )

    elif current_call == EVAL_CALLS["MID"]:
        context.bot.send_message(
            chat_id=chid,
            text="Мне жаль, что все прошло не слишком хорошо, но я надеюсь, что твоя следующая встреча пройдет лучше!"
        )

    delta = timedelta(seconds=3)
    add_scheduled_task(start, (update, context,), delta, 4, us_id)



def remind_pair(update: Update, context, usid, pairid):
    info2 = get_info_on(pairid)

    CHAT_STATUS[usid] = STATUS["QUEST"]
    CHAT_PHASE[usid] = 1
    context.bot.send_message(
        chat_id=usid,
        text=f"Привет, это снова я! Вам с <a href='tg://user?id={pairid}'> {info2['name']} </a> уже удалось встретиться"
             f" или поговорить?",
        parse_mode=ParseMode.HTML,
        reply_markup=generate_end_contest_keys()
    )

    TMP_USR_INF[usid] = {"user_id": usid, "curr_pair": -1, "prev_pair": pairid}
    ok = patch_one_user(TMP_USR_INF[usid])
    if ok:
        TMP_USR_INF[usid] = {}


def connect_pair(update: Update, context, user_id, pair_id):
    pair_info = get_info_on(pair_id)
    try:
        addition = generate_bio(pair_id)
    except Exception as e:
        print(e)
    context.bot.send_message(
        chat_id=user_id,
        text="Привет! Я нашел тебе собеседника! Это - <a href='tg://user?id={}'> {} </a>!{}".format(pair_id,
                                                                                                    pair_info["name"],
                                                                                                    addition),
        parse_mode=ParseMode.HTML
    )

    TMP_USR_INF[user_id] = {"user_id": user_id, "curr_pair": pair_id}
    ok = patch_one_user(TMP_USR_INF[user_id])
    ok2 = delete_from_pool(user_id)
    if ok2:
        TMP_USR_INF[user_id] = {}

    diff = timedelta(days=7)

    add_scheduled_task(remind_pair, (update, context, user_id, pair_id,), diff, 4, user_id)


def start_working(update: Update, context, chat_id):
    context.bot.send_message(
        chat_id=chat_id,
        text=MESSAGE_SEARCH_ASK,
        reply_markup=generate_contest_keys()
    )
    CHAT_STATUS[chat_id] = STATUS["CONTEST"]
    CHAT_PHASE[chat_id] = 1


def keyboard_regulate(update: Update, context):
    query = update.callback_query
    current_callback = query.data
    chid = update.effective_message.chat_id
    #us_id = update.effective_user.id

    # Работа с профилем пользователя
    if CHAT_STATUS[chid] == STATUS["PROFILE"]:
        regulate_profile(update, context, query, current_callback)

    if CHAT_STATUS[chid] == STATUS["CONTEST"]:
        regulate_contest(update, context, query, current_callback)

    if CHAT_STATUS[chid] == STATUS["QUEST"]:
        regulate_quest(update, context, query, current_callback)

    if CHAT_STATUS[chid] == STATUS["EVAL"]:
        regulate_eval(update, context, query, current_callback)


def texting(update: Update, context):
    chid = update.effective_message.chat_id
    if CHAT_STATUS[chid] == STATUS["PROFILE"] and CHAT_PHASE[chid] in [2, 3, 4]:
        regulate_profile(update, context)


def generate_eval_keys():
    keyboard = [
        [InlineKeyboardButton("Отлично!", callback_data=EVAL_CALLS["BEST"])],
        [InlineKeyboardButton("Неплохо", callback_data=EVAL_CALLS["GOOD"])],
        [InlineKeyboardButton("Могло быть и лучше...", callback_data=EVAL_CALLS["MID"])]
    ]

    return InlineKeyboardMarkup(keyboard)


def generate_end_contest_keys():
    keyboard = [
        [InlineKeyboardButton("Да!", callback_data=ENDING_CALLS["YES"]),
         InlineKeyboardButton("Не получилось", callback_data=ENDING_CALLS["NO"])],
        [InlineKeyboardButton("Пока еще планируем", callback_data=ENDING_CALLS["PLANNING"])
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def generate_contest_keys():
    keyboard = [
        [InlineKeyboardButton("Участвую!", callback_data=CONTEST_CALLS["YES"]),
         InlineKeyboardButton("Воздержусь", callback_data=CONTEST_CALLS["NO"])]
    ]

    return InlineKeyboardMarkup(keyboard)


def generate_bio_keys(user_info):
    if user_info == None:
        keyboard = [
            [InlineKeyboardButton("Пропустить", callback_data=PASS_CALL)]
        ]

    else:
        keyboard = [
            [InlineKeyboardButton("Оставить как есть", callback_data=LEAVE_NOW_CALL)],
            [InlineKeyboardButton("Пропустить", callback_data=PASS_CALL)]
        ]

    return InlineKeyboardMarkup(keyboard)


def generate_city_keys(user_info):
    if user_info == None:
        keyboard = [
            [InlineKeyboardButton("Москва", callback_data=CITY_CALLS["MOSCOW"]),
             InlineKeyboardButton("Санкт-Петербург", callback_data=CITY_CALLS["SPB"])],
             [InlineKeyboardButton("Казань", callback_data=CITY_CALLS["KAZAN"]),
             InlineKeyboardButton("Нижний Новгород", callback_data=CITY_CALLS["NIZH"])]
        ]

    else:
        keyboard = [
            [InlineKeyboardButton("Москва", callback_data=CITY_CALLS["MOSCOW"]),
             InlineKeyboardButton("Санкт-Петербург", callback_data=CITY_CALLS["SPB"])],
             [InlineKeyboardButton("Казань", callback_data=CITY_CALLS["KAZAN"]),
             InlineKeyboardButton("Нижний Новгород", callback_data=CITY_CALLS["NIZH"])],
            [InlineKeyboardButton("Оставить текущий город", callback_data=LEAVE_NOW_CALL)]
        ]

    return InlineKeyboardMarkup(keyboard)


def generate_name_keys(user_info):
    keyboard = [
        [InlineKeyboardButton("Оставить текущее имя", callback_data=LEAVE_NOW_CALL)]
    ]

    return InlineKeyboardMarkup(keyboard)


def generate_gender_keys(user_info):
    if user_info == None:
        keyboard = [
            [InlineKeyboardButton("В мужском", callback_data=GENDER_CALLS["MALE_CALL"]),
             InlineKeyboardButton("В женском", callback_data=GENDER_CALLS["FEMALE_CALL"])]
        ]
    else:
        ml_add = EMOJIS["check"] if user_info["gender"] == "ml" else ""
        fml_add = EMOJIS["check"] if user_info["gender"] == "fml" else ""
        keyboard = [
            [InlineKeyboardButton(f"В мужском{ml_add}", callback_data=GENDER_CALLS["MALE_CALL"]),
             InlineKeyboardButton(f"В женском{fml_add}", callback_data=GENDER_CALLS["FEMALE_CALL"]),
             InlineKeyboardButton("Оставить как есть", callback_data=LEAVE_NOW_CALL)]
        ]

    return InlineKeyboardMarkup(keyboard)


def profile(update: Update, context):
    user_id = update.effective_user.id
    ch_id = update.effective_message.chat_id
    user_info = get_info_on(user_id)

    context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=MESSAGE_PROFILE_CHANGE
    )
    context.bot.send_message(
        chat_id=ch_id,
        text=MESSAGE_GENDER,
        reply_markup=generate_gender_keys(user_info)
    )
    TMP_USR_INF[user_id] = {}
    CHAT_STATUS[ch_id] = STATUS["PROFILE"]
    CHAT_PHASE[ch_id] = 1


def start(update: Update, context):
    user = update.effective_user
    ch_id = update.effective_message.chat_id
    user_name = user.first_name
    db_result = get_info_on(user.id)  # результат
    if db_result != None:
        CHAT_STATUS[ch_id] = STATUS["FREE"]
        CHAT_PHASE[ch_id] = 1
        start_working(update, context, ch_id)

    else:
        context.bot.send_message(
            chat_id=ch_id,
            text=MESSAGE_FIRST
        )
        context.bot.send_message(
            chat_id=ch_id,
            text=MESSAGE_GENDER,
            reply_markup=generate_gender_keys(db_result)
        )
        TMP_USR_INF[user.id] = {}
        CHAT_STATUS[ch_id] = STATUS["PROFILE"]
        CHAT_PHASE[ch_id] = 1


def main():
    my_update = Updater(
        token=config.TOKEN,
        #base_url=config.PROXI,
        use_context=True
    )

    keyboard_handler = CallbackQueryHandler(callback=keyboard_regulate, pass_chat_data=True)
    text_handler = MessageHandler(Filters.all, texting)
    start_handler = CommandHandler("start", start)
    profile_handler = CommandHandler("profile", profile)

    SCHEDULER.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_ADDED)
    SCHEDULER.start()

    my_update.dispatcher.add_handler(keyboard_handler)
    my_update.dispatcher.add_handler(start_handler)
    my_update.dispatcher.add_handler(profile_handler)
    my_update.dispatcher.add_handler(text_handler)

    my_update.start_polling()
    my_update.idle()


if __name__ == "__main__":
    main()