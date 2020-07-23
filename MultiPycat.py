from os import system, name, _exit
from datetime import datetime
import argparse

from threading import Thread
import socket

# cli args
parser = argparse.ArgumentParser(description='help')
parser.add_argument('-p', dest='port', type=int, help='port to listen on, defautls to 80')
parser.add_argument('-f', dest='files', type=str, help='server specific files, separated by commas')
args = parser.parse_args()

# files to server for HTTP requests
files_to_serve = []
if args.files:
    files_to_serve = args.files.split(',')

# new connections store
connections = []
addresses = []

# Listen and save socket connections
class MultiHandler(object):
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 80          # Default port if none chosen
        self.socket = None
        
        # change port if specified in arg
        if args.port:
            self.port = int(args.port)

        banner(self.host, self.port)

    # Create and bind to socket, add new connections to array
    def listen(self):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind((self.host, self.port))
        except:
            pass
        self.socket.listen(10)
        
        while True:
            conn, address = self.socket.accept()
            conn.setblocking(1)
            try:
                client_data = conn.recv(1024).decode()
            except:
                pass
            conn_type = self.identify_conn_type(client_data)
            
            # Reverse shells
            if conn_type == "TCP":
                address = address + (conn_type, client_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                connections.append(conn)
                addresses.append(address)
                print('\n{} New connection: {} ({})'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), address[-1], address[0]))
            
            # HTTP file serving
            elif conn_type == "HTTP":
                print('\n{} New HTTP request: {} ({})'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), address[-1], address[0]))
                
                # only serve if user specified file names
                if files_to_serve:
                    try:
                        file_to_download = client_data.split(' ')[1].replace('/', '')
                        if file_to_download in files_to_serve:
                            print("Serving", file_to_download)
                            with open(file_to_download, 'rb') as file_to_send:
                                for data in file_to_send:
                                    conn.sendall(data)
                            print("File was served")
                    except:
                        print("File serving error")

    # Fingerprint connection protocol based on connected client's first input
    def identify_conn_type(self, client_data):
        # currently returns TCP for anything not supported
        # intentionally short on HTTP method support
        conn_type = "TCP"                               
        if client_data.startswith(('GET', 'POST')):
            conn_type = "HTTP"
        return conn_type

# User input as a separate thread to avoid IO blocking
class KeyboardThread(Thread):
    def __init__(self, input_callback = None, name='user-input-thread'):
        self.input_callback = input_callback
        super(KeyboardThread, self).__init__(name=name)
        self.start()

    def run(self):
        while True:
            try:
                self.input_callback(input("MultiPycat> "))
            except EOFError as e:
                cleanup_and_quit()

# Catches callbacks from the keyboard thread so we can parse them
def input_callback(keyboard_input):
    # list all connections
    if keyboard_input.startswith("l"):
        if connections:                            
            i = 0
            for addr in addresses:
                print("{}: {}".format(i, addr))
                i += 1
        else:
            print("No sessions")
    
    # interact with session
    elif keyboard_input.startswith("s"):
        try:
            selection = int(keyboard_input.split(' ')[-1])
            # verify user selection and connect to it
            if connections:
                if selection+1 <= len(connections):
                    print("Connecting to selection")
                    interact_session(connections[selection], addresses[selection])
                else:
                    print("Session not found")
            else:
                print("No sessions")
        except ValueError:
            print("Unrecognized session")

    # list currently serving files
    elif keyboard_input.startswith("fl") or keyboard_input.startswith("filel"):
        if files_to_serve:
            print("Serving: {}".format(files_to_serve))
        else:
            print("No files are served")

    # dynamically add server local file names to files_to_serve
    elif keyboard_input.startswith("fa") or keyboard_input.startswith("filea"):
        try:
            selection = keyboard_input.split(' ')[-1]
            print('Adding "{}" to files_to_serve list'.format(selection))
            files_to_serve.append(selection)
        except ValueError:
            print("Couldn't add file to list")

    # dynamically remove server local file names from files_to_serve
    elif keyboard_input.startswith("fd") or keyboard_input.startswith("filed"):
        try:
            selection = keyboard_input.split(' ')[-1]
            if selection in files_to_serve:
                print('Removing "{}" from files_to_serve list'.format(selection))
                files_to_serve.remove(selection)
            else:
                print("File not in files_to_serve list")
        except ValueError:
            print("Couldn't remove file from list")

    # delete connection
    elif keyboard_input.startswith("d"):
        try:
            selection = int(keyboard_input.split(' ')[-1])
            # verify user selection and connect to it
            if connections:
                if selection+1 <= len(connections):
                    print("Deleting selection")
                    del connections[selection]
                    del addresses[selection]
                else:
                    print("Session not found")
            else:
                print("No sessions")
        except ValueError:
            print("Unrecognized session")
    
    # clear terminal
    elif keyboard_input.startswith("c"):
        if name == 'nt':
            system('cls')
        else:
            system('clear')

    # quit
    elif keyboard_input.startswith("q"):
        cleanup_and_quit()    
    
    # help
    elif keyboard_input.startswith("h"):
        print()
        print("  command             description                         example")
        print("|---------------|-------------------------------------|----------------------------|")
        print("    list:            List existing sessions")
        print("    select:          Interact with session                 select 0")
        print("    delete:          Delete session                        delete 0")
        print("    background:      Return to this interface")
        print("    filelist:        List files we serve over HTTP")
        print("    fileadd:         Add local filename to serve           fileadd ServeMe.png")
        print("    filedelete:      Remove file from serving list         filedelete ServerMe.png")
        print("    clear:           Clear terminal")
        print("    quit:            Quit this interface")
        print()
        
# read tcp
def tcp_rx():
    while True:
        print(conn.recv(1024).decode())

# send tcp
def tcp_tx():
    while True:
        try:
            data = input()
        except EOFError as e:
            main()

        if data == 'back' or data == 'background':
            main()
        conn.send((data + "\n").encode())

# interact with an existing session by opening one thread for tcp_rx and one for txp_tx
def interact_session(new_conn, new_address):
    # set chosen connection as global variables
    global conn
    conn = new_conn
    global address
    address = new_address

    # Rx
    rx = Thread(target=tcp_rx)
    rx.daemon = True
    rx.start()
    
    # Tx
    tx = Thread(target=tcp_tx)
    tx.daemon = True
    tx.start()
    
    rx.join()
    tx.join()

# run-only-once helper function, required because when we go back to the main shell we restart MultiHandler, and we don't want to print server info twice
def banner(host, port):
    print("{} Starting a socket server at {}:{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), host, port))
    # Override function with None so it won't execute again
    banner.__code__ = (lambda h,p: None).__code__

def cleanup_and_quit():
    print("\n exiting..")
    for conn in connections:
        try:
            conn.shutdown(2)
            conn.close()
        except Exception as e:
            print("Error closing connection %s" % str(e))
    _exit(1)

def main():
    # user input handler
    kthread = KeyboardThread(input_callback)

    # listener
    mh = MultiHandler()
    mh.listen()

if __name__ == "__main__":
    main()