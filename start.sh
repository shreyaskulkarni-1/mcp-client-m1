#~/bin/bash

# First install dependencies, then run the app
pip3 install -r requirements.txt
python3 client_query.py &
python3 gradio_interface.py

# when I kill this script, it should kill the background process as well
trap "pkill -P $$" EXIT