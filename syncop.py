#!/usr/bin/env python3

import hashlib
import json
import shutil
import sys
import argparse
import logging
from _hashlib import HASH as Hash
from pathlib import Path
from typing import Union, Dict, List 

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def file_hash(file_path: Union[str, Path]) -> Hash:
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5()
        while chunck := file.read(4096):
            file_hash.update(chunck)

    logging.info(f"Generating hash for {file_path.name}: {file_hash.hexdigest()}")
    return file_hash.hexdigest()


def dir_hash(dir_path: Union[str, Path]) -> Dict[str, Hash]:
    logging.info(f"Generating hash for files in {dir_path.name}")
    assert dir_path.is_dir()
    dir_path = dir_path.resolve()
    hashes = {}
    dir_key = str(Path.cwd() / dir_path)
    hashes[dir_key] = {}
    for path in sorted(dir_path.iterdir(), key=lambda p: str(p).lower()):
        path_key = str(Path.cwd() / path)
        if path.is_file():
            hashes[dir_key][path_key] = file_hash(path)
        elif path.is_dir():
            hashes[dir_key][path_key] = list(dir_hash(path).values())[0]

    return hashes


# def dir_hash(dir_path: Union[str, Path]) -> Dict[str, Hash]:
#    assert dir_path.is_dir()
#    dir_path = dir_path.resolve()
#    hashes = {}
#    hashes[dir_path.name] = {}
#    for path in sorted(dir_path.iterdir(), key=lambda p: str(p).lower()):
#        if path.is_file():
#            hashes[dir_path.name][path.name] = file_hash(path)
#        elif path.is_dir():
#            hashes[dir_path.name][path.name] = list(dir_hash(path).values())[0]
#
#    return hashes


# def json_compare(json1, json2, changes=[], missing=[], base=""):
#    # Compare all keys
#    for key in json1.keys():
#        # if key exist in json2:
#        new_base = f"{base}/{key}" if base else key
#        if key in json2.keys():
#            # If subjson
#            if type(json1[key]) == dict:
#                json_compare(json1[key], json2[key], changes, missing, new_base)
#            else:
#                if json1[key] != json2[key]:
#                    # print("These entries are different:")
#                    # print(f"{key}: {json1[key]}/{json2[key]}")
#                    changes.append(new_base)
#        else:
#            # print(f"found new item: {key}:{json1[key]}")
#            missing.append(new_base)
#    return changes, missing


def json_compare(json1: Dict, json2: Dict, changes: List=[], missing: List=[]) -> Union[List, List]:
    # Compare all keys
    for key in json1.keys():
        # if key exist in json2:
        if key in json2.keys():
            # If subjson
            if type(json1[key]) is dict:
                json_compare(json1[key], json2[key], changes, missing)
            else:
                if json1[key] != json2[key]:
                    # print("These entries are different:")
                    # print(f"{key}: {json1[key]}/{json2[key]}")
                    changes.append(key)
        else:
            # print(f"found new item: {key}:{json1[key]}")
            missing.append(key)
    return changes, missing


def append_operations(deleted: List, created: List, update: List, source_name: str, replica_name: str) -> None:
    
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
    parser.add_argument("-i", "--interval", help="Interval for script execution in minutes.", type=int)
    parser.add_argument("-l", "--logs", help="Log file path.")

    args = parser.parse_args()

    if len(sys.argv) == 1:
            parser.print_help(sys.stderr)
            sys.exit(1)

    setup_logging(args.logs)
    
    source_name = Path.cwd() / args.source
    replica_name = Path.cwd() / args.replica
    source_hashes = dir_hash(source_name)
    logging.info(f"Starting synchronization for {source_name} -> {replica_name}")

    config_file = Path(f"{replica_name}/sync_config.json")

    logging.info(f'Looking for {replica_name}/dump_config.json file.')
    if config_file.is_file():
        logging.info(f"Found {replica_name}/dump_config.json, loading it.")
        config_json = {}
        with open(config_file, "r") as config:
            config_json = json.load(config)
    else:
        logging.warning(f'Cannot find {replica_name}/dump_config.json file.')
        logging.warning(f'Start copying content of {source_name} into {replica_name}')
        shutil.copytree(Path(source_name), Path(replica_name))
        with open(config_file, "w") as config:
            logging.info(f'Saving files hashes into {replica_name}/dump_config.json')
            json.dump(source_hashes, config, indent=4)
        sys.exit()

    nl = "\n"

    logging.info('Looking for new and updated files and directories.')
    updated, created = json_compare(source_hashes, config_json)
    
    if created:
        logging.info(f'Created: {nl.join([str(i) for i in created])}')
    if updated:
        logging.info(f'Updated: {nl.join([str(i) for i in updated])}')

    logging.info('Looking for deleted files and directories.')
    _, deleted = json_compare(config_json, source_hashes, changes=[], missing=[])
    
    if deleted:
        logging.info(f'Deleted: {nl.join([str(i) for i in deleted])}')

    append_operations(deleted, created, updated, source_name, replica_name)

    with open(config_file, "w") as config:
        logging.info(f'Saving new files hashes into {replica_name}/dump_config.json')
        json.dump(source_hashes, config, indent=4)
