# Setup remote access on Raspberry Pi

## Setup in LAN first 

After SSH is ready. New Pi system require a virtual environment.

```
sudo apt-get install git

git clone https://github.com/DeqingSun/CH32V003-Automatic-Test-Tool

cd CH32V003-Automatic-Test-Tool/remoteAccessCode

# Create a environment named 'venv'
python3 -m venv venv
# Activate the virtual environment
source venv/bin/activate

pip3 install -r requirements.txt

python3 server.py
```

And server can run.

Then add rule

```
sudo cp ../autoTestCode/lib/toolBinary/99-minichlink.rules /etc/udev/rules.d/
sudo chmod 644 /etc/udev/rules.d/99-minichlink.rules
sudo reboot
```

Then

```
cd ~/CH32V003-Automatic-Test-Tool/remoteAccessCode
source venv/bin/activate
python3 server.py
```

The remote access server is ready on LAN.

## Setup tunnel for internet access

Use cloudflare tunnel

in cloudflare dashboard, networking->tunnels. Create tunnel

I give it name ch32v003_remote

Setup Environment choose Debian arm64, copy commands and run as service

After running "Install as service"

The cloudflare allow us to go forward

then

Dashboard → Networks → Tunnels -> Open your tunnel (e.g. ch32v003_remote) Go to Routes, add route , Add published application Subdomain: ch32v003 Service URL: http://localhost:8000

```
nohup python3 server.py > /dev/null 2>&1 &
```

and https://ch32v003.thinkcreate.us/ works!

to kill it, find ID

ps aux | grep server.py
