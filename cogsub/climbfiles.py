import paramiko
import logging 
import os 

class ClimbFiles():

    def __init__(self, climb_file_server, climb_username):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        k = paramiko.RSAKey.from_private_key_file("/home/ubuntu/.ssh/id_rsa")
        try:
            ssh.connect(climb_file_server, username=climb_username)
        except paramiko.ssh_exception.SSHException:
            k = paramiko.RSAKey.from_private_key_file("/home/ubuntu/.ssh/id_rsa")
            ssh.connect(climb_file_server, username=climb_username, pkey=k)
        self.sftp = ssh.open_sftp() 

    def create_climb_dir(self, dir_name):
        try:
            self.sftp.stat(dir_name)
        except FileNotFoundError:
            logging.debug(f'dir {dir_name} on remote not found, creating')
            self.sftp.mkdir(dir_name)
        return dir_name

    def put_file(self, filename, path):
        remote_file_path = os.path.join(path, os.path.basename(filename))
        try:
            self.sftp.stat(remote_file_path)
        except FileNotFoundError:
            logging.debug(f'sending file {filename}')
            self.sftp.put(filename, remote_file_path) 
        return remote_file_path
