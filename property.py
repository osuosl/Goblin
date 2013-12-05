import jprops
def Property(key_file,properties_file):
   if not properties_file.startswith("/"):
      properties_file = "/var/www/goblin/current/etc/" + properties_file

   with open(properties_file) as fp:
      properties = jprops.load_properties(fp)
      return properties
