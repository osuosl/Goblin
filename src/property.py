import jprops
def Property(key_file,properties_file):
   with open("/home/vagrant/goblin/src/etc/" + properties_file) as fp:
	properties = jprops.load_properties(fp)
        return properties
