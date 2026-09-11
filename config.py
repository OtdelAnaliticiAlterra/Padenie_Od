from pathlib import Path

# --- Пути ---
BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Отчёт ---
SQL_FILE = SQL_DIR / "report.sql"

# Период: начало текущего периода. Меняется здесь.
CURRENT_START = (2026, 6, 26)   # (год, месяц, день)
PERIOD_MONTHS = 2               # длина периода в месяцах

# Имя файла-шаблона (если будем использовать шаблон Excel)
OUTPUT_FILENAME_TEMPLATE = "Отчет_дистрибуция_{start}_{end}.xlsx"

# --- Форматирование отчёта ---
MONEY_COLUMNS = [
    "Выручка период сравнения",
    "Выручка текущий период",
    "Выручка третий период",
    "Абсолютный прирост",
]
PERCENT_COLUMNS = ["Относительный прирост"]