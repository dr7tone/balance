"""Работа с CSV: формирование экспорта и разбор импорта (UTF-8, разделитель ';')."""
import csv
import io
from datetime import date, datetime

TYPE_ALIASES = {
    "income": "income", "доход": "income", "доходы": "income", "+": "income",
    "1": "income",
    "expense": "expense", "расход": "expense", "расходы": "expense",
    "-": "expense", "0": "expense",
}
HEADER = ["Дата", "Тип", "Сумма", "Категория", "Комментарий"]


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def build_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for r in rows:
        writer.writerow([
            r["date"], r["type"],
            f"{r['amount']:.2f}".replace(".", ","),
            r["category"], r["comment"],
        ])
    return buf.getvalue()


def parse_csv(text: str) -> tuple[list[dict], list[str]]:
    """Возвращает (валидные строки, описания ошибок)."""
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows: list[dict] = []
    errors: list[str] = []
    line_no = 0
    first_row = True
    for raw in reader:
        line_no += 1
        if first_row:
            first_row = False
            # пропускаем строку заголовка (шапка экспорта)
            if raw and raw[0].strip().lower() in ("дата", "date"):
                continue
        if not raw or not any(cell.strip() for cell in raw):
            continue
        if len(raw) < 4:
            errors.append(f"Строка {line_no}: недостаточно полей")
            continue
        date_str, type_str, amount_str = raw[0].strip(), raw[1].strip(), raw[2].strip()
        category_str = raw[3].strip() if len(raw) > 3 else ""
        comment_str = raw[4].strip() if len(raw) > 4 else ""

        d = _parse_date(date_str)
        if d is None:
            errors.append(f"Строка {line_no}: неверная дата «{date_str}»")
            continue
        op_type = TYPE_ALIASES.get(type_str.lower())
        if op_type is None:
            errors.append(f"Строка {line_no}: неверный тип «{type_str}»")
            continue
        try:
            amount = float(amount_str.replace(",", "."))
        except ValueError:
            errors.append(f"Строка {line_no}: неверная сумма «{amount_str}»")
            continue
        if amount <= 0:
            errors.append(f"Строка {line_no}: сумма должна быть больше нуля")
            continue
        rows.append({"date": d, "type": op_type, "amount": amount,
                     "category": category_str, "comment": comment_str})
    return rows, errors
