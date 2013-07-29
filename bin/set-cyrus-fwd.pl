#!/usr/bin/perl -w
use Config::Simple;

$cfg = new Config::Simple($ARGV[0]);
$imaphost = $cfg->param('ImapHost');
$imapuser = $cfg->param('User');
$imappass = $cfg->param('Password');


#
# Sets an ONID user's forward in Cyrus to Google
#

use Cyrus::SIEVE::managesieve;

if ($#ARGV < 1) {
	print "Usage: $0 <username>\n";
	print "  Set the forward in Cyrus for <username> to <username>\@g-mx.oregonstate.edu.\n";
	print "  Prints 'success' if forward is successfully set.\n";
	exit;
}

our $username = $ARGV[1];

my %prefs = ('imapserver' => $imaphost,
		'imapuser'	=> $imapuser,
		'imappass'	=> $imappass
		);

my $scriptname = "google-mig";
my $rv = 0;

my $sievescript = "# This file generated by Google Migration tools\n\n";
$sievescript .= "# Mail forward to Google\n";
$sievescript .= "redirect \"$username\@g-mx.oregonstate.edu\";\n";

# Connect to sieve
# $username is provided to the sieve object by the auth_cb
my $location = $prefs{'imapserver'};
my $sivobj = sieve_get_handle($location, "auth_cb", "auth_cb", "auth_cb", "auth_cb");

if (!defined $sivobj) {
	print "ERROR: unable to connect to sieve server '$location'";
	exit;
}

# Upload it
$rv = sieve_put($sivobj, $scriptname, $sievescript);
if ($rv != 0) { 
	$errstr = sieve_get_error($sivobj);
	$errstr = "unknown error" if (! defined($errstr));
	print "ERROR: uploading sieve rules for '$username': $errstr";
	exit;
}

# Activate it
$rv = sieve_activate($sivobj, $scriptname);
if ($rv != 0) { 
	$errstr = sieve_get_error($sivobj);
	$errstr = "unknown error" if (! defined($errstr));
	print "ERROR: activating sieve rules for '$username': $errstr";
	exit;
}

sieve_logout($sivobj);

print "success\n";





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

