Use pre-configured .py and .env files to keep certain model's configs and reuse. A pair of files is needed, naming convention `<template_name>.py` and `<template_name>.env`. Sample claude37 templates provided

To run within virtual env (assuming you created one under .venv) you need to use venv's Python binary: `.venv/bin/python run_templates/claud37.py`

To quickly test if the script works, you can limit the number of repetitions to 1: `.venv/bin/python run_templates/claud37.py -n 1`

## Cron Setup
Add to crontab (`crontab -e`):
```bash
# Run daily at 3 AM (min hour day month weekday)
0 3 * * * cd /path/to/project/root && .venv/bin/python run_templates/claud37.py
```
Replace `/path/to/project/root` with your actual project path.
Time format: `0 3 * * *` means run at minute 0 of 3rd hour (3 AM) every day.

Checking cron system logs: `sudo grep CRON /var/log/syslog`
