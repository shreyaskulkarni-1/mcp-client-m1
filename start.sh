#~/bin/bash

# First install dependencies, then run the app
pip install -r requirements.txt
python client_query.py &
python3 gradio_interface.py

# when I kill this script, it should kill the background process as well
trap "pkill -P $$" EXIT