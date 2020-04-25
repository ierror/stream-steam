Get Started
===========


Prerequisites
-------------

* `Python <http://www.python.org/>`_ >= 3.6
* `pip <https://pip.pypa.io/en/stable/installing/>`_ (python package manager)
* AWS account
* `ipinfo.io <https://ipinfo.io/>`_  account if you want to use geocoding (IP to user's geo info) (probably yes)
* `userstack <https://userstack.com/>`_ account if you want to use device detection (Useragent to device info) (probably yes)


Installation
------------

* Fork the project and run git clone as always e.g.

.. code-block:: bash

    git clone git@github.com:ierror/stream-steam.git

* Install pipenv globally e.g.

.. code-block:: bash

    pip3 install pipenv

* Install project dependencies. pipenv takes care of creating the virtualenv for you - omit the `--dev` flag for installations in production environments

.. code-block:: bash

    pipenv install --dev --python python3.7

* Activate the created virtualenv

.. code-block:: bash

    pipenv shell


Configuration
-------------

* Configure the project

.. code-block:: bash

    ./stream-steam config

* Deploy it!

.. code-block:: bash

    ./stream-steam deploy

* Describe your deployment

.. code-block:: bash

    ./stream-steam describe-deployment

* Run the Webtracking Demo

.. code-block:: bash

    ./stream-steam demo-tracking-web

After 60s you can inspect the enriched events in your S3 Bucket (S3BucketName)

.. code-block:: bash

    /events/enriched/...

* Run the ios Demo

.. code-block:: bash

    ./stream-steam demo-tracking-ios

* Run the Android Demo

.. code-block:: bash

    ./stream-steam demo-tracking-android


* Destroy it!

.. code-block:: bash

    ./stream-steam destroy

Whats next?
-----------

## Moudules

    ./stream-steam module list

### Redash

    ./stream-steam module enable --name redash

... TODO

