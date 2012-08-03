# GENERATE SELF-SIGNED SSL CERTIFICATE
openssl genrsa -out ssl.key 2048
openssl req -new -batch -key /etc/ssl/private/ssl-cert-snakeoil.key > /etc/ssl/private/ssl-cert-snakeoil.csr
openssl x509 -req -days 365 -in /etc/ssl/private/ssl-cert-snakeoil.csr -signkey /etc/ssl/private/ssl-cert-snakeoil.key  -out /etc/ssl/certs/ssl-cert-snakeoil.pem

# Start SSL site to signify end
/etc/init.d/apache2 restart
