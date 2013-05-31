import jprops
def Property(key_file,properties_file):
   with open("/var/www/goblin/current/etc/" + properties_file) as fp:
	properties = jprops.load_properties(fp)
        return properties
