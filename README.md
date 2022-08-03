## Discord Pi Locator bot
A Discord bot used to get alerts on when raspberry pi's get back in stock. Using the RSS feed of rpilocator.com

The bot also includes the ability to filter *models*, *countries* and *vendors* so that you can only get notified for the things you care about. For more info run `-help` to get a list of all commands, or `-help <command>` to get help regarding a specific command.

### Add it to your server
If you don't want to host it yourself you can just invite the public version using this invite [link](https://discord.com/api/oauth2/authorize?client_id=824761148796698654&permissions=274878187520&scope=bot%20applications.commands).

## Installation and first run
The following instructions will be for a Debian system. **There can be problems if your system uses SELinux!!!**
(It is recommended that you [add yourself](https://docs.docker.com/engine/install/linux-postinstall/) to the docker user group to omit sudo for better security)
### Install docker:

```
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose
```
### Clone the repository
```
git clone https://github.com/diminDDL/discordPiLocator.git
```
### Navigate to installed folder and start the docker container
**Depending on your version of docker compose you will either need to use `docker-compose` or `docker compose` to run this correctly.**
```
cd discordPiLocator
sudo docker-compose up
```
Docker will download all dependencies and start. This can take a while.
After it finishes starting hit `ctrl+c` to stop it and wait until it finishes.

### Set API keys
```
nano ./data/init_settings.json
```
This will open nano editor where you will see something like this:
```
{
    "discord token": "",
    "prefix": "-"
}
```
`discord token` is the discord bot API token you can get from [discord](https://discord.com/developers/). `prefix` is what the bot will use as a command prefix for example `-` or `ex` or any other string or character. Don't forger to turn on `Privileged Gateway Intents` in the discord bot panel (next to the bot API token).

After that is done hit `ctrl + x`, `y` and `enter`. The settings will be saved.

### Starting the bot 
To start the bot from a stopped state (like we have right now), navigate to it's folder (discordPiLocator) and run the following:
```
sudo docker-compose up -d pilocator
```
You will see it print:
```
Starting redis ... done

Starting discordpilocator_pilocator ... done
```
To check the status of the container do `sudo docker container ls` you will see 2 containers `redis:alpine` and `discordpilocator_pilocator` that means everything is running.
Now go to the server that you added the bot to and do -help (or whatever command prefix you chose) to see if it's working.
### Stopping
```
sudo docker-compose stop
```
