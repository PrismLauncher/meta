# PolyMC Meta
Scripts to generate jsons and jars that PolyMC will access.

## Deployment
It is recommended to use Docker to deploy the environment.

- Clone this repo to a server
- Make sure it's writable by the container later: `chown -R 1000:1000 .`
- Configure `config/config_local.sh`
  - The defaults should be fine (apart from committer email and name perhaps)
- Put your SSH key (which has push access to meta-upstream and meta-polymc) at `config/deploy.key`
- Pull meta- repos: `bash clone.sh`
- Customize docker-compose.yaml
  - You might want to add `restart: always`
- Run `docker-compose up -d --build`
- Observe Cron logs using `docker-compose logs -f` (Runs hourly by default)
- (Optional) Run once to fill caches: `docker-compose run meta update`

## Usage

### Install the dependencies

As root:
```
sudo pip install -r requirements.txt
```

Or as user:
```
pip install --user -r requirements.txt
```

### Initial setup
This will clone [meta-polymc](https://github.com/PolyMC/meta-polymc) and [meta-upstream](https://github.com/PolyMC/meta-upstream)

```
./clone.sh
```

### Generate files
This will run the main script and do its magic

```
./update.sh
```

### Check status of meta-polymc and meta-upstream

```
./status.sh
```
