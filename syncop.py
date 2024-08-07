import hashlib
import json
import shutil
import sys
import os
import subprocess
import argparse
import logging
import platform
from _hashlib import HASH as Hash
from pathlib import Path
from typing import Union, Dict, List, Tuple

HASH_FILE = "dump_hash.json"
LINUX_PATH = os.path.expanduser("~/bin")
WINDOWS_PATH = os.getenv("APPDATA", "")


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def copy_script_to_path(os_platform: str) -> Path:
    script_path = Path(os.path.abspath(__file__))
    script_name = script_path.name
    target_path = Path(LINUX_PATH) / script_name

    if os_platform == "Windows":
        target_path = Path(WINDOWS_PATH) / script_name

    if script_path != target_path:
        logging.info(f"Copying script to {target_path}.")
        shutil.copy2(script_path, target_path)
        os.chmod(target_path, 0o755)
    else:
        logging.info(f"Script already present in {target_path}.")

    return target_path


def check_scheduled_task(task_name: str) -> bool:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        capture_output=True,
        text=True,
        shell=True,
    )
    return task_name in result.stdout


def create_sheduled_task(command: str) -> None:
    logging.info("Creating sheduled task.")
    schtask_line = f"schtasks /create {command}"
    try:
        subprocess.run(schtask_line, shell=True, check=True)
        logging.info(f"Sheduled -{schtask_line}- task created.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create sheduled task: {e}")
        if e.returncode == 1:
            logging.error("Permission denied. Run script as Administrator.")
    except Exception as e:
        logging.error(f"An unexpected error occcured: {e}")


def check_cron_job(command: str) -> bool:
    logging.info("Checking cron job presence.")
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return command in result.stdout


def create_cron_job(command: str, cron_interval: str) -> None:
    logging.info("Creating cron job.")
    cron_line = f"{cron_interval} {command}"
    subprocess.run(f'echo "{cron_line}" | crontab', shell=True, check=True)
    logging.info(f"Cron job {cron_line} created.")


def setup_cronjob(
    source_name: Path, replica_name: Path, interval: int, logs: Path
) -> None:
    logging.info("Starting syncop setup.")
    logging.info("Detecting operating system platform.")
    os_platform = platform.system()
    cron_interval = ""

    if interval < 1 or interval > 59:
        logging.info("Wrong interval [1 > interval or interval > 59].")
        logging.info("Cron job timer set up  to 1 hour.")
        cron_interval = "* * * * *"
    else:
        logging.info(f"Cron job set up to each {interval} minutes.")
        cron_interval = f"*/{interval} * * * *"
    script_path = copy_script_to_path(os_platform)

    if os_platform == "Windows":
        logging.info("Windows system detected.")
        task_name = f"syncop-{source_name.name}"
        if check_scheduled_task(task_name):
            logging.info(f"{task_name} already created.")
        else:
            command = f'/tn {task_name} /tr "python3 -s {source_name} -r {replica_name} -i {interval} -l {logs}" /sc minute /mo {interval}'
            create_sheduled_task(command)
    elif os_platform == "Linux":
        logging.info("Linux system detected.")
        command = f"python3 {script_path} -s {source_name} -r {replica_name} -i {interval} -l {logs}"

        if check_cron_job(command):
            logging.info("Cronjob already exist.")
            return
        else:
            logging.info("Cron job not found.")
            create_cron_job(command, cron_interval)

    logging.info("syncop setup finished.")


def file_hash(file_path: Union[str, Path]) -> Hash:
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5()
        while chunck := file.read(4096):
            file_hash.update(chunck)

    return file_hash.hexdigest()


def dir_hash(dir_path: Path) -> Dict[str, Hash]:
    dir_abspath = str(Path.cwd() / dir_path)
    logging.info(f"Generating hash for files in {dir_abspath} direcotry.")
    assert dir_path.is_dir()
    hashes = {}
    hashes[dir_abspath] = {}
    for path in sorted(dir_path.iterdir(), key=lambda p: str(p).lower()):
        path_key = str(Path.cwd() / path)
        if path.is_file():
            hashes[dir_abspath][path_key] = file_hash(path)
        elif path.is_dir():
            hashes[dir_abspath][path_key] = list(dir_hash(path).values())[0]

    return hashes


def json_compare(
    json1: Dict, json2: Dict, changes: List = [], missing: List = []
) -> Tuple[List, List]:
    for key in json1.keys():
        if key in json2.keys():
            if isinstance(json1[key], dict):
                json_compare(json1[key], json2[key], changes, missing)
            else:
                if json1[key] != json2[key]:
                    changes.append(key)
        else:
            missing.append(key)

    return changes, missing


def append_operations(
    deleted: List, created: List, updated: List, source_name: str, replica_name: str
) -> None:

    for item in deleted:
        path = str(item)
        path = path.replace(str(source_name), str(replica_name))
        if Path(path).is_file():
            logging.warning(f"Removing file: {path}")
            Path(path).unlink()
        else:
            logging.warning(f"Removing directory: {path}")
            shutil.rmtree(path)

    for item in created:
        path = str(item)
        path = path.replace(str(source_name), str(replica_name))
        if Path(item).is_file():
            logging.warning(f"Creating file: {path}")
            shutil.copy2(item, path)
        else:
            logging.warning(f"Creating folder: {path}")
            new_dir = Path(path)
            new_dir.mkdir(parents=True, exist_ok=True)

    for item in updated:
        path = str(item)
        path = path.replace(str(source_name), str(replica_name))
        if Path(path).is_file():
            logging.warning(f"Updating file: {path}")
            shutil.copy2(item, path)
        else:
            logging.warning(f"Updating folder: {path}")
            new_dir = Path(path)
            new_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # [-s SOURCE] [-r REPLICA] [-i INTERVAL] [-l LOGS]
    parser.add_argument("-s", "--source", help="Source directory path.")
    parser.add_argument("-r", "--replica", help="Replica directory path.")
    parser.add_argument(
        "-i", "--interval", help="Interval for script execution in minutes.", type=int
    )
    parser.add_argument("-l", "--logs", help="Log file path.")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    for arg, value in vars(args).items():
        if value is None:
            logging.error(f"{arg} value not provided.")
            parser.print_help(sys.stderr)
            sys.exit(1)

    source_name = Path.cwd() / args.source
    replica_name = Path.cwd() / args.replica

    setup_logging(args.logs)
    setup_cronjob(source_name, replica_name, args.interval, args.logs)

    source_hashes = dir_hash(source_name)
    logging.info(f"Starting synchronization for {source_name} -> {replica_name}")
    config_file = Path(f"{replica_name}/{HASH_FILE}")
    logging.info(f"Looking for {replica_name}/{HASH_FILE} file.")
    dump_json = {}

    if config_file.is_file():
        logging.info(f"Found {replica_name}/{HASH_FILE}, reading it.")
        with open(config_file, "r") as config:
            dump_json = json.load(config)
    else:
        logging.warning(f"Cannot find {replica_name}/{HASH_FILE} file.")

    if replica_name.is_dir() and not config_file.is_file():
        logging.info(f"Found {replica_name} directory.")
        logging.info(f"Generating hashes for files in {replica_name} directory.")
        dump_json = dir_hash(replica_name)

    if not replica_name.is_dir():
        logging.info(f"Directory {replica_name} not found.")
        logging.warning(f"Start copying content of {source_name} into {replica_name}")
        try:
            shutil.copytree(Path(source_name), Path(replica_name))
            logging.info(f"Copied directory from {source_name} to {replica_name}.")
        except FileNotFoundError as e:
            logging.error(f"Failed to copy directory: {e}")
            logging.error("Please check if the source directory exists.")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
        with open(config_file, "w") as config:
            logging.info(f"Saving files hashes into {replica_name}/{HASH_FILE}")
            json.dump(source_hashes, config, indent=4)
        logging.info(
            f"Copying of content from {source_name} to {replica_name} finished. Synchronization done."
        )
        sys.exit()

    nl = "\n"
    logging.info("Looking for new and updated files and directories.")
    updated, created = json_compare(source_hashes, dump_json)

    if created:
        logging.info(f"Created: {nl.join([str(i) for i in created])}")
    if updated:
        logging.info(f"Updated: {nl.join([str(i) for i in updated])}")

    logging.info("Looking for deleted files and directories.")
    _, deleted = json_compare(dump_json, source_hashes, changes=[], missing=[])

    if deleted:
        logging.info(f"Deleted: {nl.join([str(i) for i in deleted])}")

    append_operations(deleted, created, updated, source_name, replica_name)

    with open(config_file, "w") as config:
        logging.info(f"Saving new files hashes into {replica_name}/{HASH_FILE}")
        json.dump(source_hashes, config, indent=4)

    logging.info(f"Synchronization of {source_name} -> {replica_name} done.")
