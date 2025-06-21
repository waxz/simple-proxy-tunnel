# simple http/ssh/tcp proxy via cloudflare/pinggy tunnel

You can run a gost proxy server on remote server like gcp or aws.

Then forward your local traffic to remote server via cloudflare tunnel.

If your server doesn't have extern ip, you can use tailscale.

You can also use other tunnel like [pinggy](https://pinggy.io/), you need an account.


## on server 

```bash

cat << 'EOF' | tee -a $HOME/.bashrc

# gh_install vi/websocat websocat.x86_64-unknown-linux-musl
gh_install(){

  echo "Number of arguments: $#"
  echo "All arguments as separate words: $@"
  echo "All arguments as a single string: $*"
  if [[ -z "$1" ||  -z "$2" || -z "$3" ]]; then
    echo "please set repo , arch and filename"
  else
    repo=$1
    arch=$2
    filename=$3

    echo "set repo: $repo, arch: $arch, filename: $filename"

    url=$(curl -L   -H "Accept: application/vnd.github+json"   https://api.github.com/repos/$repo/releases | jq -r ".[0].assets[] | .browser_download_url" | grep "$arch") 
    count=0
    while [  -z "$url" && $count -lt 5 ];do
      url=$(curl -L   -H "Accept: application/vnd.github+json"   https://api.github.com/repos/$repo/releases | jq -r ".[0].assets[] | .browser_download_url" | grep "$arch") 
      count=$((count+1))
    done
  echo "url: $url"

  if [ ! -z "$url" ]; then
      wget $url -O $filename
  fi

  fi 

} 

EOF

source $HOME/.bashrc
gh_install
```

### install gost and websocat

```bash
gh_install go-gost/gost linux_amd64.tar.gz /tmp/gost_linux.tar.gz
mkdir -p /tmp/gost && tar xf /tmp/gost_linux.tar.gz -C /tmp/gost
sudo mv /tmp/gost/gost /bin/

gh_install vi/websocat websocat.x86_64-unknown-linux-musl /tmp/websocat
chmod +x /tmp/websocat
sudo mv /tmp/websocat /bin/

```

### install tunnel

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Add this repo to your apt repositories
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# install cloudflared
sudo apt-get update && sudo apt-get install -y cloudflared


```

### run flask server

```bash
pip install flask

# flask run --host 0.0.0.0 --port 8000
nohup bash -c "flask run --host 0.0.0.0 --port 8000 " > /tmp/flask.nohup.out 2>&1 &

```
### run websocat ssh server and tunnel

```bash
nohup bash -c "websocat --binary ws-l:127.0.0.1:38022 tcp:127.0.0.1:22" > /tmp/websocat-ssh.out 2>&1 &
nohup bash -c "while true; do cloudflared tunnel --url localhost:38022   > /tmp/cloudflared-ssh.out 2>&1 ;flock -x  /tmp/cloudflared-ssh.out  truncate -s 0 /tmp/cloudflared-ssh.out;  done " > /tmp/cloudflared-ssh.nohup.out 2>&1 &

```

### run proxy and tunnel

#### cloudflare

```bash
nohup bash -c "gost -L=mws://:38083?enableCompression=true&keepAlive=true&idletimeout=30s&readBufferSize=64KB" > /tmp/gost.2.out 2>&1 &
nohup bash -c "while true; do cloudflared tunnel --url localhost:38083   > /tmp/cloudflared.out 2>&1 ;flock -x  /tmp/cloudflared.out  truncate -s 0 /tmp/cloudflared.out;  done " > /tmp/cloudflared.nohup.out 2>&1 &
```

#### pinggy
If you use free plan, pinggy will reset every hour. Just rerun your local script.

```bash
PINGGY_TOKEN=xxxxx
nohup bash -c "gost -L=ss+ohttp://chacha20:123456@:38082 " > /tmp/gost.1.out 2>&1 &
nohup bash -c "while true; do ssh -p 443 -R0:localhost:38082 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 xzL2nErJ1Pq+tcp@free.pinggy.io  > /tmp/pinggy.out ;flock -x  /tmp/pinggy.out  truncate -s 0 /tmp/pinggy.out;  done " > /tmp/pinggy.nohup.out 2>&1 &
```


## on client

### run proxy client

#### cloudflare

```bash

server=<your server>

url=$(curl -X POST http://$server:8000/run \
  -H "Authorization: Bearer mysecrettoken123" \
  -H "Content-Type: application/json" \
  -d '{"action": "extract_urls", "file_path": "/tmp/cloudflared.out"}'  | jq -r ".urls[2]")

url=${url/"https://"/""}
echo url: $url

gost -L=:38083 -F=mwss://$url:443?enableCompression=true&keepAlive=true&idletimeout=30s&readBufferSize=64KB
```

#### pinggy

```bash

server=<your server>

url=$(curl -X POST http://$server:8000/run \
  -H "Authorization: Bearer mysecrettoken123" \
  -H "Content-Type: application/json" \
  -d '{"action": "extract_urls", "file_path": "/tmp/pinggy.out"}'  | jq -r ".urls[1]")

url=${url/"tcp://"/""}
echo url: $url

gost -L=:38082 -F=ss+ohttp://chacha20:123456@$url
```
### run ssh client

```bash
server=<your server>
url=$(curl -X POST http://$server:8000/run   -H "Authorization: Bearer mysecrettoken123"   -H "Content-Type: application/json"   -d '{"action": "extract_urls", "file_path": "/tmp/cloudflared-ssh.out"}' | jq -r ".urls[2]")
url="${url/https:\/\//}"
ssh runner@$url -o ProxyCommand="websocat -E  --binary wss://%h" -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no

```
