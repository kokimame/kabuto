# Using Freqtrade with Docker

## Install Docker

Start by downloading and installing Docker CE for your platform:

* [Mac](https://docs.docker.com/docker-for-mac/install/)
* [Windows](https://docs.docker.com/docker-for-windows/install/)
* [Linux](https://docs.docker.com/install/)

Optionally, [`docker-compose`](https://docs.docker.com/compose/install/) should be installed and available to follow the [docker quick start guide](#docker-quick-start).

Once you have Docker installed, simply prepare the config file (e.g. `config.json`) and run the image for `freqtrade` as explained below.

## Freqtrade with docker-compose

Freqtrade provides an official Docker image on [Dockerhub](https://hub.docker.com/r/freqtradeorg/freqtrade/), as well as a [docker-compose file](https://github.com/freqtrade/freqtrade/blob/develop/docker-compose.yml) ready for usage.

!!! Note
    - The following section assumes that `docker` and `docker-compose` are installed and available to the logged in user.
    - All below commands use relative directories and will have to be executed from the directory containing the `docker-compose.yml` file.

### Docker quick start

Create a new directory and place the [docker-compose file](https://github.com/freqtrade/freqtrade/blob/develop/docker-compose.yml) in this directory.

=== "PC/MAC/Linux"
    ``` bash
    mkdir ft_userdata
    cd ft_userdata/
    # Download the docker-compose file from the repository
    curl https://raw.githubusercontent.com/freqtrade/freqtrade/master/docker-compose.yml -o docker-compose.yml

    # Pull the freqtrade image
    docker-compose pull

    # Create user directory structure
    docker-compose run --rm freqtrade create-userdir --userdir user_data

    # Create configuration - Requires answering interactive questions
    docker-compose run --rm freqtrade new-config --config user_data/config.json
    ```

=== "RaspberryPi"
    ``` bash
    mkdir ft_userdata
    cd ft_userdata/
    # Download the docker-compose file from the repository
    curl https://raw.githubusercontent.com/freqtrade/freqtrade/master/docker-compose.yml -o docker-compose.yml

    # Pull the freqtrade image
    docker-compose pull

    # Create user directory structure
    docker-compose run --rm freqtrade create-userdir --userdir user_data

    # Create configuration - Requires answering interactive questions
    docker-compose run --rm freqtrade new-config --config user_data/config.json
    ```

    !!! Note "Change your docker Image"
        You have to change the docker image in the docker-compose file for your Raspberry build to work properly.
        ``` yml
        image: freqtradeorg/freqtrade:master_pi
        # image: freqtradeorg/freqtrade:develop_pi
        ```

The above snippet creates a new directory called `ft_userdata`, downloads the latest compose file and pulls the freqtrade image.
The last 2 steps in the snippet create the directory with `user_data`, as well as (interactively) the default configuration based on your selections.

!!! Question "How to edit the bot configuration?"
    You can edit the configuration at any time, which is available as `user_data/config.json` (within the directory `ft_userdata`) when using the above configuration.

    You can also change the both Strategy and commands by editing the `docker-compose.yml` file.

#### Adding a custom strategy

1. The configuration is now available as `user_data/config.json`
2. Copy a custom strategy to the directory `user_data/strategies/`
3. add the Strategy' class name to the `docker-compose.yml` file

The `SampleStrategy` is run by default.

!!! Warning "`SampleStrategy` is just a demo!"
    The `SampleStrategy` is there for your reference and give you ideas for your own strategy.
    Please always backtest the strategy and use dry-run for some time before risking real money!

Once this is done, you're ready to launch the bot in trading mode (Dry-run or Live-trading, depending on your answer to the corresponding question you made above).

``` bash
docker-compose up -d
```

#### Docker-compose logs

Logs will be located at: `user_data/logs/freqtrade.log`. 
You can check the latest log with the command `docker-compose logs -f`.

#### Database

The database will be at: `user_data/tradesv3.sqlite`

#### Updating freqtrade with docker-compose

To update freqtrade when using `docker-compose` is as simple as running the following 2 commands:

``` bash
# Download the latest image
docker-compose pull
# Restart the image
docker-compose up -d
```

This will first pull the latest image, and will then restart the container with the just pulled version.

!!! Warning "Check the Changelog"
    You should always check the changelog for breaking changes / manual interventions required and make sure the bot starts correctly after the update.

### Editing the docker-compose file

Advanced users may edit the docker-compose file further to include all possible options or arguments.

All possible freqtrade arguments will be available by running `docker-compose run --rm freqtrade <command> <optional arguments>`.

!!! Note "`docker-compose run --rm`"
    Including `--rm` will clean up the container after completion, and is highly recommended for all modes except trading mode (running with `freqtrade trade` command).

#### Example: Download data with docker-compose

Download backtesting data for 5 days for the pair ETH/BTC and 1h timeframe from Binance. The data will be stored in the directory `user_data/data/` on the host.

``` bash
docker-compose run --rm freqtrade download-data --pairs ETH/BTC --exchange binance --days 5 -t 1h
```

Head over to the [Data Downloading Documentation](data-download.md) for more details on downloading data.

#### Example: Backtest with docker-compose

Run backtesting in docker-containers for SampleStrategy and specified timerange of historical data, on 5m timeframe:

``` bash
docker-compose run --rm freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20190801-20191001 -i 5m
```

Head over to the [Backtesting Documentation](backtesting.md) to learn more.

### Additional dependencies with docker-compose

If your strategy requires dependencies not included in the default image (like [technical](https://github.com/freqtrade/technical)) - it will be necessary to build the image on your host.
For this, please create a Dockerfile containing installation steps for the additional dependencies (have a look at [Dockerfile.technical](https://github.com/freqtrade/freqtrade/blob/develop/Dockerfile.technical) for an example).

You'll then also need to modify the `docker-compose.yml` file and uncomment the build step, as well as rename the image to avoid naming collisions.

``` yaml
    image: freqtrade_custom
    build:
      context: .
      dockerfile: "./Dockerfile.<yourextension>"
```

You can then run `docker-compose build` to build the docker image, and run it using the commands described above.
