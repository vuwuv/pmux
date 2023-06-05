# pmux
python script to batch create tmux sessions

## Commands

`pmux s` - start new sessions
`pmux a` - attach to an existing session
`pmux k` - kill existing sessions

Additional information can be found by running `pmux <command> -h`

## Configuration

### Basic configuration structure

```yaml
sessionName:
    name: sessionName
    multihistory: true
    home: ~
    ssh: 
        server: 
            host: host
            login: user
    windows:
        monitor:
            multihistory: false
            cmd: top
            home: /
            ssh:
                preset: server
                login: monitor
                keyfile: ~/.ssh/id_monitor
        shell:
            ssh: server
```

This config defines session named `sessionName` with default home directory `~` and two windows: `monitor` and `shell`. 
Both windows are ssh sessions to `host` with different logins: `shell` uses default login from `server` preset, while `monitor` uses `monitor` login. 
`monitor` window has `top` command running by default, while `shell` runs default bash. 
`monitor` window has `multihistory` disabled, while `shell` has it enabled and history is saved to a separate file `~/.multihistory/sessionName/shell`.
`monitor` window redefines home directory to `/` and `shell` just runs at session's default home directory `~`.

Session has following options:
- `name` - session name (required)
- `multihistory` - enable/disable multihistory for all windows (optional, default: `false`)
- `home` - default home directory for all windows (optional, default: `~`)
- `ssh` - ssh configuration (optional)

Window has following options:
- `multihistory` - enable/disable multihistory for this window (optional, default: `false` or inherited from session)
- `home` - default home directory for this window (optional, default: `~` or inherited from session)
- `cmd` - command to run in this window (optional, default: shell)
- `ssh` - ssh configuration (optional)

### SSH configuration

```yaml
sessionName:
    name: sessionName
    ssh: 
        host1: 
            host: host1
            login: user
        host2:
            parent: host1
            host: host2
            login: user
        jumphost:
            host: <HOST>
        host4:
            host: host4
            parent: jumphost
            HOST: host3
    windows:
        shell1: 
            ssh: host2            
        shell2:
            ssh: 
                preset: host2
                login: root
        shell3:
            ssh: 
                preset: host2
                parent: 
                    login: root
        shell4:
            ssh: 
                host: host2
                login: user
        shell5:
            ssh: host4
        shell6:
            ssh: 
                preset: host4
                HOST: host5
        shell7: 
            ssh: 
                preset: host4
                parent:
                    parent:
                        host: host7
```

- `shell1` window just uses preset and connects to `host2` using `host1` as a jump host, logging in as `user` at both hosts
- `shell2` window uses preset and connects to `host2` using `host1` as a jump host, redefining login to `root` at `host2`
- `shell3` window uses preset and connects to `host2` using `host1` as a jump host, redefining login to `root` at `host1`
- `shell4` window connects to `host2` directly, logging in as `user`
- `shell5` window connects to `host4` using `host3` as a jump host, logging in as current user at both hosts
- `shell6` window uses preset and connects to `host4` using `host5` as a jump host, redefining `HOST` variable to `host5`
- `shell7` window uses preset and connects to `host4` using `host3` as a jump host, but also adds additional jump host `host7` before `host3`

So generally that means that child preset inherits all fields from parent preset, but can redefine any of them, including variables, and even add additional parents.

Defining `ssh` section at session level is optional. It allows to specify named presets for ssh connections. Presets can be used in other presets or at window level.

SSH configuration has following options:
- `host` - host to connect to (required unless `preset` is specified)
- `port` - port to connect to (optional)
- `login` - login to use (optional)
- `keyfile` - path to keyfile (optional)
- `parent` - parent connection, used for chaining (optional)
- `preset` - name of preset to use (optional)
- any other keys must start with `$` and will be treated as variables. Variables can be used in `host`, `port`, `login` and `keyfile` fields.

If preset is used, it is possible to redefine any of its fields. For example, if preset `host1` is defined as `{host: host1, login: user}`, then `{preset: host1, login: root}` will be treated as `{host: host1, login: root}`. User variables are also redefineable.