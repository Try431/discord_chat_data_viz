import pandas as pd
import json
import datetime
import re
import matplotlib.pyplot as plt
from dateutil import tz
from pytz import timezone
import subprocess
import sys

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f+00:00'
LOCAL_TZ = tz.tzlocal()

WEEK = ['Mon',
        'Tues',
        'Wed',
        'Thu',
        'Fri',
        'Sat',
        'Sun']


def export_json(user_token):
    # dotnet_cmd = "cd DiscordChatExporter/DiscordChatExporter.Cli/ && dotnet run"
    # create json_files dir
    cmd = ["dotnet", "run", "export", "-t", user_token,
           "--format", "Json", "--parallel", "10", "--output", "../../json_files", "--channel", "682821942977364007"]
    output = subprocess.call(
        cmd, cwd="./DiscordChatExporter/DiscordChatExporter.Cli/")
    print(output)


def collect_data_from_json():
    overall_author_dict = {}
    date_data = {}
    with open("jay-hates-his-friends.json", "r") as f:
        text_json = json.load(f)
        author_counts = {}
        channel_title = text_json.get("channel").get("name")
        for m in text_json.get("messages"):
            # skip messages that weren't sent by actual people
            if m.get("type") == "GuildMemberJoin":
                continue
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
            datetime_obj = utc_datetime_obj.astimezone(timezone('US/Central'))
            weekday = WEEK[datetime_obj.date().weekday()]

            day = str(datetime_obj.date()) + f" {weekday}"
            # utc_day = str(utc_datetime_obj.date()) + f" {weekday}"

            author = m.get("author").get("name")
            author_counts[author] = author_counts.get(author, 0) + 1
            author_dict = date_data.get(day, {})

            # initialize sub-dict
            if not author_dict:
                date_data[day] = {}
            date_data[day][author] = date_data[day].get(author, 0) + 1

            # collect overall author distribution
            author = m.get("author").get("name")
            author_count = overall_author_dict.get(author, 0)
            overall_author_dict[author] = author_count + 1

    print(overall_author_dict)
    return date_data, channel_title


def plot_data(json_data, channel_title):
    df = pd.DataFrame(json_data).T
    df.plot(kind="bar", stacked=True, width=0.9)
    fig = plt.gcf()
    plt.gcf().suptitle(f"Channel: {channel_title}", fontsize=30)
    fig.set_size_inches(200, 20)
    plt.savefig("sized.png", dpi=120)


if __name__ == '__main__':
    # data, title = collect_data_from_json()
    # plot_data(data, channel_title=title)
    if len(sys.argv[1:]) > 0:
        user_token = sys.argv[1]
        export_json(user_token)

    # collect_data_from_json()
    # plot_data()
