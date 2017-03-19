# CouchDB 1.6.1 on Ubuntu 14.04 LTS
useradd -d /usr/local/var/lib/couchdb couchdb
gpasswd -a couchdb sudo
mkdir -p /usr/local/{lib,etc}/couchdb /usr/local/var/{lib,log,run}/couchdb /var/lib/couchdb
chown -R couchdb /usr/local/var/{lib,log,run}/couchdb /usr/local/{lib,etc}/couchdb
chmod 0770 /usr/local/var/{lib,log,run}/couchdb/
add-apt-repository ppa:launchpad/ppa
apt-get update
apt-get install -y python-software-properties=0.92.37.7 \
g++=4:4.8.2-1ubuntu6 \
erlang-dev=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-eunit=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-xmerl=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-inets=1:16.b.3-dfsg-1ubuntu2.1 \
erlang=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-base-hipe=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-manpages=1:16.b.3-dfsg-1ubuntu2.1 \
erlang-nox=1:16.b.3-dfsg-1ubuntu2.1 \
libmozjs185-dev=1.8.5-1.0.0+dfsg-4ubuntu1 \
libicu-dev=52.1-3ubuntu0.4 \
libcurl4-gnutls-dev \
libtool=2.4.2-1.7ubuntu1
cd /opt
wget http://apache.mirror.digitalpacific.com.au/couchdb/source/1.6.1/apache-couchdb-1.6.1.tar.gz
tar xvzf apache-couchdb-1.6.1.tar.gz
mv apache-couchdb-1.6.1/ couchdb
cd couchdb
./configure
apt-get install make
make && sudo make install
chmod 664 /usr/local/etc/couchdb/*.ini
chmod 775 /usr/local/etc/couchdb/*.d

nano /usr/local/etc/couchdb/default.ini

fdisk /dev/vdb
n
p
1
w
mkfs.ext4 /dev/vdb1
nano /etc/fstab
#add line /dev/vdb1               /mnt/couchdb            ext3    defaults        1 2
mkdir /mnt/couchdb
mount /dev/vdb1 /mnt/couchdb
