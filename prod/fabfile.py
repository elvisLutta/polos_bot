from os import environ
from fabric.api import *
from fabric.context_managers import cd
from fabric.contrib.files import sed

import os
import sys
sys.path.insert(0, '/home/lee/venv/polos_bot/src')
from keys import (SERVER_ROOT_PASSWORD, HOST_LIST, SYSADMIN_FULLNAME,
                  SYSADMIN_GROUP, SYSADMIN_USERNAME, SSH_DIR, SSH_KEYNAME)


'''
    Fabric file to upload public/private keys to remote servers
    and set up non-root users. Also prevent ssh with root user.
'''

# run the bootstrap process as root before it's locked down
env.user = 'root'

# the remote servers root password
env.password = SERVER_ROOT_PASSWORD

# all IP addresses or hostnames of the servers to put the ssh keys
# and authorized host files on.
env.hosts = HOST_LIST

# enter the full name for the new non-root user
env.new_user_full_name = SYSADMIN_FULLNAME

# username for the new non-root user
env.new_user = SYSADMIN_USERNAME

# group name for the new non-root user to be created
env.new_user_group = SYSADMIN_GROUP

# local filesystem directory where your prod_key.pub and
# authorized_keys files are located (they will be scp'd
# to target hosts)
env.ssh_key_dir = SSH_DIR



def bootstrap():
    env.ssh_key_filepath = os.path.join(env.ssh_key_dir, env.host_string + SSH_KEYNAME)
    local('ssh-keygen -t rsa -b 2048 -f {}'.format(env.ssh_key_filepath))
    local('cp {} {}/authorized_keys'.format(env.ssh_key_filepath + ".pub", env.ssh_key_dir))

    sed('/etc/ssh/sshd_config', '^UsePAM yes', 'UsePAM no')
    sed('/etc/ssh/sshd_config', '^PermitRootLogin yes', 'PermitRootLogin no')
    sed('/etc/ssh/sshd_config', '^#PasswordAuthentication yes',
        'PasswordAuthentication no')

    _create_privileged_group()
    _create_privileged_user()
    _upload_keys(env.new_user)
    run('service ssh reload')


def _create_privileged_group():
    run('/usr/sbin/groupadd ' + env.new_user_group)
    run('mv /etc/sudoers /etc/sudoers-backup')
    run('(cat /etc/sudoers-backup ; echo "%' + env.new_user_group \
         + ' ALL=(ALL) ALL") > /etc/sudoers')
    run('chmod 440 /etc/sudoers')


def _create_privileged_user():
    run('/usr/sbin/useradd -c "%s" -m -g %s %s' % \
        (env.new_user_full_name, env.new_user_group, env.new_user))
    run('/usr/bin/passwd %s' % env.new_user)
    run('/usr/sbin/usermod -a -G ' + env.new_user_group + ' ' + env.new_user)
    run('mkdir /home/%s/.ssh' % env.new_user)
    run('chown -R %s /home/%s/.ssh' % (env.new_user, env.new_user))
    run('chgrp -R %s /home/%s/.ssh' % (env.new_user_group, env.new_user))


def _upload_keys(username):
    scp_command = "scp {} {}/authorized_keys {}@{}:~/.ssh".format(
            env.ssh_key_filepath + ".pub",
            env.ssh_key_dir,
            username,
            env.host_string
            )
    local(scp_command)
