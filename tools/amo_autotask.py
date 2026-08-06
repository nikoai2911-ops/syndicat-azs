#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автозадачи: находит активные сделки без открытых задач и ставит каждой
задачу «Связаться» на завтра 18:00 на ответственного по сделке.
Закрывает причину попапа «Запрещено работать без задачи» (виджет F5).

Запуск (руками или по расписанию):
    python3 tools/amo_autotask.py
"""
import datetime
import time

from amo_api import CLOSED_STATUSES, paginate, post


def main():
    with_tasks = set()
    for t in paginate("/tasks", "tasks", "filter[is_completed]=0&filter[entity_type]=leads"):
        with_tasks.add(t["entity_id"])
    print("открытых задач по сделкам:", len(with_tasks))

    no_task_leads = []
    for lead in paginate("/leads", "leads"):
        if lead["status_id"] in CLOSED_STATUSES:
            continue
        if lead["id"] not in with_tasks:
            no_task_leads.append(lead)
    print("активных сделок без задач:", len(no_task_leads))
    if not no_task_leads:
        return

    tomorrow = datetime.datetime.now().replace(hour=18, minute=0, second=0) + datetime.timedelta(days=1)
    due_ts = int(tomorrow.timestamp())
    batch = [{
        "task_type_id": 1,
        "text": "Разобрать сделку: связаться и квалифицировать (автозадача)",
        "complete_till": due_ts,
        "entity_id": lead["id"],
        "entity_type": "leads",
        "responsible_user_id": lead["responsible_user_id"],
    } for lead in no_task_leads]

    for i in range(0, len(batch), 50):
        post("/tasks", batch[i:i + 50])
        time.sleep(0.3)
    print("поставлено задач:", len(batch))


if __name__ == "__main__":
    main()
