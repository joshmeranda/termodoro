# Termodoro
A simple but configurable tool for following the pomodoro time management / study / work right in you terminal.

## Setup and Running
To setup simply clone this repo and add a symbolic link to the installation location:

```bash
git clone https://github.com/joshmeranda/termodoro.git
cd termodoro
ln -s ~/.local/bin
```

To change the default behavior you can see [default.ini](/default.ini) for a full list of configuration options.
Termodoro will look in `/etc` and `$HOME/.config` for a file named `termodoro.ini` with configuration settings.