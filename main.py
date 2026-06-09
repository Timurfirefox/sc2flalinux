#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime

if sys.platform == "win32":
    print("[!] Данная версия программы предназначена только для Linux.")
    print("    Запусти её на Linux-системе.")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

REQUIRED_PACKAGES = [
    "sc_compression",
    "pylzham",
    "typing_extensions",
    "colorama",
    "pillow",
    "numpy",
    "affine6p",
    "lxml",
]


def is_in_venv():
    return sys.prefix != sys.base_prefix


def venv_exists():
    return os.path.isfile(VENV_PYTHON)


def create_venv():
    print("[*] Создаю виртуальное окружение в", VENV_DIR)
    result = subprocess.run([sys.executable, "-m", "venv", VENV_DIR])
    if result.returncode != 0:
        print("[!] Не удалось создать venv. Попробую через python3.")
        result = subprocess.run(["python3", "-m", "venv", VENV_DIR])
    if result.returncode != 0:
        print("[!] Ошибка создания виртуального окружения. Установи python3-venv:")
        print("    sudo apt install python3-venv")
        sys.exit(1)
    print("[+] venv создан.")


def install_packages():
    print("[*] Устанавливаю зависимости...")
    for pkg in REQUIRED_PACKAGES:
        print(f"    pip install {pkg}")
        subprocess.run([VENV_PIP, "install", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[+] Зависимости установлены.")


def relaunch_in_venv():
    print("[*] Перезапускаю скрипт внутри venv...")
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)


if not is_in_venv():
    if not venv_exists():
        create_venv()
        install_packages()
    relaunch_in_venv()


from sc_compression.signatures import Signatures
from sc_compression import Decompressor, Compressor

try:
    from lib import sc_to_fla
    SC_TO_FLA_AVAILABLE = True
except ImportError as e:
    print(f"[!] Warning: sc_to_fla не доступен: {e}")
    SC_TO_FLA_AVAILABLE = False


def print_banner():
    print("="*50)
    print("   SC Tool by SCW Make — sc2flalinux")
    print("   Работа с файлами Supercell (*.sc)")
    print("="*50)


def ask_output_dir(sc_path):
    sc_dir = os.path.dirname(os.path.abspath(sc_path))
    date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    project_output = os.path.join(SCRIPT_DIR, date_str)

    print("\nКуда сохранить результат?")
    print(f"  [1] Рядом со sc-файлом: {sc_dir}")
    print(f"  [2] Папка с датой в корне проекта: {project_output}")
    while True:
        choice = input("Выбери [1/2]: ").strip()
        if choice == "1":
            return sc_dir
        elif choice == "2":
            os.makedirs(project_output, exist_ok=True)
            return project_output
        else:
            print("Введи 1 или 2.")


def cmd_decompile():
    if not SC_TO_FLA_AVAILABLE:
        print("[!] Модуль lib.sc_to_fla не найден. Убедись, что он есть в папке lib/.")
        return

    sc_path = input("Путь к .sc файлу: ").strip().strip("'\"")
    if not sc_path or not os.path.isfile(sc_path):
        print("[!] Файл не найден.")
        return

    if not sc_path.endswith(".sc"):
        print("[!] Файл должен иметь расширение .sc")
        return

    if sc_path.endswith("_tex.sc"):
        print("[!] Нельзя декомпилировать _tex.sc напрямую — выбери основной .sc файл.")
        return

    out_dir = ask_output_dir(sc_path)
    base_name = os.path.basename(sc_path).replace(".sc", ".fla")
    output_path = os.path.join(out_dir, base_name)

    if os.path.exists(output_path):
        ans = input(f"[?] {output_path} уже существует. Перезаписать? [y/N]: ").strip().lower()
        if ans != "y":
            print("[*] Отменено.")
            return

    print("[*] Декомпилируем...")
    try:
        sc_to_fla(sc_path, out_dir)
        if os.path.exists(output_path):
            print(f"[+] Готово! Сохранено: {output_path}")
        else:
            print("[!] Файл .fla не был создан. Возможно, sc_to_fla не поддерживает аргумент out_dir.")
            fallback = sc_path.replace(".sc", ".fla")
            if os.path.exists(fallback):
                import shutil
                shutil.move(fallback, output_path)
                print(f"[+] Перемещено в: {output_path}")
            else:
                print("[!] .fla файл не найден ни рядом с источником, ни в выбранной папке.")
    except TypeError:
        try:
            orig_dir = os.getcwd()
            os.chdir(os.path.dirname(os.path.abspath(sc_path)))
            sc_to_fla(sc_path)
            os.chdir(orig_dir)
            fallback = sc_path.replace(".sc", ".fla")
            if os.path.exists(fallback):
                if fallback != output_path:
                    import shutil
                    shutil.move(fallback, output_path)
                print(f"[+] Готово! Сохранено: {output_path}")
            else:
                print("[!] .fla файл не был создан.")
        except Exception as e:
            print(f"[!] Ошибка при декомпиляции: {e}")
    except Exception as e:
        print(f"[!] Ошибка при декомпиляции: {e}")


def cmd_decompress():
    sc_path = input("Путь к .sc файлу: ").strip().strip("'\"")
    if not sc_path or not os.path.isfile(sc_path):
        print("[!] Файл не найден.")
        return

    out_dir = ask_output_dir(sc_path)
    base_name = os.path.basename(sc_path) + ".dec"
    output_path = os.path.join(out_dir, base_name)

    print("[*] Декомпрессия...")
    try:
        decompressor = Decompressor()
        with open(sc_path, "rb") as f:
            data = f.read()
        clean_data = data.split(b"START")[0]
        decompressed = decompressor.decompress(clean_data)
        with open(output_path, "wb") as f:
            f.write(decompressed)
        print(f"[+] Готово! Сохранено: {output_path}")
    except Exception as e:
        print(f"[!] Ошибка при декомпрессии: {e}")


def cmd_compress():
    file_path = input("Путь к файлу для компрессии: ").strip().strip("'\"")
    if not file_path or not os.path.isfile(file_path):
        print("[!] Файл не найден.")
        return

    out_dir = ask_output_dir(file_path)
    base_name = os.path.basename(file_path) + ".cmp"
    output_path = os.path.join(out_dir, base_name)

    print("[*] Компрессия...")
    try:
        compressor = Compressor()
        with open(file_path, "rb") as f:
            data = f.read()
        compressed = compressor.compress(data, Signatures.SC, 1)
        with open(output_path, "wb") as f:
            f.write(compressed)
        print(f"[+] Готово! Сохранено: {output_path}")
    except Exception as e:
        print(f"[!] Ошибка при компрессии: {e}")


def main():
    print_banner()
    while True:
        print("\nЧто сделать?")
        print("  [1] Decompile .sc → .fla")
        print("  [2] Decompress .sc")
        print("  [3] Compress file")
        print("  [0] Выход")
        choice = input("Выбор: ").strip()
        if choice == "1":
            cmd_decompile()
        elif choice == "2":
            cmd_decompress()
        elif choice == "3":
            cmd_compress()
        elif choice == "0":
            print("Пока!")
            break
        else:
            print("Неверный выбор.")


if __name__ == "__main__":
    main()