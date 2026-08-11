# Cache Cleaner

Cache Cleaner is a Windows app for quickly cleaning temporary files and cache from common programs.

## Quick Start

The easiest way to launch the app is to use the ready-made executable:

```text
dist\cache_clear.exe
```

No Python installation is required for this version.

## What It Cleans

- Windows temporary files
- Adobe cache for After Effects, Premiere Pro, Photoshop, and Media Encoder
- Discord cache
- Browser cache for Chrome, Firefox, Edge, Brave, and Yandex Browser

## How To Use

1. Open `dist\cache_clear.exe`
2. Select what you want to clean
3. Optionally choose an extra Adobe cache folder
4. Click the cleanup button
5. Wait for the result window

Cleanup details are saved to `clear_cache_log.txt`.

## Important

- Run the app with administrator rights if Windows asks for permission
- Close browsers, Discord, and Adobe apps before cleanup
- The deleted cache files are removed permanently

## For Developers

If you want to run the source code instead of the executable:

```bat
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python cache_clear.py
```

## Build EXE

To rebuild the executable:

```bat
pip install pyinstaller
pyinstaller cache_clear.spec
```

The built file will appear in `dist\cache_clear.exe`.

## Author

[sweetenerbae](https://github.com/sweetenerbae)
