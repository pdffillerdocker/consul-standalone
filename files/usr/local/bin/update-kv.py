#!/usr/local/bin/python3

import os
import sys
import signal
import time
import argparse
import re
import json
import yaml
import consul

# ===========================
# === Ignore some signals ===
# ===========================

signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGCHLD, signal.SIG_IGN)


# =======================
# === Misc. functions ===
# =======================

def strtr(s: str, repl: dict) -> str:
    """Replace substrings in 's' matching 'repl' keys with corresponging values
    """
    pattern = '|'.join(map(re.escape, sorted(repl, key=len, reverse=True)))
    if repl:
        return re.sub(pattern, lambda m: repl[m.group()], s)
    else:
        return s


# ===========================
# === Setup configuration ===
# ===========================

parser = argparse.ArgumentParser(
        description='Update consul KV from a file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser_group = parser.add_mutually_exclusive_group()
parser_group.add_argument(
        '-y', '--yaml',
        dest='yaml_only',
        action='store_true',
        help='consider KV file only as YAML')
parser_group.add_argument(
        '-j', '--json',
        dest='json_only',
        action='store_true',
        help='consider KV file only as JSON')

parser.add_argument(
        '-s', '--subst', '--substitute',
        dest='subst',
        type=str,
        default=os.environ.get("UPDATEKV_VARIABLES"),
        metavar='VARNAME,...',
        help='comma-separated list of env var names to substitute '
             'in KV file (supersedes UPDATEKV_VARIABLES env variable)')

parser.add_argument(
        '-t', '--timeout',
        dest='timeout',
        type=int,
        default=20,
        help='time in seconds to wait for consul to up')

parser.add_argument(
        '-f', '--force', '--overwrite',
        dest='overwrite',
        action='store_true',
        help='if to overwrite values for existing keys')

parser.add_argument(
        'kv_file',
        type=argparse.FileType('r'),
        metavar='FILE',
        help='file containing KV to update (YAML or JSON)')

args = parser.parse_args()

CONFIG_OVERWRITE = args.overwrite   # If overwrite values for present keys
CONFIG_TIMEOUT = args.timeout       # Time in seconds to wait for consul to up
CONFIG_KV_FILE = args.kv_file.name  # KV file name
CONFIG_KV_FILE_LINES = args.kv_file.read()  # KV file lines
CONFIG_YAML_ONLY = args.yaml_only   # Consider KV file only as YAML
CONFIG_JSON_ONLY = args.json_only   # Consider KV file only as JSON
CONFIG_SUBSTITUTIONS = {}           # Dictionary of substitutions

#
# Fill CONFIG_SUBSTITUTIONS
#     from 'subst' argument (defaults to UPDATEKV_VARIABLES env variable
#     contents)
#     'subst' argument should be comma-separated list
#     of environment variables names

if args.subst is not None:

    for varname in list(filter(
            None,
            map(
                lambda x: x.strip(),
                str(os.environ.get("UPDATEKV_VARIABLES")).split(",")
            ))):
        if os.environ.get(varname) is not None:
            CONFIG_SUBSTITUTIONS.setdefault(
                    f'${varname}$',
                    str(os.environ.get(varname)))


# ==================
# === Main logic ===
# ==================

#
# Substitute

kv_lines = strtr(CONFIG_KV_FILE_LINES, CONFIG_SUBSTITUTIONS)

#
# Parse

parsed = False
kv = {}

if not parsed and not CONFIG_YAML_ONLY:
    try:
        kv = json.loads(kv_lines)
    except ValueError:
        pass
    else:
        parsed = True

if not parsed and not CONFIG_JSON_ONLY:
    try:
        kv = yaml.load(kv_lines, Loader=yaml.FullLoader)
    except yaml.YAMLError:
        pass
    else:
        parsed = True

#
# KV file content checks

if not parsed:
    err_msg = f"file '{CONFIG_KV_FILE}' contains no valid "

    if CONFIG_JSON_ONLY:
        err_msg += 'JSON'
    elif CONFIG_YAML_ONLY:
        err_msg += 'YAML'
    else:
        err_msg += 'JSON nor YAML'
    print(f'Error: {err_msg}', file=sys.stderr)
    sys.exit(1)

if type(kv) != dict:
    err_msg = 'invalid KV file content: should be plain JSON object or YAML ' \
              'associative array with strings, integers or booleans as values'
    print(f'Error: {err_msg}', file=sys.stderr)
    sys.exit(2)

for k, v in kv.items():
    if (
            type(k) != str
            or (
                type(v) != str
                and type(v) != int
                and type(v) != bool
                )
            ):
        err_msg = 'invalid KV file content: should be plain JSON object ' \
                  'or YAML associative array with strings, integers or ' \
                  'booleans as values'

        if type(k) == str:
            err_msg += f" (wrong value type for key '{k}')"

        print(f'Error: {err_msg}', file=sys.stderr)
        sys.exit(2)

#
# Wait for consul

print(f'Waiting for consul to up (for max {CONFIG_TIMEOUT} seconds)..',
      end='', flush=True)

consul_is_up = False
c = consul.Consul()
start_time = time.time()
curr_time = start_time

while (curr_time <= start_time + CONFIG_TIMEOUT):
    try:
        consul_leader = c.status.leader()
    except Exception:
        print('.', end='', flush=True)
        time.sleep(.2)
    else:
        if consul_leader:
            consul_is_up = True
            print('consul is up!')
            break
        else:
            print('.', end='', flush=True)
            time.sleep(.2)
    finally:
        curr_time = time.time()

if not consul_is_up:
    print('FAIL!')
    err_msg = f'consul is not up for {CONFIG_TIMEOUT} seconds'
    print(f'Error: {err_msg}', file=sys.stderr)
    sys.exit(3)

#
# Update KV

for k, v in kv.items():
    index, data = c.kv.get(k)
    if data is None:
        print(f"Creating key '{k}'...", end='', flush=True)
        c.kv.put(k, str(v))
        print('DONE')
    elif CONFIG_OVERWRITE:
        print(f"Updating key '{k}'...", end='', flush=True)
        c.kv.put(k, str(v))
        print('DONE')
    else:
        print(f"Skipping key '{k}' as is exist")

print('All DONE!')
sys.exit(0)
