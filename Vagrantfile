# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "debian-6-20121228"
  config.vm.host_name = "vagrant-debian-base.osuosl.org"

  config.vm.box_url = "http://packages.osuosl.org/vagrant/debian-6-20121228.box"

  # Boot with a GUI so you can see the screen. (Default is headless)
  # config.vm.boot_mode = :gui

  # config.vm.network :hostonly, "192.168.33.10"

  # Forward a port from the guest to the host, which allows for outside
  # computers to access the VM, whereas host only networking does not.
  config.vm.forward_port 80, 8080
  config.vm.forward_port 8000,8000
  #config.vm.provision :shell do |shell|
  #  shell.inline = "rsync -r /vagrant/cfengine/bootstrap64/* /var/cfengine/ && cfagent -q --update-only"
  #end
end
