#!/usr/bin/perl -w
#
# Get goblin imap info from goblin.ini
#

use Config::Simple;

$cfg = new Config::Simple('../etc/ldap_fwd.cfg');
$imaphost = $cfg->param('ImapHost');
$imapuser = $cfg->param('User');
$imappass = $cfg->param('Password');

#
# Fetch an ONID user's forward from Cyrus
#

if ($#ARGV < 0) {
	print "Usage: $0 <username>\n";
	print "  Fetch the forward from Cyrus for <username>.\n";
	print "  Prints 'none' if no forward is set.\n";
	exit;
}

our $username = $ARGV[0];

our %prefs = ('imapserver' => $imaphost,
              'imapuser' => $imapuser,
              'imappass' => $imappass
             );

# Setup an empty hash to store the Sieve values
my %sievehash = (
		'forward' => "",
		'keepcopy' => 0,
		'sa' => 0,
		'sahighdiscard' => 0,
		'outofoffice' => "",
		'filters' => [ ]
		);

# Parse their Sieve rules
&parse_sieve_file(\%prefs, $username, \%sievehash);

if ($sievehash{'forward'} eq "") {
	print "none\n";
}
else {
	print "$sievehash{'forward'}\n";
}


##############################################################
# Logging function
##############################################################
sub LOGIT {
	my ($msg) = @_;

	print "$msg\n";
}


##############################################################
# Auth callback for sieve
##############################################################
sub auth_cb {
	my ($type, $prompt) = @_;

	# Gotta hope this stuff is global since the callback mechanism
	# is rather limiting.
	if ($type eq "username") {
		return $username;
	}
	elsif ($type eq "authname") {
		return $prefs{'imapuser'};
	}
	elsif ($type eq "realm") {
		return "";
	}
	elsif ($type eq "password") {
		return $prefs{'imappass'};
	}
	else {
		return "";
	}
}


##############################################################
# List callback for sieve
##############################################################
sub list_cb {
	my ($name, $isactive) = @_;

	# Again, this retarded callback depends on the global
	# variable $scriptname...
	if ($isactive == 1) {
		$scriptname = $name;
	}
}


##############################################################
# Parse the user's sieve file into a hashref
##############################################################
sub parse_sieve_file {
	my ($pref, $username, $sref) = @_;
	my ($sivobj, $rv, $errstr);
	local $scriptname;  # so the subroutine can still see it
	my @sievelines;
	my $sievescript = "";
	my $startooo = 0;

	use Cyrus::SIEVE::managesieve;

	# Locate their mailbox
	my $location = $$pref{'imapserver'};
#	my $location = &locate_mailbox($$pref{'imapserver'}, $$pref{'imapuser'}, $$pref{'imappass'}, "user.$username");
#	if ($location eq "") {
#		$location = $$pref{'imapserver'};
#	}


	# Connect to sieve
	$sivobj = sieve_get_handle($location, "auth_cb", "auth_cb",
			"auth_cb", "auth_cb");

	if (! defined($sivobj)) {
		&LOGIT("Could not connect to mail server '$location', please try again.");
		return;
	}

	# Get name of active sieve script
	# The callback will set the global variable $scriptname if an active script is found
	$rv = sieve_list($sivobj, "list_cb");
	if ($rv != 0) { 
		$errstr = sieve_get_error($sivobj);
		$errstr = "unknown error" if (! defined($errstr));
		&LOGIT("Couldn't list sieve file for $username: $errstr\n");
		return;
	}

	# Just return if they don't have a sieve file
	if (! defined($scriptname) or $scriptname eq "") {
		sieve_logout($sivobj);
		return;
	}

	# Get the active script
	$rv = sieve_get($sivobj, $scriptname, $sievescript);
	if ($rv != 0) { 
		$errstr = sieve_get_error($sivobj);
		$errstr = "unknown error" if (! defined($errstr));
		&LOGIT("Couldn't fetch sieve file '$scriptname' for $username: $errstr\n");
		return;
	}

	sieve_logout($sivobj);

	# Strip Carriage-Return (\r)
	$sievescript =~ s/\r//g;

	# Push it into an array line by line so we can parse it
	@sievelines = split(/\n/, $sievescript);

	foreach $line (@sievelines) {

		# If an Out of Office message has started, read it until a line with only "; on it
		if ($startooo == 1) {
			if ($line =~ /^";$/) {
				$startooo = 0;
				# Clean up the trailing newlines
				$$sref{'outofoffice'} =~ s/\n+$//;
			}
			else {
				# Clean up any extra CR's
				$line =~ s/\r//g;
				$$sref{'outofoffice'} .= $line . "\n";
			}
			next;
		}

		# Look for forward
		if ($line =~ /^redirect "(.*)"/) {
			$$sref{'forward'} = $1;
		}

		# Keep a local copy when forwarding?
		if ($line =~ /^keep;/) {
			$$sref{'keepcopy'} = 1;
		}

		# Look for SA
		if ($line =~ /^if header :contains "X-Spam-Flag" "YES"/) {
			$$sref{'sa'} = 1;
		}

		# Look for SA discard high scores
		if ($line =~/^if header :contains "X-Spam-Level" "\*\*\*\*\*\*\*\*\*\*" \{ discard; /) {
			$$sref{'sahighdiscard'} = 1;
		}

		# Look for From filters
		if ($line =~ /^if header :contains "From" "(.*)" \{ fileinto "(.*)"; \}/) {
			push @{$$sref{'filters'}}, "from:$1:$2";
		}

		if ($line =~ /^if header :contains "From" "(.*)" \{ discard; /) {
			push @{$$sref{'filters'}}, "from:$1:discard";
		}

		# Look for To filters
		if ($line =~ /^if header :contains \["To", "Cc", "Bcc"\] "(.*)" \{ fileinto "(.*)"; \}/) {
			push @{$$sref{'filters'}}, "to:$1:$2";
		}

		if ($line =~ /^if header :contains \["To", "Cc", "Bcc"\] "(.*)" \{ discard; /) {
			push @{$$sref{'filters'}}, "to:$1:discard";
		}

		# Look for vacation
		if ($line =~ /^vacation :days 7 :subject "Out of office" "$/) {
			# Loop until we find the end of this stanza (see above)
			$startooo = 1;
			next;
		}
	}
}





##############################################################
# Locate which backend a mailbox is on
##############################################################
sub locate_mailbox {
	my ($server, $authuser, $authpw, $mailbox) = @_;
	my $location = "";

	use Mail::IMAPClient;

	my $imap = Mail::IMAPClient->new(
				Server => $server,
				User => $authuser,
				Password => $authpw,
				Ssl => 1,
				Port => 993,
			);
	if (! $imap) {
		return $location;
	}

	my @results = $imap->tag_and_run(qq/GETANNOTATION $mailbox "*" "value.shared"/);

	$imap->logout;

	foreach my $r (@results) {
		$r =~ s/\r//g;
		$r =~ s/\n//g; 
		if ($r =~ /\/vendor\/cmu\/cyrus-imapd\/server" \("value.shared" "(.*)"\)$/) {
			$location = $1;
		}
	}

	return $location;
}



1;

