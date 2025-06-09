#!/bin/bash
#
source /home/user/openValves/venv/bin/activate

python3 /home/user/openValves/valveControl.py >> /home/user/openValves/irrigation.log 2>&1
