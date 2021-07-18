import sqlite3
import config
import random
from datetime import datetime


def format_to_dict(data):
    new_result = {}
    keys = ["user_id", "name", "gender", "city", "interest", "prev_pair", "curr_pair", "pair_date"]
    counter = 0
    for i in data:
        new_result[keys[counter]] = i if keys[counter] != "pair_date" else format_date(i)
        counter += 1
    return new_result


def format_date(d):
    if d != "-1":
        d = list(map(int, d.split("-")))
        new_date = datetime(year=d[0], month=d[1], day=d[2], hour=d[3], minute=d[4], second=d[5])
        return new_date
    return "-1"


def get_info_on(user_id):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE tid = {}".format(str(user_id)))
    db_result = cursor.fetchone()
    if db_result != None:
        db_result = format_to_dict(db_result)
    conn.close()
    return db_result


def get_paired():
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE curr_pair != -1")
    db_results = cursor.fetchall()
    if db_results != None:
        new_results = []
        for i in db_results:
            new_results.append(format_to_dict(i))
        db_results = new_results
    conn.close()
    return db_results


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


def is_in_pool(us_id):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pool WHERE tid = {};".format(us_id))
    result = cursor.fetchone()
    conn.close()
    print(f"IN POOL {result}")
    return result != None


def delete_from_pool(user_info):
    conn = sqlite3.connect(config.DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pool WHERE tid = ?", (user_info, ))
    conn.commit()
    conn.close()
    print(f"DELETED FROM POOL {user_info}")
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

    dataset = (data["user_id"], data["name"], data["gender"], data["city"], data["interest"], -1, -1, "-1")
    cursor.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?);", dataset)
    conn.commit()
    conn.close()
    return True

