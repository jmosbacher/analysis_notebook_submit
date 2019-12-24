### Analysis notebook submitter
Performs the tedious tasks of:
 1) logging in to midway.
 2) submitting a notebook script.
 3) tunneling through to the machine running the job.
 4) opening a browser.

All from the comfort of your own home.
    
Any extra parameters are passed on to the standard submission script.

### Requirements
    - click
    - paramiko

### Usage
    ```
    python analysis_noptebook [--username `USER`] [--server dali/midway] [script_arguments...]
    ```
where script_arguments are passed as is to the standard submission script on the login node:
<pre>
--copy_tutorials      Copy tutorials to ~/strax_tutorials (if it does not
                    exist)
--partition PARTITION
                    RCC/DALI partition to use. Try dali, broadwl, or
                    xenon1t.
--timeout TIMEOUT     Seconds to wait for the jupyter server to start
--cpu CPU             Number of CPUs to request.
--ram RAM             MB of RAM to request
--conda_path CONDA_PATH
                    For non-singularity environments, path to conda binary
                    to use.Default is to infer this from running 'which
                    conda'.
--gpu                 Request to run on a GPU partition. Limits runtime to 2
                    hours.
--env ENV             Environment to activate; defaults to "nt_singularity"
                    to load XENONnT singularity container. Other arguments
                    are passed to "conda activate" (and don't load a
                    container).
--container CONTAINER
                    Singularity container to loadSee wiki page https://xe1
                    t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:dsg:comp
                    uting:environment_trackingDefault container: "latest"
</pre>