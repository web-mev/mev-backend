#!/usr/bin/env bash

# print commands and their expanded arguments
set -x

set -o allexport
CROMWELL_IP=${cromwell_ip}
set +o allexport


apt-get update
     apt-get install apache2 -y
     a2ensite default-ssl
     a2enmod ssl
     vm_hostname="$(curl -H "Metadata-Flavor:Google" \
     http://169.254.169.254/computeMetadata/v1/instance/name)"
     echo "Page served from: $vm_hostname" | tee /var/www/html/index.html
     echo $CROMWELL_IP >> /var/www/html/index.html
     systemctl restart apache2

echo "DONE"