# Goblin

We use this program to migrate inboxes from Cyrus to Google Mail.

## Features

### Scalable architecture
Celery queue driven interface for managing tasks. You can match the number of workers to the 
queue size and reduce turnaround time.

### Django Webapp
Easily modified Django frontend allows users to prepare themselves and begin migration on
their own terms.

### Presynchronization
Nightly bulk pre-sync for faster migrations.

### Task generation script
Python script to generate bulk task sets for presync or final sync.

### LDAP integration
Queries LDAP for inboxes to sync.

## Installation

We rely on Memcached, PostgreSQL, and a celery MQ as backend datastores. To install,
git clone this repo, make a new virtualenv and then pip install requirements/requirements.txt

Then set up a WSGI file pointing at the repo, and run celery workers.

## Configuration
TODO

## Usage

TODO
 - document bulk task generation script

## Contributing
Patches welcome!

