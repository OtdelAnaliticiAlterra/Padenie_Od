from pathlib import Path

# --- Пути ---
BASE_DIR = Path(__file__).resolve().parent

SQL_DIR = BASE_DIR / "sql"
OUTPUT_DIR = BASE_DIR / "Новый_файл"
TEMPLATES_DIR = BASE_DIR / "Шапка"
PREVIOUS_DIR = BASE_DIR / "Старый_файл"

OUTPUT_DIR.mkdir(exist_ok=True)
PREVIOUS_DIR.mkdir(exist_ok=True)

SQL_FILE = SQL_DIR / "report.sql"
TEMPLATE_FILE = TEMPLATES_DIR / "header_template.xlsx"

# ... остальное без изменений

OUTPUT_DIR.mkdir(exist_ok=True)
PREVIOUS_DIR.mkdir(exist_ok=True)

SQL_FILE = SQL_DIR / "report.sql"
TEMPLATE_FILE = TEMPLATES_DIR / "header_template.xlsx"

# --- Периоды ---
PERIOD_MONTHS = 2
PERIOD_START_DAY = 26
PERIOD_END_DAY = 25

# --- Куда писать данные в шаблоне ---
DATA_START_ROW = 9
DATA_START_COL = 1   # A

# --- Форматы чисел ---
MONEY_COLUMNS = [
    "Выручка период сравнения",
    "Выручка текущий период",
    "Выручка третий период",
    "Абсолютный прирост",
    # блок N:U
    "Прошлый период",
    "Период",
    "Период дополнительный",
]

PERCENT_COLUMNS = [
    "Относительный прирост",
    "Относительный прирост, %",
]

# --- Соответствие "новая колонка (N:U)": "старая колонка (F:M)" ---
LOOKUP_MAP = {
    "Прошлый период":           "Выручка период сравнения",
    "Период":                   "Выручка текущий период",
    "Период дополнительный":    "Выручка третий период",
    "Абсолютный прирост":       "Абсолютный прирост",
    "Относительный прирост, %": "Относительный прирост",
    "Падение":                  "Падение",
    "Мероприятия":              "Мероприятия",
    "Результат":                "Результат",
}

# --- Второй заход: заполнить T:U нового, если пусто ---
# Берём из старого файла колонки по позиции (0-based):
#   T старого = 19, U старого = 20
LOOKUP_FALLBACK_BY_INDEX = {
    "Мероприятия": 19,
    "Результат":   20,
}