#!/usr/bin/env python
# vim: autoindent tabstop=4 expandtab shiftwidth=4 softtabstop=4

"""
Backup borker

Run this inside a git repository with hourly snapshots.
"""

from datetime import datetime, timedelta
import os
import re
import subprocess
import sys

my_environ = {
    'GIT_AUTHOR_NAME': 'borkbak',
    'GIT_AUTHOR_EMAIL': 'borkbak@feinheit.ch',
    'GIT_COMMITTER_NAME': 'borkbak',
    'GIT_COMMITTER_EMAIL': 'borkbak@feinheit.ch',
    }

for key in ('PWD', 'PATH'):
    my_environ[key] = os.environ.get(key, '')


def borkbak():
    backups = get_backups()

    occupied = set()

    now = datetime.now()

    keep = []

    for tree_id, timestamp, original_timestamp in backups:
        days = (now - timestamp).days

        if days > 100:
            # only keep monthly snapshots for backups older than 100 days
            key = timestamp.strftime('monthly-%Y-%m')
        elif days > 30:
            # only keep weekly snapshots for backups older than 30 days
            key = timestamp.strftime('weekly-%Y-%W')
        elif days > 7:
            # only keep daily snapshots for backups older than 7 days
            key = timestamp.strftime('daily-%Y-%m-%d')
        else:
            # keep all newer snapshots
            key = unicode(timestamp)

        if key in occupied:
            continue

        occupied.add(key)
        keep.append((tree_id, timestamp, original_timestamp, key))

    commit_id = None
    items = len(keep)

    print 'Recreating history for selected backups...'

    for idx, (tree_id, timestamp, original_timestamp, key) in enumerate(keep):
        commit_id = create_commit(tree_id, original_timestamp, key, commit_id)

        sys.stdout.write('\r%s/%s' % (idx+1, items))
        sys.stdout.flush()

    ref = 'refs/heads/borkbak'
    p = subprocess.call(['git', 'update-ref', ref, commit_id])
    print '\nUpdated ref %s.' % ref


def create_commit(tree_id, timestamp, key, parent=None):
    args = ['git', 'commit-tree', tree_id]
    if parent:
        args.extend(['-p', parent])
    my_environ['GIT_COMMITTER_DATE'] = timestamp
    my_environ['GIT_AUTHOR_DATE'] = timestamp
    p = subprocess.Popen(args, env=my_environ, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ret = p.communicate('Backup %s' % key)[0]
    return ret.strip()


def get_backups():
    p = subprocess.Popen(['git', 'log', '--format=%T %ct'], stdout=subprocess.PIPE)
    output = p.communicate()[0]

    LOG_RE = re.compile(r'(?P<tree_id>.{40}) (?P<timestamp>\d+)$')

    ret = []
    for line in output.splitlines():
        matches = LOG_RE.search(line)
        if not matches:
            continue

        ret.append((
            matches.group('tree_id'),
            datetime.fromtimestamp(int(matches.group('timestamp'))),
            matches.group('timestamp'),
            ))

    return reversed(ret)



if __name__ == '__main__':
    borkbak()

