#!/bin/bash
#
# wrapper.sh: because supervisor.d doesn't like multi step commands

. /var/www/goblin/shared/env/bin/activate
/var/www/goblin/current/bin/celeryd start

