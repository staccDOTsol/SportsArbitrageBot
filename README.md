# Sports Arbitrage Bot
Currently supports arbitraging Tennis matches between Fairlay and BetBTC.

# Setup

Requirements:
Python 2.7
Python Requests, PyCrypto libraries (install via pip or easy_install)

Please do sign up using my ref link (or else all this effort was for nadda):

https://www.betbtc.co/?ref=8908

if you already have a betbtc, hopefully you don't mind creating a new one for the purpose of this script.

You can find your API key for betbtc here:

https://www.betbtc.co/users/edit

Open both client_dryrun.py and client.py and replace this line: 

sessionBetBTC.headers.update({'Authorization': 'Token token=CHANGEME'})
      
where Token token=xyz is your token in the above link.

run python client_dryrun.py and it'll generate you an SSH key to put into the other exchange, Fairlay.

python client_dryrun.py 
===================================================================
It appears that you don't have a config file, so we created
a new one with a brand new key pair.

Please visit:  http://fairlay.com/user/dev and register a new API
Account with the following public key:

-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----

** Don't forget to to change ID and APIAccountID fields in
   the config.txt file.
===================================================================

So we head over to Fairlay, sign up then visit this page: 

https://fairlay.com/user/dev/

note their API has a usage fee, so you'll need funds in Fairlay before you can sign up for an API key.

open config.txt in current dir, change:

"ID": "CHANGETHIS",

to reflect your ID on the above page.

Now you can run the script. python client_dryrun.py will show you a ton of debug output (more debug for the 5th type of match), but does not execute orders or update the file ids.txt.

Running python client.py will execute the orders it finds, and will update ids.txt (so that it doesn't bet on the same competition twice).

You may want to change time.sleep(60) and comment it out in client.py, in each possible outcome, after we're in production. That's there so it doesn't open too many shoddy orders.

# Next Steps:

1. Support more APIs, see apis.txt
2. Support more sports (currently on Fairlay and BetBTC we could also have Soccer covered, many more options with the other APIs).
