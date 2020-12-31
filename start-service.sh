#! /bin/bash

export SLACK_SIGNING_SECRET=
export OAUTH_ACCESS_TOKENS=
export CERTBOT_DIR=
export CLIENT_SECRET=
export CLIENT_ID=
export FLASK_APP=modron

# Uncomment next line if you use local certificates (e.g., and not ngrok)
flask run --host 0.0.0.0 --port 7879 # --cert $CERTBOT_DIR/fullchain.pem --key $CERTBOT_DIR/privkey.pem
