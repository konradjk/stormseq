# Preparing for starcluster config and non-interactive login to starcluster
mkdir /root/.starcluster/
echo "StrictHostKeyChecking no" > ~/.ssh/config

# Unsecure site
chmod +x /var/www/landing/*cgi
chown ubuntu:ubuntu /var/www/landing/*cgi
chown ubuntu:ubuntu /var/www/landing/
echo "SuexecUserGroup ubuntu ubuntu" >> /etc/apache2/mods-enabled/cgid.conf
perl -pi -e 's/Options Indexes FollowSymLinks MultiViews/Options Indexes FollowSymLinks MultiViews +ExecCGI/g' /etc/apache2/sites-enabled/000-default
perl -pi -e 's/DocumentRoot.*/DocumentRoot \/var\/www\/landing/g' /etc/apache2/sites-available/default
perl -pi -e 's/#AddHandler cgi-script .cgi/AddHandler cgi-script .cgi/g' /etc/apache2/mods-available/mime.conf

# CGI configuration
apt-get update
apt-get install apache2-suexec
ln -s /etc/apache2/mods-available/suexec.load /etc/apache2/mods-enabled/suexec.load
perl -pi -e 's/_default_/*/g' /etc/apache2/sites-available/default-ssl
#ln -s /etc/apache2/mods-available/ssl.load /etc/apache2/mods-enabled/ssl.load
#ln -s /etc/apache2/mods-available/ssl.conf /etc/apache2/mods-enabled/ssl.conf

# Secure site
#ln -s /etc/apache2/sites-available/default-ssl /etc/apache2/sites-enabled/001-default-ssl
chmod +x /var/www/*cgi
chown ubuntu:ubuntu /var/www/*cgi
chown ubuntu:ubuntu /var/www/
perl -pi -e 's/Options Indexes FollowSymLinks MultiViews/Options Indexes FollowSymLinks MultiViews +ExecCGI/g' /etc/apache2/sites-enabled/001-default-ssl

/etc/init.d/apache2 restart
