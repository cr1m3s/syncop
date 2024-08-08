# syncop
Program that synchronizes two folders: source and replica.

Folder paths, synchronization interval and log file path should be provided
using the command line arguments:

`python3 /home/user/bin/syncop.py -s /home/user/Code -r /home/user/code_dump -i 1 -l /home/user/logs.txt`

Synchronization performed periodically:

-- For Linux used crontab. Expected interval in minutes: 1-59. If an interval outside this range is provided, it will default to 1 hour.

-- For Windows used scheduled task [Requires Administrator priviledges]. Script able to create task, but task don't work [at least on the test machine].

File creation/copying/removal operations logged to a file and to the console output:

```
2024-08-06 22:04:08 - INFO - Starting syncop setup.
2024-08-06 22:04:08 - INFO - Detecting operating system platform.
2024-08-06 22:04:08 - INFO - Cron job set up to each 1 minutes.
2024-08-06 22:04:08 - INFO - Linux system detected.
2024-08-06 22:04:08 - INFO - Script already present in /home/user/bin/syncop.py.
2024-08-06 22:04:08 - INFO - Checking cron job presence.
2024-08-06 22:04:08 - INFO - Cron job not found.
2024-08-06 22:04:08 - INFO - Creating cron job.
...
2024-08-07 20:58:22 - INFO - Starting synchronization for /home/user/Code -> /home/cr1m3s/code_dump
2024-08-07 20:58:22 - INFO - Looking for /home/user/code_dump/dump_hash.json file.
2024-08-07 20:58:22 - INFO - Found /home/user/code_dump/dump_hash.json, reading it.
2024-08-07 20:58:22 - INFO - Looking for new and updated files and directories.
2024-08-07 20:58:22 - INFO - Looking for deleted files and directories.
2024-08-07 20:58:22 - INFO - Saving new files hashes into /home/user/code_dump/dump_hash.json
2024-08-07 20:58:22 - INFO - Synchronization of /home/user/Code -> /home/cr1m3s/code_dump done.
```
