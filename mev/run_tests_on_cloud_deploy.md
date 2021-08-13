### To run unit tests on a cloud-based deployment:

As a temporary hack to run the unit tests on a cloud deployment, the provisioning script dumps the
environment variables defined at the end of the provisioning into a file at `/data/env_vars.txt`. This
set of environment variables is complete for the purposes of running the test suite.

After the stack is up, SSH into the VM. Then change to the ubuntu user:
```
sudo su ubuntu
```

At this point, we have one hitch to deal with. When the file environment variables is created, any quoted strings 
are sent to `/data/env_vars.txt` as unquoted. Hence, you will see a line like:
```
FROM_EMAIL= Someone <someone@mail.com>
```
(Obviously, the actual value will depend on the variables set in your Terraform tfvars file.)

Upon trying to source this into your current shell session (as shown below), that line will cause a failure when parsing. Hence, **you will need to add quotes around the `FROM_EMAIL` variable.**

Once that is complete, run:
```
set -o allexport
source /data/env_vars.txt
set +o allexport
cd /opt/software/mev-backend/mev
python3 manage.py test --failfast
```
