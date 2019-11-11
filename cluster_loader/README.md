# Cluster Loader
[cluster loader](https://github.com/openshift/origin/blob/master/test/extended/cluster/) is a tool to load your openshift cluster.

## Requirements

Step 1: Please build the binary openshift-tests by following [building binary](https://github.com/openshift/origin/blob/master/HACKING.md#end-to-end-e2e-and-extended-tests)

Step 2: You'll also need to install following python packages as follows:

```bash
pip install configparser elasticsearch statistics numpy pyyaml
```

Step 3: Set the following necessary environment variables:

*KUBECONFIG* and point to kubernetes cluster you want to run cluster loader against

Note: oc binary is also required as cluster loader uses openshift client

Additional environment variables:

*VIPERCONFIG* if you'd like to use custom configuration for running cluster loader.

*AZURE_AUTH_LOCATION* in case of openshift deployed on azure and pointed to the credentials.

Please read more about how you'll need to build your custom configuration file at
[openshift docs](https://docs.openshift.com/container-platform/4.2/scalability_and_performance/using-cluster-loader.html)

Note: To index data into elasticsearch you'll also need to set the environment vars *es*,*es_port* and *es_index*
as well as additional identifers such as *uuid*, *clustername* and *test_user*

## Invoking cluster loader through snafu:

You can then invoke cl as follows:

```bash
 python snafu/run_snafu.py < test_name > -t cl
```

Note: additional arguments that can be passed are:

`-s` or `--samples` type=int description=number of times to run benchmark, defaults to 1

`-d` or `--dir`  description=output parent directory, defaults to current directory

`-p` or `--path-binary` description=absolute path to openshift-tests binary defaults to `/root/go/src/github.com/openshift/origin/_output/local/bin/linux/amd64/openshift-tests`

`--cl-output` description=print the cl output to console ( helps with CI ) defaults to False if not provided

The output of the run will be in `curr_dir/<sample_number>/cl_output.txt` so you can also see what's happening by tailing the file even if `--cl-output` flag is set to false.
