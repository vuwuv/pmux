# pmux
python script to batch create tmux sessions

`pmux <yaml filelist>` - start tmux sessions from yaml files

If no yaml files are given, pmux will look for `~/.pmux.yaml`

Options:
-   `-a` - show selection screen for attaching to an existing session
-   `-c` - create local cache file for caching used presets (`~/.pmux.yaml`)
-   `-f` - do not show selection screen for selecting presets to start

Sample yaml files are provided in the `sample` directory.