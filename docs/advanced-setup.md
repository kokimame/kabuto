# Advanced Post-installation Tasks

This page explains some advanced tasks and configuration options that can be performed after the bot installation and may be uselful in some environments.

If you do not know what things mentioned here mean, you probably do not need it.

## Configure the bot running as a systemd service

Copy the `freqtrade.service` file to your systemd user directory (usually `~/.config/systemd/user`) and update `WorkingDirectory` and `ExecStart` to match your setup.

!!! Note
    Certain systems (like Raspbian) don't load service unit files from the user directory. In this case, copy `freqtrade.service` into `/etc/systemd/user/` (requires superuser permissions).

After that you can start the daemon with:

```bash
systemctl --user start freqtrade
```

For this to be persistent (run when user is logged out) you'll need to enable `linger` for your freqtrade user.

```bash
sudo loginctl enable-linger "$USER"
```

If you run the bot as a service, you can use systemd service manager as a software watchdog monitoring freqtrade bot 
state and restarting it in the case of failures. If the `internals.sd_notify` parameter is set to true in the 
configuration or the `--sd-notify` command line option is used, the bot will send keep-alive ping messages to systemd 
using the sd_notify (systemd notifications) protocol and will also tell systemd its current state (Running or Stopped) 
when it changes. 

The `freqtrade.service.watchdog` file contains an example of the service unit configuration file which uses systemd 
as the watchdog.

!!! Note
    The sd_notify communication between the bot and the systemd service manager will not work if the bot runs in a Docker container.

## Advanced Logging

On many Linux systems the bot can be configured to send its log messages to `syslog` or `journald` system services. Logging to a remote `syslog` server is also available on Windows. The special values for the `--logfile` command line option can be used for this.

### Logging to syslog

To send Freqtrade log messages to a local or remote `syslog` service use the `--logfile` command line option with the value in the following format:

* `--logfile syslog:<syslog_address>` -- send log messages to `syslog` service using the `<syslog_address>` as the syslog address.

The syslog address can be either a Unix domain socket (socket filename) or a UDP socket specification, consisting of IP address and UDP port, separated by the `:` character.

So, the following are the examples of possible usages:

* `--logfile syslog:/dev/log` -- log to syslog (rsyslog) using the `/dev/log` socket, suitable for most systems.
* `--logfile syslog` -- same as above, the shortcut for `/dev/log`.
* `--logfile syslog:/var/run/syslog` -- log to syslog (rsyslog) using the `/var/run/syslog` socket. Use this on MacOS.
* `--logfile syslog:localhost:514` -- log to local syslog using UDP socket, if it listens on port 514.
* `--logfile syslog:<ip>:514` -- log to remote syslog at IP address and port 514. This may be used on Windows for remote logging to an external syslog server.

Log messages are send to `syslog` with the `user` facility. So you can see them with the following commands:

* `tail -f /var/log/user`, or 
* install a comprehensive graphical viewer (for instance, 'Log File Viewer' for Ubuntu).

On many systems `syslog` (`rsyslog`) fetches data from `journald` (and vice versa), so both `--logfile syslog` or `--logfile journald` can be used and the messages be viewed with both `journalctl` and a syslog viewer utility. You can combine this in any way which suites you better.

For `rsyslog` the messages from the bot can be redirected into a separate dedicated log file. To achieve this, add
```
if $programname startswith "freqtrade" then -/var/log/freqtrade.log
```
to one of the rsyslog configuration files, for example at the end of the `/etc/rsyslog.d/50-default.conf`.

For `syslog` (`rsyslog`), the reduction mode can be switched on. This will reduce the number of repeating messages. For instance, multiple bot Heartbeat messages will be reduced to a single message when nothing else happens with the bot. To achieve this, set in `/etc/rsyslog.conf`:
```
# Filter duplicated messages
$RepeatedMsgReduction on
```

### Logging to journald

This needs the `systemd` python package installed as the dependency, which is not available on Windows. Hence, the whole journald logging functionality is not available for a bot running on Windows.

To send Freqtrade log messages to `journald` system service use the `--logfile` command line option with the value in the following format:

* `--logfile journald` -- send log messages to `journald`.

Log messages are send to `journald` with the `user` facility. So you can see them with the following commands:

* `journalctl -f` -- shows Freqtrade log messages sent to `journald` along with other log messages fetched by `journald`.
* `journalctl -f -u freqtrade.service` -- this command can be used when the bot is run as a `systemd` service.

There are many other options in the `journalctl` utility to filter the messages, see manual pages for this utility.

On many systems `syslog` (`rsyslog`) fetches data from `journald` (and vice versa), so both `--logfile syslog` or `--logfile journald` can be used and the messages be viewed with both `journalctl` and a syslog viewer utility. You can combine this in any way which suites you better.
