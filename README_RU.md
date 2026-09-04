<div align="center">
  <img src="assets/cache_cleaner_logo.png" width="112" alt="Логотип Cache Cleaner">

  # Cache Cleaner

  **Современная Windows-утилита для поиска и безопасной очистки временных файлов и кэша приложений.**

  [![Платформа](https://img.shields.io/badge/платформа-Windows-1674EA?style=flat-square&logo=windows11)](https://www.microsoft.com/windows)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

  [English](README.md) · [Русский](README_RU.md) · [Скачать EXE](https://github.com/sweetenerbae/cache-cleaner/raw/refs/heads/main/dist/cache_clear.exe)
</div>

---

## Интерфейс

### Главный экран

![Главный экран Cache Cleaner с диаграммой](docs/images/cache-cleaner-dashboard.png)

<details>
  <summary><strong>Другие скриншоты</strong></summary>
  <br>

  **Центр создания и восстановления бэкапов**

  ![Центр восстановления Cache Cleaner](docs/images/cache-cleaner-backups.png)

  **Результат очистки**

  ![Результат очистки в Cache Cleaner](docs/images/cache-cleaner-cleanup-result.png)
</details>

## Возможности

- Сканирование кэша до удаления файлов
- Круговая диаграмма с разделением по категориям
- Очистка временных файлов Windows
- Очистка кэша Adobe и Discord
- Поддержка Chrome, Firefox, Edge, Brave и Яндекс Браузера
- Создание ZIP-бэкапа перед очисткой и последующее восстановление
- Точное отображение очищенного и оставшегося объёма
- Отчёт о файлах, заблокированных Windows или запущенными программами
- Современный адаптивный тёмный интерфейс

## Быстрый запуск

1. [Скачайте `cache_clear.exe`](https://github.com/sweetenerbae/cache-cleaner/raw/refs/heads/main/dist/cache_clear.exe).
2. Запустите скачанный файл.
3. Подтвердите запрос Windows на права администратора.
4. Выберите категории и нажмите **Сканировать** или **Начать очистку**.

Для готового EXE устанавливать Python не нужно. Windows SmartScreen может показать предупреждение, потому что файл пока не подписан цифровым сертификатом.

> Перед очисткой закройте браузеры, Discord и приложения Adobe. Файлы, которые сейчас использует Windows или другая программа, будут безопасно пропущены.

## Что очищается

| Категория | Расположение |
|---|---|
| Windows | Пользовательские временные файлы, `Windows\Temp`, Prefetch |
| Adobe | Media Cache, Media Cache Files и выбранная папка кэша |
| Discord | Cache, Code Cache, GPUCache |
| Браузеры | Кэш Chrome, Firefox, Edge, Brave и Яндекс Браузера |

## Бэкапы и приватность

Если включена защита, перед очисткой Cache Cleaner создаёт ZIP-архив. Бэкапы хранятся только на компьютере пользователя:

```text
%LOCALAPPDATA%\CacheCleaner\backups
```

Логи работы и файлы бэкапов исключены из Git и при обычных коммитах не загружаются в репозиторий.

## Запуск из исходного кода

```bat
git clone https://github.com/sweetenerbae/cache-cleaner.git
cd cache-cleaner
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Сборка EXE

Запустите безопасный скрипт сборки:

```bat
build_exe.bat
```

Он собирает приложение отдельно, ждёт закрытия запущенного Cache Cleaner и помещает результат в `dist\cache_clear.exe`.

## Структура проекта

```text
main.py              Точка запуска приложения
gui_builder.py       Основной интерфейс и диаграмма
cleanup_logic.py     Сканирование и очистка
backup_system.py     Создание и восстановление бэкапов
restore_window.py    Интерфейс управления бэкапами
utils.py             Пути Windows и общие модели данных
```

## Автор

Разработчик — [sweetenerbae](https://github.com/sweetenerbae).
