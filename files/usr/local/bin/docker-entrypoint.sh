#!/bin/sh

# special case: if first argument is YAML or JSON file -- use it for KV provisioning in background
if (! case "$1" in (*.yml|*.yaml|*.json) false;; esac) && [ -r "$1" ]; then

    kv_file="$1"
    shift

    if [ "$1" = "--force" -o "$1" = "-f" -o "$1" = "--overwrite" ]; then
        force_flag="$1"
	    shift
    fi

    # run provisioning script in background and kill PID 1 if it fails
    (
        trap '' HUP PIPE CHLD
        if ! /usr/local/bin/update-kv.py $force_flag $kv_file; then
            /bin/kill -INT 1
        fi
    )&

fi

# if no command is given, run default command
if [ $# -eq 0 ]; then
    set -- consul agent -server -bootstrap-expect=1 -data-dir=/consul/data -client=0.0.0.0 -ui
fi

# exec consul's entrypoint
exec /usr/local/bin/consul-docker-entrypoint.sh $@
