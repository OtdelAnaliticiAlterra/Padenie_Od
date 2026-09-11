"""
Основной скрипт формирования отчёта по падению продаж ОД.

Что делает:
  1. Считает 3 периода от текущей даты (26 → 25, окно 2 месяца).
  2. Читает старый отчёт из папки previous/ (единственный .xlsx).
  3. Выполняет SQL из sql/report.sql с параметрами периодов.
  4. Делает "ВПР" #1 в pandas: тянет F:M старого в N:U нового по ключу 'Ключ'.
  5. Делает "ВПР" #2 (fallback): тянет T и U старого в T и U нового,
     но только в те ячейки, которые остались пустыми после шага 4.
  6. Открывает Excel-шаблон templates/header_template.xlsx.
  7. Пишет:
       - подписи периодов в шапку (F6, G6, H6),
       - данные SQL в A9:K{last},
       - значения из старого отчёта в N9:U{last},
       - fallback в T9:U{last} (только в пустые),
       - 0 и #Н/Д оставляет пустыми.
  8. Сохраняет результат в output/Отчет_дистрибуция_<период>.xlsx
  9. Удаляет старый файл из previous/.
"""

from datetime import date
from dateutil.relativedelta import relativedelta

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

import config
from db import run_query


# ---------------------------------------------------------------------------
# Периоды
# ---------------------------------------------------------------------------

def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d 00:00:00.000")


def _label(d1: date, d2: date) -> str:
    return f"{d1:%d.%m.%Y} - {(d2 - relativedelta(days=1)):%d.%m.%Y}"


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def build_period_params() -> dict:
    today = date.today()
    start_day = config.PERIOD_START_DAY
    months = config.PERIOD_MONTHS

    cur_end = today.replace(day=start_day)
    start_month = _first_day_of_month(today) - relativedelta(months=months)
    cur_start = start_month.replace(day=start_day)

    prev_start = cur_start - relativedelta(years=1)
    prev_end = cur_end - relativedelta(years=1)

    fut_start = prev_start + relativedelta(months=months)
    fut_end = prev_end + relativedelta(months=months)

    return {
        "cur_start":  _fmt(cur_start),
        "cur_end":    _fmt(cur_end),
        "prev_start": _fmt(prev_start),
        "prev_end":   _fmt(prev_end),
        "fut_start":  _fmt(fut_start),
        "fut_end":    _fmt(fut_end),
        "period_label": _label(cur_start, cur_end),
        "prev_label":   _label(prev_start, prev_end),
        "future_label": _label(fut_start, fut_end),
    }


# ---------------------------------------------------------------------------
# Запрос к БД
# ---------------------------------------------------------------------------

def fetch_data(params: dict) -> pd.DataFrame:
    sql = config.SQL_FILE.read_text(encoding="utf-8")
    result = run_query(sql, params)
    df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df


# ---------------------------------------------------------------------------
# Старый отчёт
# ---------------------------------------------------------------------------

def load_previous_report() -> pd.DataFrame:
    files = list(config.PREVIOUS_DIR.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(
            f"В папке {config.PREVIOUS_DIR} нет .xlsx файлов. "
            f"Положи туда старый отчёт."
        )
    if len(files) > 1:
        raise RuntimeError(
            f"В папке {config.PREVIOUS_DIR} должно быть ровно один .xlsx. "
            f"Найдено: {[f.name for f in files]}"
        )

    path = files[0]
    print(f"Читаю старый отчёт: {path.name}")

    df_prev = pd.read_excel(path, header=7)
    df_prev = df_prev.dropna(how="all")
    return df_prev


def build_lookup(df: pd.DataFrame, df_prev: pd.DataFrame) -> pd.DataFrame:
    """
    VLOOKUP #1: F:M старого → N:U нового по ключу 'Ключ'.
    """
    prev_value_cols = list(config.LOOKUP_MAP.values())

    missing = [c for c in prev_value_cols if c not in df_prev.columns]
    if missing:
        raise KeyError(
            f"В старом отчёте не найдены колонки: {missing}\n"
            f"Доступные колонки: {list(df_prev.columns)}"
        )

    prev_slim = (
        df_prev[["Ключ"] + prev_value_cols]
        .drop_duplicates(subset="Ключ", keep="first")
        .set_index("Ключ")
    )

    result = prev_slim.reindex(df["Ключ"]).reset_index(drop=True)
    result.columns = list(config.LOOKUP_MAP.keys())
    return result


def build_lookup_fallback(df: pd.DataFrame, df_prev: pd.DataFrame) -> pd.DataFrame:
    """
    VLOOKUP #2: T и U старого (по индексам) → T и U нового.
    Используется только для пустых ячеек после VLOOKUP #1.
    """
    key_col = "Ключ"

    max_idx = max(config.LOOKUP_FALLBACK_BY_INDEX.values())
    if len(df_prev.columns) <= max_idx:
        raise IndexError(
            f"В старом отчёте только {len(df_prev.columns)} колонок, "
            f"а нужен индекс {max_idx}. Проверь структуру старого файла."
        )

    fallback = pd.DataFrame({
        new_name: df_prev.iloc[:, idx]
        for new_name, idx in config.LOOKUP_FALLBACK_BY_INDEX.items()
    })
    fallback[key_col] = df_prev[key_col].values

    fallback = (
        fallback
        .drop_duplicates(subset=key_col, keep="first")
        .set_index(key_col)
    )

    result = fallback.reindex(df["Ключ"]).reset_index(drop=True)
    return result[list(config.LOOKUP_FALLBACK_BY_INDEX.keys())]


def delete_previous_file():
    for f in config.PREVIOUS_DIR.glob("*.xlsx"):
        f.unlink()
        print(f"Удалён старый отчёт: {f.name}")


# ---------------------------------------------------------------------------
# Сохранение в Excel
# ---------------------------------------------------------------------------

def save_excel(
    df: pd.DataFrame,
    df_lookup: pd.DataFrame,
    df_fallback: pd.DataFrame,
    params: dict,
) -> str:
    period_for_name = params["period_label"].replace(" ", "").replace(".", "")
    filename = f"Отчет_дистрибуция_{period_for_name}.xlsx"
    out_path = config.OUTPUT_DIR / filename

    wb = load_workbook(config.TEMPLATE_FILE)
    ws = wb.active

    start_row = config.DATA_START_ROW
    start_col = config.DATA_START_COL
    lookup_start_col = 14  # N

    # 1. Подписи периодов
    ws["F6"] = params["prev_label"]
    ws["G6"] = params["period_label"]
    ws["H6"] = params["future_label"]

    ZERO_AS_EMPTY = {
        "Выручка период сравнения",
        "Выручка текущий период",
        "Выручка третий период",
        "Абсолютный прирост",
        "Относительный прирост",
        "Прошлый период",
        "Период",
        "Период дополнительный",
        "Относительный прирост, %",
    }

    def is_empty(v):
        if v is None:
            return True
        if isinstance(v, float) and pd.isna(v):
            return True
        return False

    def clean(value, col_name):
        if col_name in ZERO_AS_EMPTY and value == 0:
            return None
        if is_empty(value):
            return None
        if isinstance(value, str) and value.strip() in ("#Н/Д", "#N/A", ""):
            return None
        return value

    # 2. A..K
    for r_offset, row in enumerate(df.itertuples(index=False)):
        for c_offset, col_name in enumerate(df.columns):
            ws.cell(
                row=start_row + r_offset,
                column=start_col + c_offset,
                value=clean(row[c_offset], col_name),
            )

    # 3. N..U (VLOOKUP #1)
    for r_offset in range(len(df_lookup)):
        for c_offset, col_name in enumerate(df_lookup.columns):
            ws.cell(
                row=start_row + r_offset,
                column=lookup_start_col + c_offset,
                value=clean(df_lookup.iat[r_offset, c_offset], col_name),
            )

    # 4. T..U fallback (только в пустые)
    fallback_target_cols = {
        "Мероприятия": 20,  # T
        "Результат":   21,  # U
    }
    for new_col_name, target_col in fallback_target_cols.items():
        if new_col_name not in df_fallback.columns:
            continue
        src = df_fallback[new_col_name]
        for r_offset in range(len(df_fallback)):
            cell = ws.cell(row=start_row + r_offset, column=target_col)
            if cell.value not in (None, ""):
                continue
            value = clean(src.iat[r_offset], new_col_name)
            if value is not None:
                cell.value = value

    if len(df) == 0:
        wb.save(out_path)
        return str(out_path)

    last_data_row = start_row + len(df) - 1

    # 5. Форматы чисел
    col_map = {}
    for i, name in enumerate(df.columns):
        col_map[name] = start_col + i
    for i, name in enumerate(df_lookup.columns):
        col_map[name] = lookup_start_col + i

    for col_name in config.MONEY_COLUMNS:
        if col_name in col_map:
            col_idx = col_map[col_name]
            for r in range(start_row, last_data_row + 1):
                ws.cell(row=r, column=col_idx).number_format = '#,##0.00'

    for col_name in config.PERCENT_COLUMNS:
        if col_name in col_map:
            col_idx = col_map[col_name]
            for r in range(start_row, last_data_row + 1):
                ws.cell(row=r, column=col_idx).number_format = '0.00"%"'

    # 6. Автоширина
    target_cols = (
        list(range(start_col, start_col + len(df.columns)))
        + list(range(lookup_start_col, lookup_start_col + len(df_lookup.columns)))
    )
    for col_idx in target_cols:
        letter = get_column_letter(col_idx)
        header_val = ws.cell(row=start_row - 1, column=col_idx).value
        max_len = len(str(header_val)) if header_val else 0
        for r in range(start_row, last_data_row + 1):
            v = ws.cell(row=r, column=col_idx).value
            if v is not None:
                max_len = max(max_len, len(str(v)))
        ws.column_dimensions[letter].width = min(max_len + 2, 40)

    # 7. Автофильтр + закрепление
    ws.auto_filter.ref = f"A{start_row - 1}:U{last_data_row}"
    ws.freeze_panes = f"A{start_row}"

    wb.save(out_path)
    return str(out_path)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    params = build_period_params()

    print("Периоды:")
    print(f"  Текущий:   {params['period_label']}")
    print(f"  Прошлый:   {params['prev_label']}")
    print(f"  Дополнит.: {params['future_label']}")
    print()

    print("Читаю старый отчёт...")
    df_prev = load_previous_report()

    print("Выполняю запрос к БД...")
    df = fetch_data(params)
    print(f"Получено строк: {len(df)}")


    df_lookup = build_lookup(df, df_prev)


    df_fallback = build_lookup_fallback(df, df_prev)

    path = save_excel(df, df_lookup, df_fallback, params)
    print(f"Готово: {path}")

    # delete_previous_file()


if __name__ == "__main__":
    main()