Ansible Debian Package
======================

To create an Ansible DEB package:

    sudo apt-get install cdbs debhelper dpkg-dev git-core reprepro
    git clone git://github.com/ansible/ansible-provisioning.git
    cd ansible
    make deb

The debian package file will be placed in the `../` directory. This can then be added to an APT repository or installed with `dpkg -i ../*.deb`.

Note that `dpkg -i` does not resolve dependencies
