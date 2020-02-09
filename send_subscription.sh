#!/bin/bash

# activate venv
source /var/physaci_subscriber/.venv/bin/activate

# call subscription console script
physaci_send_subscription

# deactivate venv
deactivate
