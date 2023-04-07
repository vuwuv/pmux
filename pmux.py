#!/usr/bin/python3

import yaml
import subprocess
import sys
import string
import curses
import os

userConfigFile = os.path.expanduser("~/.pmux.yaml")

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
                sys.exit(0)
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

def attach(sessionName):
    try:
        subprocess.run(["tmux", "attach", "-t", sessionName], check=True)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("No tmux session found to attach.")
        else:
            print(f"tmux attach failed with return code {e.returncode}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sys.exit()

def execute(cmd, ignoreExitCode = False):
    print(cmd)
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
    setupName = config['name']
    globalHomeDirectory = config.get('home', None)
    globalMultihistory = config.get('multihistory', None)
    multihistoryPath = f'~/.multihistory/{setupName}/'
    if not config['windows']: return
    windows = config['windows']

    sshPresets = config.get('ssh', None)
    if sshPresets == None: sshPresets = dict()
    
    targetWindows = NameCommandList()

    for windowName in windows.keys():
        window = windows[windowName]
        if not window: window = dict()
        historyArg = ''
        mkdirHistoryArg = ''
        homeArg = ''
        multihistory = window.get('multihistory', globalMultihistory)
        homeDirectory = window.get('home', globalHomeDirectory)
        
        if multihistory: 
            historyArg = f'HISTFILE={multihistoryPath}{windowName} '
            mkdirHistoryArg = f'mkdir -p {multihistoryPath}; '
        if homeDirectory: homeArg = f'cd {homeDirectory}; '

        command = f"{homeArg}{mkdirHistoryArg}{historyArg}PROMPT_COMMAND='history -a' /bin/bash"

        if window:
            if cmd := window.get('cmd', None):
                if not isarray(cmd): cmd = [cmd]
                if homeDirectory: cmd = ['cd ' + homeDirectory] + cmd
                command = ' && '.join(cmd)

            if ssh := window.get('ssh', None):
                if not isarray(ssh): ssh = [ssh]
                ssh.reverse()
                for sshStage in ssh:
                    if not isinstance(sshStage, dict): sshStage = sshPresets[sshStage]
                    loginArg = ''
                    if (sshLogin := sshStage.get('login', None)): loginArg = f' -l {sshLogin}'
                    command = f'ssh {sshStage["host"]}{loginArg} -t "{escape(command)}"'

        command = f'"{command}"'

        targetWindows.add_to_first_free_index(windowName, command)

    openWindows = NameCommandList()
    for line in execute(f'tmux list-windows -t {setupName} -F "#{{E:window_index}} @*@ #{{E:window_name}} @*@ #{{E:pane_start_command}}"').split('\n'):
        if not line: continue
        [index, name, command] = line.split(' @*@ ')
        if not command.startswith('"'): command = f'"{command}"'
        openWindows.add(int(index), name, command)

    if openWindows.size() == 0:
        execute(f'tmux new-session -d -s {setupName} -n _default bash')
        openWindows.add(0, '_default', '"bash"')

    usedNames = dict()

    for [index, name, command] in openWindows:
        targetIndex = targetWindows.get_first_index_by_name(name)
        targetCommand = targetIndex != None and targetWindows.get_command(targetIndex) or None

        if targetCommand == command and not name in usedNames:
            usedNames[name] = True
        else:
            if name != '_default':
                if openWindows.size() == 1:
                    freeIndex = openWindows.first_free_index()
                    execute(f'tmux new-window -t {setupName}:{freeIndex} -n _default bash')
                    openWindows.add(freeIndex, "_default", '"bash"')
                execute(f'tmux kill-window -t {setupName}:{index}')
                openWindows.delete_index(index)

    for [index, name, command] in targetWindows:
        if not openWindows.has_name(name) or openWindows.get_command(openWindows.get_first_index_by_name(name)) != command:
            freeIndex = not openWindows.has_index(index) and index or openWindows.first_free_index()
            execute(f'tmux new-window -t {setupName}:{freeIndex} -n {name} {command}')
            openWindows.add(freeIndex, name, command)

        openIndex = openWindows.get_first_index_by_name(name)
        if openIndex != index:
            if openWindows.has_index(index):
                execute(f'tmux swap-window -s {setupName}:{openIndex} -t {setupName}:{index}')
                openWindows.swap_indexes(openIndex, index)
            else:
                execute(f'tmux move-window -s {setupName}:{openIndex} -t {setupName}:{index}')
                openWindows.move_index_to(openIndex, index)
        else:
            execute(f'tmux respawn-pane -t {setupName}:{index}')

        execute(f'tmux set-window-option -t {setupName}:{index} remain-on-exit on')
        execute(f'tmux set-hook -t {setupName}:{index} pane-exited "tmux respawn-pane -t {setupName}:{index}"')
        execute(f'tmux set-hook -t {setupName}:{index} pane-died "tmux respawn-pane -t {setupName}:{index}"')

    if openWindows.has_name('_default'):
        execute(f'tmux kill-window -t {setupName}:_default')
    
def start_sessions(sessions, select = False):
    selectedSessions = list(sessions.keys())
    selectedSessions.sort()
    if select: selectedSessions = choose_elements('sessions to start', selectedSessions)

    for sessionName in selectedSessions:
        session = sessions.get(sessionName)
        start(session)

def help():
    print(f'Usage:')
    print(f'pmux -a: attach to a session')
    print(f'pmux -c: create user local config file for saving used presets ({userConfigFile})')
    print(f'pmux <config file list>')

if len(sys.argv) < 2:
    if not os.path.exists(userConfigFile):
        help()
        sys.exit(1)
    else:
        with open(userConfigFile, "r") as stream:
            try:
                userConfig = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                sys.exit(1)
            
            if userConfig: start_sessions(userConfig.get('presetsCache'), True)

elif sys.argv[1] == '-a':
    sessions = list(filter(lambda x: x != '', execute('tmux list-sessions -F "#S"').split('\n')))

    if len(sessions) > 0:
        sessionName = choose_elements('a session to attach', sessions, True)
        if sessionName != None: attach(sessionName)
    
        print('no sessions found or selected')
        sys.exit(1)
elif sys.argv[1] == '-c':
    with open(userConfigFile, "a+") as f:
        pass
elif sys.argv[1] == '-h' or sys.argv[1] == '--help' or sys.argv[1] == '-?':
    help()
    sys.exit(0)
else:
    userConfig = dict()

    if os.path.exists(userConfigFile):
        with open(userConfigFile, "r") as stream:
            try:
                userConfig = yaml.safe_load(stream) or dict()
                if 'presetsCache' not in userConfig: userConfig['presetsCache'] = dict()
            except yaml.YAMLError as exc:
                print(exc)
                sys.exit(1)

    sessions = dict()
    select = True

    for filename in sys.argv[1:]:
        if filename == '-f': 
            select = False
            continue

        with open(filename, "r") as stream:
            try:
                config = yaml.safe_load(stream)
                
                for sessionName in config.keys():
                    session = config.get(sessionName)
                    if 'name' not in session: 
                        raise Exception(f'no name for session {sessionName}')
                    name = session.get('name')
                    if name in sessions:
                        raise Exception(f'duplicate name {name} for session {sessionName}')
                    sessions[name] = session
                    if userConfig:
                        userConfig['presetsCache'][name] = config.get(sessionName)

            except yaml.YAMLError as exc:
                print(exc)

    start_sessions(sessions, select)

    if userConfig:
        with open(userConfigFile, "w") as stream:
            try:
                yaml.dump(userConfig, stream, default_flow_style=False)
            except yaml.YAMLError as exc:
                print(exc)
                sys.exit(1)
