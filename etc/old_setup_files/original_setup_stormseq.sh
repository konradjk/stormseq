# Enable unsecure website with instructions
/etc/init.d/apache2 restart

# Assumes that cert- and pk- are only 2 certs in /root/
logger -is stormseq "Waiting for certificate file to be uploaded..."
while [ ! -f /root/cert-*.pem ]; do
  sleep 3;
done
logger -is stormseq "Waiting for private key file to be uploaded..."
while [ ! -f /root/pk-*.pem ]; do
  sleep 3;
done
logger -is stormseq "Done waiting for keys"
export EC2_CERT=`ls -1 /root/cert-*.pem`
export EC2_PRIVATE_KEY=`ls -1 /root/pk-*.pem`

security_group=stormseq
logger -is stormseq "Finding security group id for security group ${security_group}..."
security_group_id=`ec2-describe-group --filter group-name=$security_group | grep ^GROUP | cut -f2`
logger -is stormseq "Found security group id ${security_group_id}"

logger -is stormseq "Authorizing ports 80 and 443 on security group ${security_group}..."
ec2-authorize ${security_group_id} -P tcp -p 80
ec2-authorize ${security_group_id} -P tcp -p 443

logger -is stormseq "Getting external IP address..."
external_ip=`ec2-describe-instances --filter tag-key=Name --filter tag-value=stormseq --filter instance-state-name=running|grep ^INSTANCE|cut -f4`
logger -is stormseq "Got external IP address: ${external_ip}"

# GENERATE SELF-SIGNED SSL CERTIFICATE
logger -is stormseq "Generating SSL cert for ${external_ip}..."
openssl genrsa -out ${external_ip}.key 2048
openssl req -new -batch -key ${external_ip}.key > ${external_ip}.csr
openssl x509 -req -days 365 -in ${external_ip}.csr -signkey ${external_ip}.key  -out ${external_ip}.crt

cp ${external_ip}.crt /etc/ssl/certs/ssl-cert-snakeoil.pem
cp ${external_ip}.key /etc/ssl/private/ssl-cert-snakeoil.key

logger -is stormseq "Configuring and restarting apache..."
# Enable SSL site
ln -s /etc/apache2/mods-available/ssl.load /etc/apache2/mods-enabled/ssl.load
ln -s /etc/apache2/mods-available/ssl.conf /etc/apache2/mods-enabled/ssl.conf
ln -s /etc/apache2/sites-available/default-ssl /etc/apache2/sites-enabled/001-default-ssl

# Prepare CGI script dependencies
chmod u+s `which python` `which ipython` `which umount`
ln -s /usr/lib/jvm/java-6-openjdk/jre/lib/amd64/jli/libjli.so /usr/lib/

# Attach the volume for uploading.  It will have the tag "Name:stormseq_data"
logger -is stormseq "Finding instance id..."
instance_id=`ec2-describe-instances --filter tag:Name=stormseq --filter instance-state-name=running | grep ^INSTANCE | cut -f2`
while [ -z "$instance_id" ]; do
  instance_id=`ec2-describe-instances --filter tag:Name=stormseq --filter instance-state-name=running | grep ^INSTANCE | cut -f2`
done
logger -is stormseq "Found: $instance_id"

logger -is stormseq "Finding stormseq_data volume..."
volume_id=`ec2-describe-volumes --filter tag:Name=stormseq_data | grep ^VOLUME | cut -f2`
while [ -z "$volume_id" ]; do
  volume_id=`ec2-describe-volumes --filter tag:Name=stormseq_data | grep ^VOLUME | cut -f2`
done
logger -is stormseq "Found: $volume_id"

logger -is stormseq "Attaching volume: ec2-attach-volume $volume_id -i $instance_id -d /dev/sdf ..."
ec2-attach-volume $volume_id -i $instance_id -d /dev/sdf

logger -is stormseq "Waiting until volume $volume_id is attached..."
vol_state=`ec2-describe-volumes $volume_id | grep ^ATTACHMENT | cut -f5`
while [ "attached" != "$vol_state" ]; do
  sleep 1;
  vol_state=`ec2-describe-volumes $volume_id | grep ^ATTACHMENT | cut -f5`
done
logger -is stormseq "Volume $volume_id is attached!"

# mkfs
#logger -is stormseq "Make filesystem and mount drive"
mkdir /mnt/stormseq_data

# hopefully it is /dev/xvdf, otherwise maybe loop over likely candidates
device=/dev/xvdf
mkfs -t ext3 $device
mount -t ext3 $device /mnt/stormseq_data

# Start SSL site to signify end
/etc/init.d/apache2 restart
