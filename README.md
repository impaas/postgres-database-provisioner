# Postgres Database Provisioner for Tsuru

This is a simple service that provisions a Postgres database for Tsuru applications.

## Setup

> [!CAUTION]
> This minimal setup config is for a dev/test environment. It's about as insecure as it gets. Do not use this in production. You have been warned.

### Virtual Machine

In Azure portal:

- Spin up a new Azure VM with Ubuntu, called 'postgres-provisioner'
- Configure rules on the VM's network interface to allow inbound connections from Azure IPs on ports 5432 (postgres) and 4999 (tsuru service API)

SSH into the VM.

Install updates:

```bash
sudo apt update
sudo apt upgrade
```

### Postgres

Install Postgres:

```bash
sudo apt install postgresql
```

Configure Postgres to listen to all connections in `/etc/postgresql/*/main/postgresql.conf`:

```conf
listen_addresses = '*'
```

Configure Postgres to allow any user to remotely authenticate in `/etc/postgresql/*/main/pg_hba.conf`:

```conf
host    all             all             0.0.0.0/0            md5
```

Restart Postgres to apply config: `sudo systemctl restart postgresql.service`

Set a password for the `postgres` user:

```bash
sudo -u postgres psql template1
> ALTER USER postgres with encrypted password 'dummy_password';
```

## Deployment

Clone this repo on the VM:

```bash
git clone git@github.com:impaas/postgres-database-provisioner.git
cd postgres-database-provisioner
```

Edit the credentials in [`app.py`](app.py) to their actual values.

Install dependencies:

```bash
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the service:

```bash
python app.py
```

To run the service in the background, you could use `nohup`:

```bash
nohup python app.py &
```

## Usage

Edit the values in the [service manifest](service-manifest.yaml) to match the actual credentials/IPs.

Create the service:

```bash
impaas service-create service-manifest.yaml
```

Check that the service is available:

```bash
impaas service plan list postgres
```

Bind the service to an app backed by Postgres, such as [this simple Flask todo app](https://github.com/impaas/docs/tree/todo-postgres/demos/todo):

```bash
impaas app create todo-pg python -t demo
impaas app deploy -a todo-pg .
impaas service instance add postgres tododb -t demo
impaas service instance bind postgres tododb --app todo-pg
```

The app should now be able to connect to the provisioned Postgres database.
Visit the app's URL to see it in action, e.g. [todo-pg.impaas.uk](https://todo-pg.impaas.uk).

To tear down the service and app:

```bash
impaas service instance unbind postgres tododb --app todo-pg
impaas service instance remove postgres tododb
impaas app remove -a todo-pg
```
