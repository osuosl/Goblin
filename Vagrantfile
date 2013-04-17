# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "debian-6-20121228"
  config.vm.host_name = "vagrant-debian-base.osuosl.org"

  config.vm.box_url = "http://packages.osuosl.org/vagrant/debian-6-20121228.box"
  
  config.vm.provision :shell, :path => "config.sh"

  config.vm.share_folder "goblin", "/home/vagrant/goblin/src", "./"

  # Forward ports from the guest to the host, which allows for outside
  # computers to access the VM, whereas host only networking does not.
  config.vm.forward_port 80, 8080
  config.vm.forward_port 8000,8000
  #config.vm.provision :shell do |shell|
  #  shell.inline = "rsync -r /vagrant/cfengine/bootstrap64/* /var/cfengine/ && cfagent -q --update-only"
  #end
end
