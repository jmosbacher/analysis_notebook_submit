import click
import paramiko
import getpass
import webbrowser
import os
import time
import sys

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SCRIPT_NAME = "start_jupyter_modified.py"
SCRIPT_PATH = os.path.join(SCRIPT_DIR, SCRIPT_NAME)

KNOWN_NODES = {
"dali": "dali-login1.rcc.uchicago.edu",
"midway": "midway2.rcc.uchicago.edu",
}



def line_buffered(f):
    line_buf = b""
    while not f.channel.exit_status_ready():
        line_buf += f.read(1)
        if line_buf.endswith(b'\n'):
            yield line_buf.decode().strip()
            line_buf = b''

def auth_handler(title, instructions, prompt_list):
    answers = []
    if title:
        print(title.strip())
    if instructions:
        print(instructions.strip())
    for prompt, show_input in prompt_list:
        if "password" in prompt.strip().lower():
            answer = getpass.getpass(prompt.strip())
        else:
            answer = input(prompt.strip())
        answers.append(answer)
    return answers

def do_2fa(ssh, username):
    transport = ssh.get_transport()
    transport.auth_interactive(username=username, handler=auth_handler)

def upload_script(ssh):
    ftp_client=ssh.open_sftp()
    click.echo("Uploading job script...")
    ftp_client.put(SCRIPT_PATH, SCRIPT_NAME)
    ftp_client.close()


@click.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.option("--username", default=getpass.getuser(), help="UCC Chicago user name")
@click.option("--password", prompt=False, hide_input=True, help="UCC Chicago user name")
@click.option("--server", default="dali", help="Login node, can be 'dali' or 'midway' or explicit address.")
@click.argument('scipt_args', nargs=-1, type=click.UNPROCESSED)
def main(username, password, server,scipt_args):
    """Performs the tedious tasks of
     1) logging in to midway.
     2) submitting a notebook script.
     3) tunneling through to the machine running the job.
     4) opening a browser.
     All from the comfort of your own home.
     Any extra parameters are passed on to the standard submission script.
     """
    
    if server in KNOWN_NODES:
        server = KNOWN_NODES[server]
    ssh = paramiko.SSHClient()
    # k = paramiko.RSAKey.from_private_key_file(f"{home}/.ssh/id_rsa")
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(server, username=username, auth_timeout=10)
    except paramiko.AuthenticationException as e:
        # password = getpass.getpass("Password: ")password=password,
        try:
            ssh.connect(server, username=username,  auth_timeout=60)
        except paramiko.AuthenticationException:
            do_2fa(ssh, username)
        
    upload_script(ssh)

    cmd_to_execute = "python {} {}".format(SCRIPT_NAME, " ".join(scipt_args))
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)
    ssh_stdin.close()
    lines = []
    for line in line_buffered(ssh_stdout):
        if "{" in line:
            click.echo("Done. adding ssh tunnel.")
            params = eval(line)
            os.system("ssh -fN -L {port}:{ip}:{port} {username}@{host}".format(**params, host=server))
            break
        else:
            click.echo(line)
    
    click.echo("Browser should open automatically. If not, browse to: http://localhost:{port}/?token={token}".format(**params))
    click.echo("Happy strax analysis!")
    webbrowser.open("http://localhost:{port}/?token={token}".format(**params))
    ssh.close()
    sys.exit(0)
    

if __name__ == '__main__':
    main()