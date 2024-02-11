import pymongo
from openai import OpenAI
from datetime import datetime, timedelta
import time
import os

select_max_houre_ago = 1
select_last_log_count = 10

api_key = os.environ.get("OPENAI_API_KEY", None)
if api_key:
    client = OpenAI(
        api_key=api_key,
    )

db = os.environ.get("DB", "127.0.0.1")
mongo_client = pymongo.MongoClient(f"mongodb://{db}:27017/")
db = mongo_client["O3"]
attacks_collection = db["ATTACKS"]
reports_collection = db["REPORTS"]


def analyze_logs(logs):
    log_text = "\n".join(str(log["content"]) for log in logs)
    message = f"What is the target goal of the following attacker logs? \n LOGS:```{log_text}``` \n"
    print(message)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": message,
            }
        ],
        model="gpt-3.5-turbo",
    )

    target_goal = chat_completion.data.choices[0].message
    return target_goal


def generate_report(target_goal, logs):
    report = f"Report for Target Goal:\n {target_goal}\n\n"

    for idx, log in enumerate(logs, 1):
        report += f"Log {idx}:\n"
        report += f"  IP: {log['ip']}\n"
        report += f"  Time: {log['time']}\n"
        report += f"  Data: {log['content']}\n"
        report += f"  Detector: {log['detector']}\n\n"

    return report


while True:
    current_time = datetime.now()
    one_hour_ago = current_time - timedelta(hours=select_max_houre_ago)

    have_un_read_log = attacks_collection.count_documents({
        "time": {"$gte": one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")},
        "read": {"$ne": True}
    })

    if have_un_read_log == 0:
        time.sleep(10)
        print("NO NEW LOG")
        continue

    logs_within_last_hour = list(attacks_collection.find({
        "time": {"$gte": one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")},
        "read": {"$ne": True}
    }).limit(select_last_log_count))

    if logs_within_last_hour:
        print("NEW REPORT")

        target_goal = analyze_logs(logs_within_last_hour) if api_key else "-"
        report = generate_report(target_goal, logs_within_last_hour)

        report_data = {
            "target_goal": target_goal,
            "logs": logs_within_last_hour,
            "report_text": report,
            "timestamp": time.time()
        }

        reports_collection.insert_one(report_data)

        for log in logs_within_last_hour:
            attacks_collection.update_one(
                {"_id": log["_id"]}, {"$set": {"read": True}})

    time.sleep(60)
