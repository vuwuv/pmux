#!/usr/bin/python3

import yaml
import subprocess
import sys
import string
import curses
import os
import argparse

user_config_file = os.path.expanduser("~/.pmux.yaml")
verbose = False

class NameCommandList:
    def __init__(self):
        self.__array = {}

    def add(self, index, name, command):
        if index in self.__array:
            raise KeyError(f"Index {index} already exists.")
        self.__array[index] = (name, command)

    def get_name(self, index):
        if index not in self.__array:
            raise KeyError(f"Index {index} does not exist.")
        return self.__array[index][0]

    def get_command(self, index):
        if index not in self.__array:
            raise KeyError(f"Index {index} does not exist.")
        return self.__array[index][1]

    def has_index(self, index):
        return index in self.__array

    def has_name(self, name):
        return any(n == name for n, _ in self.__array.values())

    def has_command(self, command):
        return any(c == command for _, c in self.__array.values())

    def indexes_by_name(self, name):
        return [index for index, (n, _) in self.__array.items() if n == name]

    def indexes_by_command(self, command):
        return [index for index, (_, c) in self.__array.items() if c == command]

    def delete_index(self, index):
        if index not in self.__array:
            raise KeyError(f"Index {index} does not exist.")
        del self.__array[index]

    def first_free_index(self):
        i = 0
        while i in self.__array:
            i += 1
        return i

    def add_to_first_free_index(self, name, command):
        index = self.first_free_index()
        self.add(index, name, command)

    def set(self, index, name, command):
        if index not in self.__array:
            raise KeyError(f"Index {index} does not exist.")
        self.__array[index] = (name, command)

    def get_first_index_by_name(self, name):
        for index, (n, _) in self.__array.items():
            if n == name:
                return index
        return None

    def swap_indexes(self, index1, index2):
        if index1 not in self.__array or index2 not in self.__array:
            raise KeyError(f"Both index1 {index1} and index2 {index2} must exist.")
        self.__array[index1], self.__array[index2] = self.__array[index2], self.__array[index1]

    def move_index_to(self, source_index, target_index):
        if source_index not in self.__array:
            raise KeyError(f"Source index {source_index} does not exist.")
        if target_index in self.__array:
            raise KeyError(f"Target index {target_index} already exists.")
        self.__array[target_index] = self.__array[source_index]
        del self.__array[source_index]

    def size(self):
        return len(self.__array)

    def __iter__(self):
        return NameCommandIterator(self.__array)

class NameCommandIterator:
    def __init__(self, array):
        self.array = array
        self.indexes = iter(sorted(self.array.keys()))

    def __iter__(self):
        return self

    def __next__(self):
        index = next(self.indexes)
        name, command = self.array[index]
        return (index, name, command)

def read_key(window):
    return window.getch()

def choose_elements(hint, items, unique_selection=False):
    def draw_elements(window, start_index):
        max_y, max_x = window.getmaxyx()
        window.clear()
        window.addstr(0, 0, f"Select {hint}:")
        for i, item in enumerate(items[start_index:start_index + 36]):
            if i + 1 < max_y - 2:
                selected_mark = '*' if start_index + i in selected_items else ' '
                window.addstr(i + 1, 0, f"{selected_mark} {index_chars[i]}: {item}")
        if max_y - 2 > 0:
            line = unique_selection and "Commands: index letter or number, PGUP, PGDN, ESC (exit)" or "Commands: index letter or number, PGUP, PGDN, TAB (select all on the screen), SPACE (select all), ENTER (confirm), BACKSPACE (clear), ESC (exit)"
            window.addstr(max_y - 3, 0, line)
        window.refresh()

    def main(window):
        nonlocal selected_items
        curses.cbreak()
        window.keypad(1)
        curses.use_default_colors()
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        current_index = 0

        while True:
            draw_elements(window, current_index)
            user_input = read_key(window)

            if user_input == curses.KEY_PPAGE:  # PGUP
                current_index = max(0, current_index - 36)
            elif user_input == curses.KEY_NPAGE:  # PGDN
                current_index = min(len(items) - 36, current_index + 36)
            elif user_input == 10:  # ENTER
                break
            elif user_input == 27:  # ESC
                exit(0)
                break
            elif user_input == curses.KEY_BACKSPACE:  # BACKSPACE
                selected_items.clear()
            elif user_input == ord(' '):  # SPACE
                if len(selected_items) == len(items):
                    selected_items.clear()
                else:
                    selected_items = sorted(range(len(items)))
            elif user_input == ord('\t'):  # TAB
                displayed_items = set(range(current_index, min(current_index + 36, len(items))))
                if displayed_items.issubset(selected_items):
                    selected_items = sorted(set(selected_items).difference(displayed_items))
                else:
                    selected_items = sorted(set(selected_items).union(displayed_items))
            elif user_input == curses.KEY_MOUSE:
                _, x, y, _, button_state = curses.getmouse()
                if 1 <= y < len(items) - current_index + 1 and button_state & curses.BUTTON1_CLICKED:
                    index = y - 1 + current_index
                    if unique_selection:
                        return items[index] if index < len(items) else None
                    elif index in selected_items:
                        selected_items.remove(index)
                    else:
                        selected_items.append(index)
                        selected_items.sort()
            elif chr(user_input) in index_chars:
                index = index_chars.index(chr(user_input)) + current_index
                if unique_selection:
                    return items[index] if index < len(items) else None
                elif index in selected_items:
                    selected_items.remove(index)
                else:
                    selected_items.append(index)
                    selected_items.sort()

    index_chars = string.ascii_lowercase + string.digits
    selected_items = list()

    result = curses.wrapper(main)
    return result if unique_selection else [items[i] for i in selected_items]

def verify_ssh_config(session_name, ssh_name, ssh_config):
    if not isinstance(ssh_config, dict) and not isinstance(ssh_config, str):
        raise TypeError(f"ssh {session_name}.{ssh_name} must be a dictionary or a string")
    
    if isinstance(ssh_config, str):
        return

    if "host" in ssh_config and not isinstance(ssh_config["host"], str):
        raise KeyError(f"ssh {session_name}.{ssh_name} must contain a host (host: string)")

    if "login" in ssh_config and not isinstance(ssh_config["login"], str):
        raise KeyError(f"ssh {session_name}.{ssh_name} login must be a string")

    if "port" in ssh_config and not isinstance(ssh_config["port"], int):
        raise KeyError(f"ssh {session_name}.{ssh_name} port must be an integer")

    if "keyfile" in ssh_config and not isinstance(ssh_config["keyfile"], str):
        raise KeyError(f"ssh {session_name}.{ssh_name} keyfile must be a string")

    if "preset" in ssh_config and not isinstance(ssh_config["preset"], str):
        raise KeyError(f"ssh {session_name}.{ssh_name} preset must be a string")

    if "parent" in ssh_config and not isinstance(ssh_config["parent"], str) and not isinstance(ssh_config["parent"], dict):
        print(ssh_config["parent"])
        raise KeyError(f"ssh {session_name}.{ssh_name} parent must be a string or a dictionary")

    if "parent" in ssh_config and isinstance(ssh_config["parent"], dict):
        verify_ssh_config(session_name, ssh_name + ".parent", ssh_config["parent"])

    for key in ssh_config:
        if key not in ["host", "login", "port", "keyfile", "preset", "parent"] and not key.startswith("$"):
            raise KeyError(f"ssh {session_name}.{ssh_name} contains an unknown key {key}")

def verify_window_config(session_name, window_name, window_config):
    if not isinstance(window_config, dict) and not window_config is None:
        raise TypeError(f"window {session_name}.{window_name} must be a dictionary or empty")

    if window_config is None:
        return

    if "home" in window_config and not isinstance(window_config["home"], str):
        raise KeyError(f"window {session_name}.{window_name} home must be a string")

    if "multihistory" in window_config and not isinstance(window_config["multihistory"], bool):
        raise KeyError(f"window {session_name}.{window_name} multihistory must be a boolean")

    if "cmd" in window_config and not isinstance(window_config["cmd"], str):
        raise KeyError(f"window {session_name}.{window_name} cmd must be a string")

    if "ssh" in window_config:
        verify_ssh_config(session_name, window_name, window_config["ssh"])

    for key in window_config.keys():
        if key not in ["home", "multihistory", "cmd", "ssh"]:
            raise KeyError(f"window {session_name}.{window_name} contains unknown key '{key}'")

def verify_session_config(session_name, session_config):
    if not isinstance(session_config, dict):
        raise TypeError(f"session {session_name} must be a dictionary")     
    
    if "name" not in session_config or not isinstance(session_config["name"], str):
        raise KeyError(f"session {session_name} must contain a name (name: string)")

    if "home" in session_config and not isinstance(session_config["home"], str):
        raise KeyError(f"session {session_name} home must be a string")

    if "windows" not in session_config or not isinstance(session_config["windows"], dict):
        raise KeyError(f"session {session_name} must contain a windows (windows: dictionary)")        

    if "ssh" in session_config:
        for ssh_name, ssh_config in session_config["ssh"].items():
            verify_ssh_config(session_name, ssh_name, ssh_config)

    if "multihistory" in session_config and not isinstance(session_config["multihistory"], bool):
        raise KeyError("multihistory must be a boolean")

    for key in session_config:
        if key not in ["name", "home", "windows", "ssh", "multihistory"]:
            raise KeyError(f"session {session_name} contains unknown key '{key}'")

    for window_name, window_config in session_config["windows"].items():
        verify_window_config(session_name, window_name, window_config)

def template_replace(template_string, variables):
    NORMAL = 0
    ESCAPE = 1
    BRACE = 2

    state = NORMAL
    output = ""
    buffer = ""

    for char in template_string:
        if state == NORMAL:
            if char == '\\':
                state = ESCAPE
            elif char == '<':
                state = BRACE
                buffer = ""
            else:
                output += char
        elif state == ESCAPE:
            output += char
            state = NORMAL
        elif state == BRACE:
            if char == '>':
                if not buffer in variables:
                    raise KeyError(f"variable '{buffer}' is not defined")
                output += str(variables.get(buffer, ''))
                state = NORMAL
            else:
                buffer += char

    return output

def template_ssh_config(ssh_config, user_vars = {}):
    if not isinstance(ssh_config, dict):
        raise TypeError(f"ssh_config must be a dictionary")

    result = {}
    vars_block = user_vars.copy()

    for key in ssh_config:
        if key.startswith("$"):
            vars_block[key[1:]] = ssh_config[key]

    for key in ssh_config:
        if key in ["host", "login", "port", "keyfile"]:
            result[key] = template_replace(str(ssh_config[key]), vars_block)

    if 'parent' in ssh_config:
        result['parent'] = template_ssh_config(ssh_config['parent'], vars_block)

    return result

def use_ssh_preset(target_config, preset_config):
    ssh_config = {}

    if preset_config:
        for key in preset_config:
            ssh_config[key] = preset_config[key]

    for key in target_config:
        ssh_config[key] = target_config[key]

    if "preset" in ssh_config:
        del ssh_config["preset"]

    return ssh_config

def fill_ssh_config(ssh_presets, ssh_config = None, preset_config = None, visited_names = []):
    if ssh_config is None:
        for ssh_name in ssh_presets:
            fill_ssh_config(ssh_presets, ssh_name)
        return

    ssh_name = None

    if isinstance(ssh_config, str):
        ssh_name = ssh_config
        if not ssh_name in ssh_presets:
            raise KeyError(f"ssh preset {ssh_name} not found")
        ssh_config = ssh_presets[ssh_name]

    if isinstance(ssh_config, str):
        if not ssh_config in ssh_presets:
            raise KeyError(f"ssh preset {ssh_config} not found")
        ssh_config = ssh_presets[ssh_config]

    if ssh_name:
        if visited_names.count(ssh_name) > 0:
            raise KeyError(f"ssh preset circular reference: {visited_names + [ssh_name]}")
        visited_names = visited_names + [ssh_name]

    if isinstance(preset_config, str):
        fill_ssh_config(ssh_presets, preset_config, visited_names)
        preset_config = ssh_presets[preset_config]

    if "preset" in ssh_config:
        fill_ssh_config(ssh_presets, ssh_config["preset"], visited_names = visited_names)
        preset_config = use_ssh_preset(ssh_presets[ssh_config["preset"]], preset_config)

    parent_config = ssh_config.get("parent", None)

    if parent_config:
        if isinstance(parent_config, str):
            fill_ssh_config(ssh_presets, parent_config, visited_names = visited_names)
            parent_config = ssh_presets[parent_config]

        if preset_config and 'parent' in preset_config:
            parent_config = use_ssh_preset(parent_config, preset_config['parent'])

        ssh_config['parent'] = parent_config
        fill_ssh_config(ssh_presets, parent_config, visited_names = visited_names)

    if preset_config:
        ssh_config = use_ssh_preset(ssh_config, preset_config)

    if ssh_name:
        ssh_presets[ssh_name] = ssh_config

    return ssh_config

def attach(session_name):
    exitcode = 0

    try:
        subprocess.run(["tmux", "attach", "-t", session_name], check=True)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("No tmux session found to attach.")
        else:
            print(f"tmux attach failed with return code {e.returncode}")
        exitcode = 1
    except KeyboardInterrupt:
        print("\nExiting...")
        exitcode = 1
    finally:
        exit(exitcode)

def execute(cmd, ignoreExitCode = False):
    if verbose: print(cmd)
    output = ""
    try:
        output = subprocess.check_output(['/bin/bash', '-c', cmd], stderr=subprocess.STDOUT).decode('utf8')
    except subprocess.CalledProcessError: 
        if (not ignoreExitCode): pass
    return output

def escape(cmd):
    result = "$'" + cmd.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return result

def isarray(var):
    return isinstance(var, list) and not isinstance(var, (str))

def start(config):
    setup_name = config['name']
    global_home_directory = config.get('home', None)
    global_multihistory = config.get('multihistory', None)
    multihistory_path = f'~/.multihistory/{setup_name}/'
    if not config['windows']: return
    windows = config['windows']

    ssh_presets = config.get('ssh', None)
    if ssh_presets == None: ssh_presets = dict()
    
    fill_ssh_config(ssh_presets)

    for window_name in windows.keys():
        window = windows[window_name]

        if window and 'ssh' in window:
            ssh_template = fill_ssh_config(ssh_presets, window['ssh'])
            ssh_config = template_ssh_config(ssh_template)

            ssh_stages = []
            while ssh_config:
                ssh_stages.append(ssh_config)
                ssh_config = ssh_config.get('parent', None)

            window['ssh'] = ssh_stages

    target_windows = NameCommandList()

    for window_name in windows.keys():
        window = windows[window_name]
        if not window: window = dict()
        history_arg = ''
        mkdirhistory_arg = ''
        home_arg = ''
        multihistory = window.get('multihistory', global_multihistory)
        home_directory = window.get('home', global_home_directory)
        
        if multihistory: 
            history_arg = f'HISTFILE={multihistory_path}{window_name} '
            mkdirhistory_arg = f'mkdir -p {multihistory_path}; '
        if home_directory: home_arg = f'cd {home_directory}; '

        command = f"{home_arg}{mkdirhistory_arg}{history_arg}PROMPT_COMMAND='history -a' /bin/bash"

        if window:
            if cmd := window.get('cmd', None):
                if not isarray(cmd): cmd = [cmd]
                if home_directory: cmd = ['cd ' + home_directory] + cmd
                command = ' && '.join(cmd)

            if ssh := window.get('ssh', None):
                for ssh_stage in ssh:
                    port_arg = ''
                    login_arg = ''
                    keyfile_arg = ''
                    if (ssh_login := ssh_stage.get('login', None)): login_arg = f' -l {ssh_login}'
                    if (ssh_keyfile := ssh_stage.get('keyfile', None)): keyfile_arg = f' -i {ssh_keyfile}'
                    if (ssh_port := ssh_stage.get('port', None)): port_arg = f' -p {ssh_port}'
                    command = f'ssh {ssh_stage["host"]}{login_arg}{keyfile_arg}{port_arg} -t {escape(command)}'

        #command = f'"{command}"'
        command = f'{escape(command)}'

        target_windows.add_to_first_free_index(window_name, command)

    open_windows = NameCommandList()
    for line in execute(f'tmux list-windows -t {setup_name} -F "#{{E:window_index}} @*@ #{{E:window_name}} @*@ #{{E:pane_start_command}}"').split('\n'):
        if not line: continue
        [index, name, command] = line.split(' @*@ ')
        if not command.startswith('"'): command = f'"{command}"'
        open_windows.add(int(index), name, command)

    if open_windows.size() == 0:
        execute(f'tmux new-session -d -s {setup_name} -n _default bash')
        open_windows.add(0, '_default', '"bash"')

    used_names = dict()

    for [index, name, command] in open_windows:
        target_index = target_windows.get_first_index_by_name(name)
        target_command = target_index != None and target_windows.get_command(target_index) or None

        if target_command == command and not name in used_names:
            used_names[name] = True
        else:
            if name != '_default':
                if open_windows.size() == 1:
                    free_index = open_windows.first_free_index()
                    execute(f'tmux new-window -t {setup_name}:{free_index} -n _default bash')
                    open_windows.add(free_index, "_default", '"bash"')
                execute(f'tmux kill-window -t {setup_name}:{index}')
                open_windows.delete_index(index)

    for [index, name, command] in target_windows:
        if not open_windows.has_name(name) or open_windows.get_command(open_windows.get_first_index_by_name(name)) != command:
            free_index = not open_windows.has_index(index) and index or open_windows.first_free_index()
            execute(f'tmux new-window -t {setup_name}:{free_index} -n {name} {command}')
            open_windows.add(free_index, name, command)

        open_index = open_windows.get_first_index_by_name(name)
        if open_index != index:
            if open_windows.has_index(index):
                execute(f'tmux swap-window -s {setup_name}:{open_index} -t {setup_name}:{index}')
                open_windows.swap_indexes(open_index, index)
            else:
                execute(f'tmux move-window -s {setup_name}:{open_index} -t {setup_name}:{index}')
                open_windows.move_index_to(open_index, index)
        else:
            execute(f'tmux respawn-pane -t {setup_name}:{index}')

        execute(f'tmux set-window-option -t {setup_name}:{index} remain-on-exit on')
        execute(f'tmux set-hook -t {setup_name}:{index} pane-exited "tmux respawn-pane -t {setup_name}:{index}"')
        execute(f'tmux set-hook -t {setup_name}:{index} pane-died "tmux respawn-pane -t {setup_name}:{index}"')

    if open_windows.has_name('_default'):
        execute(f'tmux kill-window -t {setup_name}:_default')

def run_attach(args):
    sessions = list(filter(lambda x: x != '', execute('tmux list-sessions -F "#S"').split('\n')))

    if len(sessions) > 0:
        session_name = args.name
        if session_name == None:
            session_name = choose_elements('a session to attach', sessions, True)
        if session_name != None and session_name in sessions: 
            attach(session_name)
        else:
            raise Exception(f'session not found: {session_name}')
    else:
        raise Exception('no sessions running')

def run_start(args):
    files = args.files
    save = args.save
    user_config = None

    if os.path.exists(user_config_file): 
        with open(user_config_file, "r") as stream:
            user_config = yaml.safe_load(stream)

    sessions = dict()

    if len(files) > 0:
        for file in files:
            if os.path.exists(file):
                with open(file, "r") as stream:
                    config = yaml.safe_load(stream)
                    for session_name in config:
                        if session_name in sessions:
                            raise Exception(f'session {session_name} already defined')
                        sessions[session_name] = config[session_name]
            else:
                raise Exception(f'no such file: {file}')
    else:
        if user_config is not None and 'presetsCache' in user_config:
            sessions = user_config['presetsCache']
            save = False
        else: 
            raise Exception('no files specified')
    
    for session_name in sessions:
        session = sessions[session_name]
        verify_session_config(session_name, session)

    names = list(sessions.keys())

    if not args.all:
        if not args.names or len(args.names) == 0:
            names = choose_elements('sessions to start', names)
        else:
            names = args.names
            for name in names:
                if not name in names:
                    raise Exception(f'no such session: {name}')

    if save:
        if user_config is None: user_config = dict()
        if not 'presetsCache' in user_config: user_config['presetsCache'] = dict()
        for session_name in names:
            user_config['presetsCache'][session_name] = sessions[session_name]
        with open(user_config_file, "w") as stream:
            yaml.dump(user_config, stream)

    for session_name in names:
        start(sessions[session_name])    

def run_kill(args):
    names = args.names

    sessions = list(filter(lambda x: x != '', execute('tmux list-sessions -F "#S"').split('\n')))

    if len(sessions) == 0:
        raise Exception('no sessions running')

    if len(names) == 0:
        if args.all:
            names = sessions
        else:
            names = choose_elements('sessions to kill', sessions)
    else:
        for name in names:
            if not name in sessions:
                raise Exception(f'no such session: {name}')

    for name in names:
        execute(f'tmux kill-session -t {name}')

def run_reload(args):
    names = args.names

    sessions = list(filter(lambda x: x != '', execute('tmux list-sessions -F "#S"').split('\n')))

    if len(sessions) == 0:
        raise Exception('no sessions running')

    if len(names) == 0:
        if args.all:
            names = sessions
        else:
            names = choose_elements('sessions to reload', sessions)
    else:
        for name in names:
            if not name in sessions:
                raise Exception(f'no such session: {name}')

    for name in names:
        for line in execute(f'tmux list-windows -t {name} -F "#{{E:window_index}} @*@ #{{E:window_name}} @*@ #{{E:pane_dead}}"').split('\n'):
            if not line: continue
            [index, pane, dead] = line.split(' @*@ ')
            if dead == '1':
                execute(f'tmux respawn-pane -t {name}:{index}')

parser = argparse.ArgumentParser(description='tmux session manager')
subparsers = parser.add_subparsers(help='sub-command help', dest='command')

start_parser = subparsers.add_parser('s', description='start new sessions from yaml configs (select at selection screen)')
start_parser.add_argument('-a', '--all', action='store_true', help='process all the sessions omitting selection screen')
start_parser.add_argument('-s', '--save', action='store_true', help='save started sessions to config file')
start_parser.add_argument('-n', '--names', nargs='*', help='session names to start')
start_parser.add_argument('-v', '--verbose', action='store_true', help='print tmux commands executed')
start_parser.add_argument('files', nargs='*', help='yaml config files to start sessions from')

kill_parser = subparsers.add_parser('k', description='kill sessions (session list or select at selection screen)')
kill_parser.add_argument('-a', '--all', action='store_true', help='process all the sessions omitting selection screen')
kill_parser.add_argument('-v', '--verbose', action='store_true', help='print tmux commands executed')
kill_parser.add_argument('names', nargs='*', help='session names to kill')

attach_parser = subparsers.add_parser('a', description='attach to session (session name or select at selection screen)')
attach_parser.add_argument('-v', '--verbose', action='store_true', help='print tmux commands executed')
attach_parser.add_argument('name', nargs='?', help='session name to attach to')

reload_parser = subparsers.add_parser('r', description='reload windows (session list or select at selection screen)')
reload_parser.add_argument('-v', '--verbose', action='store_true', help='print tmux commands executed')
reload_parser.add_argument('-a', '--all', action='store_true', help='process all the sessions omitting selection screen')
reload_parser.add_argument('names', nargs='*', help='session names to reload')

help_parser = subparsers.add_parser('h', help='show help')

subparsers_actions = [
    action for action in parser._actions 
    if isinstance(action, argparse._SubParsersAction)]

args = parser.parse_args()

if 'verbose' in args:
    verbose = args.verbose

try:
    if args.command == 's':
        run_start(args)
    elif args.command == 'k':
        run_kill(args)
    elif args.command == 'a':
        run_attach(args)
    elif args.command == 'r':
        run_reload(args)
    elif args.command == 'h':
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                print("command '{}': {}".format(choice, subparser.format_help()))
except Exception as e:
    print(e)
    #raise e

exit(0)
