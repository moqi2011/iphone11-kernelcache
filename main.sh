#!/bin/bash
set -e
python3 main.py rename_and_clean
/bin/bash -c "$(python3 main.py gen_download_cmd)"
python3 main.py rename_and_clean
/bin/bash -c "$(python3 main.py gen_upload_cmd)"
