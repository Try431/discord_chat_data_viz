import pandas as pd
import json
import datetime
import re
import matplotlib.pyplot as plt
from pytz import timezone
import subprocess
import sys
import os
from tzlocal import get_localzone
import numpy as np

from collections import OrderedDict

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f+00:00'
LOCAL_TZ = get_localzone()

JSON_FILES_PATH = "./json_files"
IMAGES_PATH = "./images"

WEEK = ['Mon',
        'Tues',
        'Wed',
        'Thu',
        'Fri',
        'Sat',
        'Sun']

SERVER_NAME = "The Ganja Army and Brad"
TEXT_CHANNELS = "Text Channels"


def export_single_channel_to_json(user_token, channel_id):
    isExist = os.path.exists(JSON_FILES_PATH)
    if not isExist:
        os.makedirs(JSON_FILES_PATH)

    cmd = ["dotnet", "run", "export", "-t", user_token, "-c", channel_id,
           "--format", "Json", "--output", f"../../{JSON_FILES_PATH}"]
    output = subprocess.call(
        cmd, cwd="./DiscordChatExporter/DiscordChatExporter.Cli/")
    if output != 0:
        print("Non-zero exit code for DiscordChatExporter call")

    clean_up_json_filenames()


def export_all_channels_to_json(user_token):
    isExist = os.path.exists(JSON_FILES_PATH)
    if not isExist:
        os.makedirs(JSON_FILES_PATH)

    cmd = ["dotnet", "run", "exportall", "-t", user_token,
           "--format", "Json", "--parallel", "10", "--output", f"../../{JSON_FILES_PATH}"]
    output = subprocess.call(
        cmd, cwd="./DiscordChatExporter/DiscordChatExporter.Cli/")
    if output != 0:
        print("Non-zero exit code for DiscordChatExporter call")

    clean_up_json_filenames()


def clean_up_json_filenames():
    for (_, _, filenames) in os.walk(JSON_FILES_PATH):
        for filename in filenames:
            if "Voice Channels" in filename:
                os.remove(f"{JSON_FILES_PATH}/{filename}")
                continue
            filename_split = filename.split("[")
            new_filename = filename_split[0].strip().replace("- Text Channels -", "-").replace("- Voice Channels -", "-") + ".json"
            os.rename(f"{JSON_FILES_PATH}/{filename}", f"{JSON_FILES_PATH}/{new_filename}")


def grab_messages_from_specified_channel(channel_filename):
    with open(f"{JSON_FILES_PATH}/{channel_filename}", 'r') as f:
        print(f"Adding messages from {JSON_FILES_PATH}/{channel_filename}")
        text_json = json.load(f)
        return text_json.get("messages")


def consolidate_channel_messages():
    messages_list = []

    for filename in os.listdir(JSON_FILES_PATH):
        with open(f"{JSON_FILES_PATH}/{filename}", 'r') as f:
            print(f"Adding messages from {JSON_FILES_PATH}/{filename}")
            text_json = json.load(f)
            messages_list += text_json.get("messages")
    return messages_list


def parse_message_data(messages):
    total_author_distribution = {}
    author_msg_counts = {}
    data = {}
    print("Parsing message data...")
    for m in messages:
        try:
            if m.get("type") == "GuildMemberJoin":
                continue
        except:
            print(m)
        if m.get("author").get("isBot"):
            continue
        timestamp = m.get("timestamp")
        regex = r":[0-9][0-9]\+00:00"
        match = re.search(regex, timestamp)
        if match:
            # massaging timestamp into format we expect in the case there's no
            # millisecond granularity in the timestamp
            timestamp = timestamp[:-6] + ".000+00:00"

        utc_datetime_obj = datetime.datetime.strptime(
            timestamp, TIME_FORMAT).astimezone(timezone('UTC'))
        datetime_obj = utc_datetime_obj.astimezone(LOCAL_TZ)
        weekday = WEEK[datetime_obj.date().weekday()]

        day = str(datetime_obj.date()) + f" {weekday}"
        # utc_day = str(utc_datetime_obj.date()) + f" {weekday}"
        author = m.get("author").get("name")

        # collect day-by-day count per author
        author_msg_counts[author] = author_msg_counts.get(author, 0) + 1
        author_dict = data.get(day, {})
        if not author_dict:
            data[day] = {}
        data[day][author] = data[day].get(author, 0) + 1

    return data


def get_total_per_author_from_messages(messages):
    total_author_distribution = {}
    for m in messages:
        if m.get("type") == "GuildMemberJoin":
            continue
        if m.get("author").get("isBot"):
            continue
        author = m.get("author").get("name")
        author_count = total_author_distribution.get(author, 0)
        total_author_distribution[author] = author_count + 1
    for author in total_author_distribution:
        total_author_distribution[author] = [total_author_distribution[author]]
    return total_author_distribution


def get_highest_msg_count_and_day_per_author(data):
    highest_author_count = {}
    highest_author_day = {}
    for day in data:
        author_day_counts = data[day]
        for author in author_day_counts:
            if author_day_counts[author] > highest_author_count.get(author, 0):
                highest_author_count[author] = author_day_counts[author]
                highest_author_day[author] = day
    data = {}
    for auth in highest_author_count:
        data[highest_author_day[auth]] = {auth: highest_author_count[auth]}
    return data


def get_chattiest_per_day(data):
    chattiest_per_day = {}
    for day in data:
        day_of_data = data[day]
        itemMaxValue = max(day_of_data.items(), key=lambda x: x[1])
        listOfKeys = list()
        # Iterate over all the items in dictionary to find keys with max value
        for key, value in day_of_data.items():
            if value == itemMaxValue[1]:
                listOfKeys.append(key)
        if len(listOfKeys) == 1:
            chattiest_per_day[day] = {listOfKeys[0]: itemMaxValue[1]}
        else:
            shared_chattiest = {}
            for author in listOfKeys:
                shared_chattiest[author] = itemMaxValue[1]
            chattiest_per_day[day] = shared_chattiest
    return chattiest_per_day


def plot_data(json_data, title=None):
    print("Plotting data and creating graph...")
    df = pd.DataFrame(json_data).T
    print(df)
    ax = df.plot(kind="bar", stacked=True, width=0.9, ylabel='Msg Count')

    # adding count total to stacked bars
    bottom = np.zeros(len(df))
    for i, col in enumerate(df.columns):
        ax.bar(
            df.index, df[col], bottom=bottom, label=col)
        bottom += np.array(df[col])
    totals = df.sum(axis=1)
    y_offset = 4
    for i, total in enumerate(totals):
        ax.text(totals.index[i], total + y_offset, round(total), ha='center',
                weight='bold')

    # plt.xlim(right=3)

    # for p in axes.patches:
    #     axes.annotate(str(p.get_height()), xy=(p.get_x(), p.get_height()))
    # for container in ax.containers:
    #     print(container)
    #     ax.bar_label(container, label_type='center')

    fig = plt.gcf()
    if title:
        plt.gcf().suptitle(f"{title}", fontsize=50)
    fig.set_size_inches(200, 30)
    isExist = os.path.exists(IMAGES_PATH)
    if not isExist:
        os.makedirs(IMAGES_PATH)
    print(f"Saving {IMAGES_PATH}/{title}.png...")
    plt.savefig(f"{IMAGES_PATH}/{title}.png", dpi=120)


# Plot Functions

def plot_chattiest_per_day():
    all_channel_msgs = consolidate_channel_messages()
    parsed_data = parse_message_data(all_channel_msgs)
    chattiest = get_chattiest_per_day(parsed_data)
    ordered = OrderedDict(sorted(chattiest.items(), key=lambda t: t[0]))
    plot_data(ordered, "Chattiest")


def plot_single_channel_message_data(channel_name):
    channel_msg = grab_messages_from_specified_channel(
        f"{SERVER_NAME} - {channel_name}.json")
    parsed_data = parse_message_data(channel_msg)
    plot_data(parsed_data, channel_name)


def plot_highest_msg_count_per_day():
    all_channel_msgs = consolidate_channel_messages()
    parsed_data = parse_message_data(all_channel_msgs)
    hpd = get_highest_msg_count_and_day_per_author(parsed_data)
    plot_data(hpd, "Highest Msg Count and Day")
    print(hpd)


def plot_total_msg_count_per_user_all_channels():
    all_channel_msgs = consolidate_channel_messages()
    parsed_data = parse_message_data(all_channel_msgs)
    total = 0
    for d in parsed_data:
        sub_total = sum(parsed_data[d].values())
        total += sub_total
    print(f"Total messages: {total}")

    auth_total_data = get_total_per_author_from_messages(all_channel_msgs)
    print(auth_total_data)
    s = 0
    for k in auth_total_data:
        s += auth_total_data[k][0]
    print(s)
    plot_data(auth_total_data, "Total Msg Count per User")


def plot_all_messages():
    all_channel_msgs = consolidate_channel_messages()
    parsed_data = parse_message_data(all_channel_msgs)
    ordered = OrderedDict(sorted(parsed_data.items(), key=lambda t: t[0]))
    plot_data(ordered, "All Messages")


if __name__ == '__main__':
    # print("Exporting data now...")
    # user_token = sys.argv[1]
    # if len(sys.argv) == 2:
    #     export_all_channels_to_json(user_token)
    # elif len(sys.argv) == 3:
    #     export_single_channel_to_json(user_token, channel_id=sys.argv[2])

    # plot_single_channel_message_data("wuhan")
    # plot_total_msg_count_per_user_all_channels()
    # plot_highest_msg_count_per_day()
    # plot_chattiest_per_day()
    plot_all_messages()
