"""
Работа с облаком Алтерра (API v1).

Документация: https://cloud.tg-alterra.ru/api/v1
"""

import requests
from pathlib import Path

import config


API_BASE_URL = "https://cloud.tg-alterra.ru/api/v1"


# ---------------------------------------------------------------------------
# Служебное
# ---------------------------------------------------------------------------

def _get_headers() -> dict:
    if not config.CLOUD_API_TOKEN:
        raise ValueError("Не задан CLOUD_API_TOKEN в config.py")
    return {
        "Authorization": f"Bearer {config.CLOUD_API_TOKEN}",
        "Accept": "application/json",
    }


def _list_all_files(folder_id: int) -> list[dict]:
    """
    Возвращает все файлы в папке (с обходом пагинации).
    """
    url = f"{API_BASE_URL}/files"
    files = []
    page = 1

    while True:
        response = requests.get(
            url,
            headers=_get_headers(),
            params={"folder_id": folder_id, "page": page, "per_page": 100},
        )
        response.raise_for_status()
        payload = response.json()
        files.extend(payload.get("data", []))

        meta = payload.get("meta", {})
        if page >= meta.get("last_page", 1):
            break
        page += 1

    return files


# ---------------------------------------------------------------------------
# Поиск прошлого отчёта
# ---------------------------------------------------------------------------

def find_previous_report_in_folder(folder_id: int, search_name: str) -> dict | None:
    """
    Ищет в папке все файлы, чьё имя содержит search_name и заканчивается на .xlsx.
    Возвращает ПОСЛЕДНИЙ по id файл (самый свежий по загрузке).

    Логика: в папке облака лежит накопительная история отчётов.
    Скрипт запускается раз в месяц, и на каждом запуске прошлым отчётом
    является самый свежий файл, загруженный в прошлый раз.
    """
    files = _list_all_files(folder_id)

    needle = search_name.lower().replace(".xlsx", "")
    matches = [
        f for f in files
        if needle in f.get("name", "").lower()
        and f.get("name", "").lower().endswith(".xlsx")
    ]

    if not matches:
        return None

    # Сортируем по id по убыванию и берём первый — самый свежий
    matches.sort(key=lambda f: f["id"], reverse=True)
    chosen = matches[0]

    print(f"Выбран прошлый отчёт: {chosen['name']} (ID={chosen['id']})")
    return chosen


# ---------------------------------------------------------------------------
# Скачивание / загрузка / удаление
# ---------------------------------------------------------------------------

def download_file(file_id: int, destination_path: Path) -> None:
    """Скачивает файл по его ID и сохраняет по указанному пути."""
    url = f"{API_BASE_URL}/files/{file_id}/download"
    response = requests.get(url, headers=_get_headers(), stream=True)
    response.raise_for_status()

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    with open(destination_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Файл скачан: {destination_path}")


def upload_file(local_path: Path, folder_id: int, remote_name: str | None = None) -> dict:
    """Загружает локальный файл в указанную папку облака."""
    url = f"{API_BASE_URL}/files"

    with open(local_path, "rb") as f:
        files = {"file": (remote_name or local_path.name, f)}
        data = {"folder_id": folder_id}
        if remote_name:
            data["name"] = remote_name

        response = requests.post(
            url,
            headers=_get_headers(),
            files=files,
            data=data,
        )
        response.raise_for_status()

    payload = response.json()
    return payload.get("data")


def delete_file(file_id: int) -> None:
    """Удаляет файл по ID (перемещает в корзину)."""
    url = f"{API_BASE_URL}/files/{file_id}"
    response = requests.delete(url, headers=_get_headers())
    if response.status_code not in (204, 200):
        response.raise_for_status()
    print(f"Файл с ID {file_id} удалён из облака.")