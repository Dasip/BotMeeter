import sqlite3
import config
import random


def get_info_on(user_id):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE tid = {}".format(str(user_id)))
    db_result = cursor.fetchone()
    if db_result != None:
        new_result = {}
        keys = ["user_id", "name", "gender", "city", "interest", "prev_pair", "curr_pair"]
        counter = 0
        for i in db_result:
            new_result[keys[counter]] = i
            counter += 1
        db_result = new_result
    conn.close()
    return db_result


def try_find_pair(data):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    current_user = data["tid"]
    prev_user = data["prev_pair"]

    cursor.execute("SELECT * FROM pool WHERE tid != ? AND tid != ?", (current_user, prev_user))
    db_result = cursor.fetchall()
    if len(db_result) > 0:
        new_pair = random.choice(db_result)
        return new_pair
    return None


def add_to_pool(data):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    dataset = (data["tid"], data["prev_pair"])
    cursor.execute("INSERT INTO pool VALUES(?, ?);", dataset)
    conn.commit()
    conn.close()

    new_pair = try_find_pair(data)
    if new_pair == None:
        return True
    else:
        return {"tid": new_pair[0]}


def get_pool():
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pool;")
    result = cursor.fetchall()
    conn.close()
    return result


def delete_from_pool(user_info):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pool WHERE tid = ?", (user_info, ))
    conn.commit()
    conn.close()
    return True


def patch_one_user(data):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()

    for key in data.keys():
        if key != "user_id":
            cursor.execute("UPDATE users set {} = ? where tid = ?".format(key), (data[key], data["user_id"]))

    conn.commit()
    conn.close()
    return True


def add_new_user(data):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()

    dataset = (data["user_id"], data["name"], data["gender"], data["city"], data["interest"], -1, -1)
    cursor.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?);", dataset)
    conn.commit()
    conn.close()
    return True
