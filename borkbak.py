#!/usr/bin/env python
# vim: autoindent tabstop=4 expandtab shiftwidth=4 softtabstop=4

"""
Backup borker

Run this inside a git repository with hourly snapshots.
"""

from datetime import datetime, timedelta
import optparse
import os
import re
import subprocess
import sys

MY_ENVIRON = {
    'GIT_AUTHOR_NAME': 'borkbak',
    'GIT_AUTHOR_EMAIL': 'borkbak@feinheit.ch',
    'GIT_COMMITTER_NAME': 'borkbak',
    'GIT_COMMITTER_EMAIL': 'borkbak@feinheit.ch',
    }

for key in ('PWD', 'PATH'):
    MY_ENVIRON[key] = os.environ.get(key, '')


def borkbak():
    parser = optparse.OptionParser()
    parser.add_option('', '--ref', dest='ref',
        help='Set ref to create/update [default: %default]',
        default='refs/heads/borkbak')
    parser.add_option('-q', '--quiet', dest='verbose', action='store_false',
        help='Do not print status messages',
        default=True)
    parser.add_option('', '--prune', dest='prune',
        help='Prune unreachable objects',
        default=False)
    options, args = parser.parse_args()
    if args:
        parser.error('Don\'t try argu(ment)ing with me')

    # keys which have been used (generated using commit timestamps)
    occupied = set()
    # trees which should be preserved and strung using newly created commits
    keep = []

    now = datetime.now()

    for tree_id, timestamp, original_timestamp in get_backups():
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
            key = timestamp.strftime('original-%Y-%m-%d-%H-%M')

        if key in occupied:
            continue
        occupied.add(key)

        keep.append((tree_id, timestamp, original_timestamp, key))

    if options.verbose:
        print 'Recreating history for selected backups...'

    # first commit has no parent
    commit_id = None
    items = len(keep)

    for idx, (tree_id, timestamp, original_timestamp, key) in enumerate(keep):
        commit_id = create_commit(tree_id, original_timestamp, key, commit_id)

        if options.verbose:
            sys.stdout.write('\r%s/%s' % (idx+1, items))
            sys.stdout.flush()

    p = subprocess.call(['git', 'update-ref', options.ref, commit_id])
    if options.verbose:
        print '\nUpdated ref %s.' % options.ref


def create_commit(tree_id, timestamp, key, parent=None):
    args = ['git', 'commit-tree', tree_id]
    if parent:
        args.extend(['-p', parent])
    MY_ENVIRON['GIT_COMMITTER_DATE'] = timestamp
    MY_ENVIRON['GIT_AUTHOR_DATE'] = timestamp
    p = subprocess.Popen(args, env=MY_ENVIRON, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ret = p.communicate('%s\n' % key)[0]
    return ret.strip()


def get_backups():
    # we only need the commit's tree and timestamp from the old history
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

