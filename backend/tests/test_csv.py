# -*- coding: utf-8 -*-
"""Тесты утилит работы с CSV."""
from app.services.csv_utils import build_csv, parse_csv


def test_build_csv_format():
    text = build_csv([{"date": "2026-10-05", "type": "доход", "amount": 100.5,
                       "category": "Зарплата", "comment": "октябрь"}])
    lines = text.strip().splitlines()
    assert lines[0] == "Дата;Тип;Сумма;Категория;Комментарий"
    assert lines[1] == "2026-10-05;доход;100,50;Зарплата;октябрь"


def test_parse_csv_valid():
    text = "Дата;Тип;Сумма;Категория;Комментарий\n" \
           "2026-11-01;расход;500;Транспорт;билет\n" \
           "01.11.2026;доход;1000,50;Подработка;\n"
    rows, errors = parse_csv(text)
    assert len(rows) == 2
    assert rows[0]["type"] == "expense"
    assert rows[1]["amount"] == 1000.5
    assert errors == []


def test_parse_csv_invalid():
    text = ("Дата;Тип;Сумма;Категория;Комментарий\n"
            "bad-date;расход;500;Транспорт;билет\n"
            "2026-11-01;неизвестно;500;Кат;\n"
            "2026-11-01;расход;-5;Кат;\n")
    rows, errors = parse_csv(text)
    assert rows == []
    assert len(errors) == 3
