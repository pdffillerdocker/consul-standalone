# Supported tags and respective `Dockerfile` links

## <a name="tags-frozen"></a>Immutable (fixed, "frozen") tags

Tags that were once built and should not be rebuilt

-	[`1.5.3`](https://github.com/pdffillerdocker/consul-standalone/blob/49bac345b06ca984cd0ddfc92850763b4de49ec9/Dockerfile)


## <a name="tags-stable"></a>Mutable tags

Tags that can point to different images over time

-	[`1.5`, `latest`](https://github.com/pdffillerdocker/consul-standalone/blob/49bac345b06ca984cd0ddfc92850763b4de49ec9/Dockerfile)


## <a name="tags-dev"></a>Development tags

Tags that used for development purposes and can be (and most likely will be) deleted/rebuilt
at any time


# Quick reference

<!--
-	**Where to get help:**
-	**Published image artifact details**:
-	**Image updates**:
-->

-	**Where to file issues**:
        <br/>[https://github.com/pdffillerdocker/consul-standalone/issues](https://github.com/pdffillerdocker/consul-standalone/issues)

-	**Supported architectures**:
	<br/>`amd64`

-	**Maintained by**:
	<br/>[PDFfiller](https://github.com/pdffillerdocker/consul-standalone)
	<br/>[Anton Trifonov](https://github.com/rinrailin)

-	**Source of this description**:
	<br/>[`README.md` at GitHub](https://github.com/pdffillerdocker/consul-standalone/blob/master/README.md)

# Consul-standalone

Consul-standalone is lightweight Docker image based on [Consul official docker image](https://hub.docker.com/_/consul)
and designed to be used as light standalone Consul server with provisioned key/value ("KV") in local development (e.g. `docker-compose`)
or testing/QA environments.

# Contents

- [Supported tags and respective `Dockerfile` links](#supported-tags-and-respective-dockerfile-links)
  - [Immutable tags](#tags-frozen)
  - [Mutable Tags](#tags-stable)
  - [Development Tags](#tags-dev)
- [Quick reference](#quick-reference)
- [Consul-standalone](#consul-standalone)
- [Contents](#contents)
- [How to use this image](#how-to-use-this-image)
  - [Provisioning](#provisioning)
  - [Templating](#templating)
  - [Sample docker-compose configuration](#sample-docker-compose-configuration)
  - [Persistent data and mounts](#persistent-data-and-mounts)
    - [Persistent consul data](#persistent-consul-data)
    - [KV file mounting](#kv-file-mounting)
  - [Changing KV](#changing-kv)
    - [With Consul UI](#with-consul-ui)
    - [By changing KV file](#by-changing-kv-file)
    - [Directly from command line](#directly-from-command-line)
- [License](#license)

# How to use this image

The simpliest (but not the most useful) way to use this image is just run it:

```bash
$ docker run -d --rm -p 8500:8500 pdffiller/consul-standalone
```

In such a case, you will get a Consul standalone server without any KV in it, providing Consul HTTP API at port `8500/tcp` of your local machine
and with UI accessible by [http://localhost:8500/ui/](http://localhost:8500/ui/). 

## Provisioning

In many cases, the application, which being developed or tested, expects that there are some KV in Consul. In such situations, consul-standalone can be
provisioned with KVs using simple YAML or JSON file ("KV file") mounted or copied to a container and passed as command. This file
should contain plain JSON object or YAML associative array with strings, integers or booleans as values (integers and booleans are
converted to strings).

JSON example (`provision/kv.json`):

```json
{
  "some/kv_path/key1": "value1",
  "some/kv_path/key2": 234,
  "other/kv_path/key3": true
}
```

Same data but in YAML (`provision/kv.yml`):

```yaml
some/kv_path/key1: value1
some/kv_path/key2: 234
other/kv_path/key3: true
```

To run consul-standalone with KV file:

```bash
$ docker run -v `pwd`/provision:/provision -d --rm -p 8500:8500 pdffiller/consul-standalone /provision/kv.yaml
```

Or in case of docker-compose (`docker-compose.yml`):

```yaml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./provision:/provision
    command: /provision/kv.yaml

...

  app:
    build: .
    environment:
      - CONSUL_HTTP_ADDR=consul:8500

...
```

If path to readable `.yml`, `.yaml` or `.json` file is passed as a first argument of the docker command, consul-template
image entrypoint will create background job, which will wait for Consul to start and populate the KVs described in KV file.

## Templating

The KV file can be templated using environment variables.

There is a special environment variable called `UPDATEKV_VARIABLES`, whose value should be a comma-separated list of
environment variable names, which you want to use. If `VAR_NAME` is present in `UPDATEKV_VARIABLES`, a provisioning
script will replace all special strings like `$VAR_NAME$` into the value of the environment variable `VAR_NAME` inside
the KV file before parsing.

For example if you have `provision/kv.yml` KV file:

```yaml
$KV_PATH$/key1: value1
$KV_PATH$/key2: 234
$OTHER_KV_PATH$/key2: true
```

and run

```bash
$ docker run \
  -e UPDATEKV_VARIABLES=KV_PATH,OTHER_KV_PATH \
  -e KV_PATH=some/kv/path \
  -e OTHER_KV_PATH=other/path \
  -v `pwd`/provision:/provision \
  -d \
  --rm \
  -p 8500:8500 \
  pdffiller/consul-standalone \
  /provision/kv.yml
```

KV file will be parsed as

```yaml
some/kv/path/key1: value1
some/kv/path/key2: 234
other/path: true
```

## Sample docker-compose configuration

Since `docker-compose` allows the definition of environment variables in multiple ways, it would be convenient not
to define variables used by consul-standalone in `environment` block of `docker-compose.yml` file, but place them in
separate `*.env` file.

For example, if you have `provision/kv.yml`:

```yaml
$KV_PATH$/db/host: mysql
$KV_PATH$/db/port: 3306
$KV_PATH$/db/user: root
$KV_PATH$/db/pass: root
$KV_PATH$/app_name: $APP_NAME$
$KV_PATH$/debug: true
```

and `local-consul.env`:

```ini
CONSUL_HTTP_ADDR=consul:8500
UPDATEKV_VARIABLES=KV_PATH,APP_NAME
KV_PATH=app/settings
APP_NAME=My application
```

you can use them in `docker-compose.yml` as simple as:

```yml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./provision:/provision
    env_file: local-consul.env
    command: /provision/kv.yml

  app:
    build: .
    env_file: local-consul.env
    environment:
      - ENV=dev
...
```

## Persistent data and mounts

### Persistent consul data

By default, consul-standalone container doesn't exposes volumes. So no data (including KV) is saved if container is recreated.
It is possible to make consul data persistent by mounting `/consul/data` as a volume:

```bash
$ docker run \
  -v `pwd`/consul/data:/consul/data \
  -v `pwd`/provision:/provision \
  -d \
  --rm \
  -p 8500:8500 pdffiller/consul-standalone \
  /provision/kv.yaml
```

or in case of `docker-compose.yml`

```yml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./provision:/provision
      - ./consul/data:/consul/data
    env_file: local-consul.env
    command: /provision/kv.yml

  app:
    build: .
    env_file: local-consul.env
    environment:
      - ENV=dev
...
```

Keep in mind that the KV provisioning script creates by default only non-existant keys, so if some key exists in consul it will not
be updated from KV file. This behavior can be changed by adding `--force` parameter to docker command after KV file name.
In such case all keys defined in KV file will be updated to values defined in KV file.

Example:

```yml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./provision:/provision
      - ./consul/data:/consul/data
    env_file: local-consul.env
    command: /provision/kv.yml --force

  app:
    build: .
    env_file: local-consul.env
    environment:
      - ENV=dev
...
```

### KV file mounting

In all examples above the KV file was mounted as part of directory. In fact the KV file can be mounted as file itself:

```yml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./kv.yml:/kv.yml
    env_file: local-consul.env
    command: /kv.yml

...
```

But pay attention! Many text editors recreate files when editing leading index number of file changes. Docker
bind mount of file can not handle such changes, so a container will continue execute with old data in KV file.

## Changing KV

Consul KV can be changed at runtime in several ways. Considering you are running following `docker-compose.yml`:

```yml
services:
  consul:
    image: pdffiller/consul-standalone
    ports:
      - "8500:8500"
    volumes:
      - ./provision:/provision
    env_file: local-consul.env
    command: /provision/kv.yml

...
```

you can update consul KV

### With Consul UI

As Consul UI is enabled by default, you can change the KV using your web browser with it at 
[http://localhost:8500/ui/](http://localhost:8500/ui/)


### By changing KV file

1. Change `provision/kv.yml`
2. Update

   with `docker-compose`:

   ```bash
   $ docker-compose exec consul update-kv --force /provision/kv.yml
   ```

   with `docker` CLI:

   ```bash
   $ docker exec <consul-standalone_container_id_or_name> update-kv --force /provision/kv.yml
   ```

### Directly from command line

`update-kv` script can use `STDIN` as input file so it is possible to change data by piping
YAML or JSON to it.

With `docker-compose`:

```bash
$ echo '$KV_PATH$/new_key: new_value' | docker-compose exec -T consul update-kv --force -
```

With `docker` CLI:

```bash
$ echo '$KV_PATH$/new_key: new_value' | docker exec -i <consul-standalone_container_id_or_name> update-kv -
```

# License

pdffiller/consul-standalone is **licensed** under the [**MIT License**](https://github.com/pdffillerdocker/consul-standalone/blob/master/LICENSE).
