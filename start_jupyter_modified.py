#!/usr/bin/env python
from __future__ import print_function
import argparse
import tempfile
import time
import os.path as osp
import shutil

import random
import string
import os
import sys
import subprocess

parser = argparse.ArgumentParser(
    description='Start a strax jupyter notebook server on the dali batch queue')
parser.add_argument('--copy_tutorials', 
    action='store_true',
    help='Copy tutorials to ~/strax_tutorials (if it does not exist)')
parser.add_argument('--partition',
    default='xenon1t', type=str,
    help="RCC/DALI partition to use. Try dali, broadwl, or xenon1t.")
parser.add_argument('--timeout', 
    default=120, type=int,
    help='Seconds to wait for the jupyter server to start')
parser.add_argument('--cpu', 
    default=1, type=int, 
    help='Number of CPUs to request.')
parser.add_argument('--ram',
    default=4480, type=int,
    help='MB of RAM to request')
parser.add_argument('--conda_path', 
    default='<INFER>',
    help="For non-singularity environments, path to conda binary to use."
         "Default is to infer this from running 'which conda'.")
parser.add_argument('--gpu', 
    action='store_true', default=False,
    help='Request to run on a GPU partition. Limits runtime to 2 hours.')
parser.add_argument('--env', 
    default='nt_singularity',
    help='Environment to activate; defaults to "nt_singularity" '
         'to load XENONnT singularity container. '
         'Other arguments are passed to "conda activate" '
         "(and don't load a container).")
parser.add_argument('--container', 
    default='osgvo-xenon:latest',
    help='Singularity container to load'
         'See wiki page https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:dsg:computing:environment_tracking'
         'Default container: "latest"')
args = parser.parse_args()
n_cpu = args.cpu
s_container = args.container

if args.copy_tutorials:
    dest = osp.expanduser('~/strax_tutorials')
    if osp.exists(dest):
        print("NOT copying tutorials, folder already exists")
        sys.stdout.flush()
    else:
        shutil.copytree(
            '/dali/lgrandi/strax/straxen/notebooks/tutorials',
            dest)


jupyter_job = """#!/bin/bash
#SBATCH --job-name=straxlab
#SBATCH --output={log_fn}
#SBATCH --error={log_fn}
#SBATCH --account=pi-lgrandi
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpu}
#SBATCH --mem-per-cpu={mem_per_cpu}
#SBATCH --time={max_hours}:00:00
{extra_header}

echo Starting jupyter job

"""

gpu_header = """\
#SBATCH --partition=gpu2
#SBATCH --gres=gpu:1

module load cuda/9.1
"""

cpu_header = """\
#SBATCH --qos {partition}
#SBATCH --partition {partition}
#SBATCH --reservation=xenon_notebook
""".format(partition=args.partition)



# This is only for non-standard envs; 
# usually this is included in _xentenv_inner
_start_jupyter = """
# Arcane conda setup instructions
if [ -f "{conda_dir}/etc/profile.d/conda.sh" ]; then
    echo "Using slightly less magic conda setup"
    . "{conda_dir}/etc/profile.d/conda.sh"
else
    echo "Using totally unmagical conda setup"
    export PATH="{conda_dir}/bin:$PATH"
fi

{conda_dir}/bin/conda activate {env_name}
source {conda_dir}/bin/activate {env_name} 

JUP_PORT=$(( 15000 + (RANDOM %= 5000) ))
JUP_HOST=$(hostname -i)
{conda_dir}/envs/{env_name}/bin/jupyter notebook --no-browser --port=$JUP_PORT --ip=$JUP_HOST 2>&1
"""

if args.env == 'nt_singularity':
    jupyter_job += '/project2/lgrandi/xenonnt/development/xnt_env -j {s_container}'.format(s_container=s_container)
else:
    if args.conda_path == '<INFER>':
        print("Autoinferring conda path")
        sys.stdout.flush()
        conda_path = subprocess.check_output(['which', 'conda']).strip()
        conda_path = conda_path.decode()
    else:
        conda_path = args.conda_path

    conda_dir = os.path.dirname(conda_path)
    conda_dir = os.path.abspath(os.path.join(conda_dir, os.pardir))
    print("Using conda from %s instead of singularity container." % conda_dir)
    sys.stdout.flush()
    jupyter_job += _start_jupyter.format(
        conda_dir=conda_dir,
        env_name=args.env)


# Dir for temporary files
# Must be shared between batch queue and login node
# (i.e. not /tmp)
tmp_dir = '/project2/lgrandi/xenonnt/development/.tmp_for_jupyter_job_launcher'

def make_executable(path):
    """Make the file at path executable, see """
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)
    

url_cache_fn = osp.join(
    os.environ['HOME'],
    '.last_jupyter_url')
username = os.environ['USER']

q = subprocess.check_output(['squeue', '-u', username])
for line in q.decode().splitlines():
    if 'straxlab' in line:
        print("You still have a running jupyter job, trying to retrieve the URL.")
        job_id = int(line.split()[0])
        with open(url_cache_fn) as f:
            url = f.read()
        break
        
else:
    print("Submitting a new jupyter job")
    sys.stdout.flush()
    import getpass
    username = getpass. getuser()
    if username == 'kmoraa':
        print("Hi Knut!")
        sys.stdout.flush()
        job_fn = '/project2/lgrandi/xenonnt/development/.tmp_for_jupyter_job_launcher/knut_job'
        log_fn = '/project2/lgrandi/xenonnt/development/.tmp_for_jupyter_job_launcher/knut_log'
    else:
        job_fn = tempfile.NamedTemporaryFile(
            delete=False, dir=tmp_dir).name
        log_fn = tempfile.NamedTemporaryFile(
            delete=False, dir=tmp_dir).name
        
        
    with open(job_fn, mode='w') as f:
        f.write(jupyter_job.format(
            log_fn=log_fn,
            max_hours=2 if args.gpu else 24,
            extra_header=gpu_header if args.gpu else cpu_header,
            n_cpu=n_cpu,
            mem_per_cpu=int(args.ram/n_cpu)))
    make_executable(job_fn)
    print("Sumbitting sbatch %s" % job_fn)
    sys.stdout.flush()
    result = subprocess.check_output(['sbatch', job_fn])
    print("sbatch returned: %s" % result.decode())
    sys.stdout.flush()
    job_id = int(result.decode().split()[-1])

    print("Starting to look for logfile %s..." % log_fn)
    sys.stdout.flush()
    while not osp.exists(log_fn):
        print("Waiting for your job to start...")
        sys.stdout.flush()
        time.sleep(1)

    slept = 0
    url = None
    while url is None and slept < args.timeout:
        with open(log_fn, mode='r') as f:
            for line in f.readlines():
                if 'http' in line:
                    url = line.split()[-1]
                    break
            else:
                print("Waiting for jupyter server to start inside job...")
                sys.stdout.flush()
                sys.stdout.flush()
                time.sleep(2)
                slept += 2
    if url is None:
        with open(log_fn, mode='r') as f:
            content = f.read()
        raise RuntimeError("Jupyter did not start inside your job. Dumping job logfile {log_fn}:\n\n{content}".format(
            log_fn=log_fn,
            content=content,
        ))
    
    with open(url_cache_fn, mode='w') as f:
        f.write(url)
    print("Dumped URL %s to cache file" % url)
    sys.stdout.flush()
    #os.remove(job_fn)
    #os.remove(log_fn)

print("Parsing URL %s" % url)
sys.stdout.flush()
ip, port = url.split('/')[2].split(':')
if 'token' in url:
    token = url.split('?')[1].split('=')[1]
    
else:
    token = ''


print("{{'port':'{port}', 'ip':'{ip}', 'username':'{username}', 'token':'{token}'}}".format(ip=ip, port=port, token=token, username=username))
sys.stdout.flush()
time.sleep(1)

