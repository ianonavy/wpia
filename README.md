WPIA
====

Name's a work in progress. Simple course management software for the masses.

Installing
----------

Preferably in a virtual environment, run

    pip install -r requirements.txt
    cp config.py.example config.py
    $EDITOR config.py  # replace all the values
    python2 manager.py init
    python2 manager.py migrate
    python2 manager.py upgrade

Running
-------

python2 server.py


