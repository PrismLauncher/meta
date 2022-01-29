# PolyMC Meta
Scripts to generate jsons and jars that PolyMC will access.

## Usage

### Install the dependencies

As root:
```
sudo pip install requirements.txt
```

Or as user:
```
pip install --user requirements.txt
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