import socket
import sys
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ip = sys.argv[1]
port = int(sys.argv[2])
path = sys.argv[3]
timeOver = int(sys.argv[4])
FLAG = False
index = 0
IN_TIMEOUT = False

# the class Event extends eventhandler
# and responsible for connecting to the server whenever the directory changed
class Event(FileSystemEventHandler):
    def on_created(self, event):
        pass

    def on_modified(self, event):
        pass

    # on any event, the client first creating a new socket and connect it to the server
    # then, the client sending the server a number from 0 to 10, each number feature a new event (deletion, creation...)
    # after that, the client sends the server his ID number and Index in order to be recognized by the server
    # and updating the server with the event.
    def on_any_event(self, event):
        global index, IN_TIMEOUT
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        if event.is_directory:
            global FLAG
            if event.event_type == 'modified':
                pass
            # create new dir
            elif event.event_type == 'created':
                FLAG = True
                s.send(b'4')  # acknowledge the server that the event is a creating of a new directory
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)    # sending the server the name of the directory and it's path
            # delete dir
            elif event.event_type == 'deleted':
                s.send(b'5')    # acknowledge the server that the event is a  of deletetion of directory
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)
            # renaming a directory
            elif event.event_type == 'moved':
                s.send(b'7')
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)  # sending the server the old path and name of the directory
                send_name(s, event.dest_path)  # sending the server the new path and name of the directory
        else:
            if event.event_type == 'modified':
                # ignoring goutputstream events
                if "goutputstream" in event.src_path:
                    pass
                # modify a file
                else:
                    s.send(b'9')
                    s.recv(2)
                    s.send(id_number.encode('UTF-8'))
                    s.recv(2)
                    s.send(index.to_bytes(4, 'big'))
                    s.recv(2)
                    send_file(s, event.src_path)    # sending the modified new file to the server
                    if s.recv(2) == b'0':
                        send_name(s, event.src_path)
                        send_file(s, event.src_path)
            # create file
            elif event.event_type == 'created':
                FLAG = True
                s.send(b'8')
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)
            # delete file
            elif event.event_type == 'deleted':
                s.send(b'5')
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)
            elif event.event_type == 'moved':
                # rename file
                s.send(b'7')
                s.recv(2)
                s.send(id_number.encode('UTF-8'))
                s.recv(2)
                s.send(index.to_bytes(4, 'big'))
                s.recv(2)
                send_name(s, event.src_path)
                send_name(s, event.dest_path)
                # update file
                if FLAG:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((ip, port))
                    s.send(b'9')
                    s.recv(2)
                    s.send(id_number.encode('UTF-8'))
                    s.recv(2)
                    s.send(index.to_bytes(4, 'big'))
                    s.recv(2)
                    send_file(s, event.dest_path)
                    if s.recv(2) == b'0':
                        send_name(s, event.dest_path)
                        send_file(s, event.dest_path)
                    FLAG = False

# function gets a file path and a data and creating the file and writing the data to the file
def write_file(file_name, data):
    file = open(file_name, "wb")
    file.write(data)
    file.close()

# the function responsible on the first connection with the server,
# when the client still doesn't have id number.
# param: a socket with the server (s1)
# the function gets from the server the client's id number and index for future communicates.
def first_connection(s1):
    global index
    id = s1.recv(128).decode('UTF-8')
    s1.send(b'ok')
    index = s1.recv(4)
    index = int.from_bytes(index, 'big')
    return id

# the function sending the server a directory and all of its files in it.
# param: socket s2, path path1 (path of a directory), string id
# function sending the server the directory and all of it's content.
def send_dir(s2, path1, id):
    num_of_files = len(os.listdir(path1))
    s2.send(num_of_files.to_bytes(4, 'big'))    # sends to the server the number of files in the directory
    s2.recv(2)
    for file in os.listdir(path1):
        s2.send(len(file.encode('UTF-8')).to_bytes(4, 'big'))
        s2.recv(2)
        s2.send(file.encode('UTF-8'))
        s2.recv(2)
        # if the file is a directory, then performing a recursive call with the inner directory
        if os.path.isdir(os.path.join(path1, file)):
            s2.send(b'1')
            s2.recv(2)
            send_dir(s2, os.path.join(path1, file), id)
        else:
            s2.send(b'0')
            s2.recv(2)
            size = (os.path.getsize(os.path.join(path1, file)))
            s2.send(size.to_bytes(4, 'big'))    # sending the size of the file
            s2.recv(2)
            data = open((os.path.join(path1, file)), "rb").read()
            i = 0
            s = size
            # sending the file
            while size > 5000:
                d = data[i:i + 5000]
                s2.send(d)
                s2.recv(2)
                size = size - 5000
                i = i + 5000
            d = data[i:s]
            s2.send(d)
            s2.recv(2)


# param: socket s3, path path3 (path of a file)
# function sending the server the file (and it's content)
def send_file(s3, path3):
    name = path3[len((sys.argv[3])) + 1:]
    s3.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
    s3.recv(2)
    s3.send(name.encode('UTF-8'))
    s3.recv(2)
    size = (os.path.getsize(path3))
    s3.send(size.to_bytes(4, 'big'))
    s3.recv(2)
    data = open(path3, "rb").read()
    i = 0
    s = size
    while size > 5000:
        d = data[i:i + 5000]
        s3.send(d)
        s3.recv(2)
        size = size - 5000
        i = i + 5000
    d = data[i:s]
    s3.send(d)


# when the client connecting to the server for the first time with an ID number
# the client pulls from the server all of its directory's content
# param: socket s3, path path
def pull_from_server(s3, path):
    number_of_files = int.from_bytes(s3.recv(4), 'big') # gets the number of files
    s3.send(b'ok')
    while number_of_files > 0:
        s_name = int.from_bytes(s3.recv(4), 'big')
        s3.send(b'ok')
        name = s3.recv(s_name).decode('utf-8')  #gets the name of the file
        s3.send(b'ok')
        # changing behaviours between linux and windows
        if os.name == "nt":
            name = name.replace("/", "\\")
        if os.name == "posix":
            name = name.replace("\\", "/")
        new_path = os.path.join(path, name)
        is_dir = s3.recv(2)
        s3.send(b'ok')
        # if the file is a directory the performing a recursive call with the directory
        if is_dir == b'1':
            os.mkdir(new_path)
            pull_from_server(s3, new_path)
        else:   # gets the file from the server
            size = int.from_bytes(s3.recv(4), 'big')
            s3.send(b'ok')
            data = b''
            while size > 5000:
                d = s3.recv(5000)
                s3.send(b'ok')
                size = size - 5000
                data = data + d
            data = data + s3.recv(size)
            write_file(new_path, data)
        number_of_files = number_of_files - 1

# param: socket s5, path path5
# function sending the server the name of the file / directory
def send_name(s5, path5):
    size = len((sys.argv[3]))
    name = path5[size + 1:]
    s5.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
    s5.recv(2)
    s5.send(name.encode('UTF-8'))
    s5.recv(2)

# function get a path of a file / directory and deletes it
def delete(name):
    global path
    new_path3 = os.path.join(path, name)
    if not os.path.isdir(os.path.join(path, name)) and not os.path.isfile(os.path.join(path, name)):
        return
    # if its a directory then performing a recursive call
    if os.path.isdir(new_path3):
        delete_recurse(os.path.join(path, name))
        os.rmdir(os.path.join(path, name))
    else:
        os.remove(new_path3)


def delete_recurse(path1):
    for file in os.listdir(path1):
        if not os.path.isdir(os.path.join(path1, file)) and not os.path.isfile(os.path.join(path1, file)):
            return
        if os.path.isdir(os.path.join(path1, file)):
            delete_recurse(os.path.join(path1, file))
            os.rmdir(os.path.join(path1, file))
        else:
            os.remove(os.path.join(path1, file))

# param: string name
# the function creates a new file with the name in the argument
def create_file(name):
    global path
    if os.path.isfile(os.path.join(path, name)):
        return
    f = open(os.path.join(path, name), 'x')
    f.close()

# param: string name
# the function creates a new directory with the name in the argument
def create_dir(name):
    global path
    if os.path.isdir(os.path.join(path, name)):
        return
    os.mkdir(os.path.join(path, name))

# param: string old, string new
# the function renaming the old directory with new name
def rename(old, new):
    global path
    if os.path.isdir(os.path.join(path, new)) or os.path.isfile(os.path.join(path, new)):
        return
    os.rename(os.path.join(path, old), os.path.join(path, new))

# every time out the client asking for the server wether there are new changes
# made in his directory, if there are any then the client updating his local directory based on those changes.
# param: socket socket1
def time_out_over(socket1):
    global IN_TIMEOUT
    # sending the server the client's index and id number
    socket1.send(b'10')
    socket1.recv(2)
    socket1.send(id_number.encode('UTF-8'))
    socket1.recv(2)
    socket1.send(index.to_bytes(4, 'big'))
    action = socket1.recv(2000)  # gets from the server the new action
    socket1.send(b'ok')
    while action != b'0':
        if action == b'1':
            socket1.send(b'ok')
        else:
            # in these conditions the function gets the path which came with a midification
            # based on the operating system
            action = action.decode('UTF-8')
            if action == 'create dir':
                s_name = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                name = socket1.recv(s_name).decode('UTF-8')
                if os.name == "nt":
                    name = name.replace("/", "\\")
                if os.name == "posix":
                    name = name.replace("\\", "/")
                create_dir(name)
            if action == 'create file':
                s_name = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                name = socket1.recv(s_name).decode('UTF-8')
                if os.name == "nt":
                    name = name.replace("/", "\\")
                if os.name == "posix":
                    name = name.replace("\\", "/")
                create_file(name)
            if action == 'delete':
                s_name = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                name = socket1.recv(s_name).decode('UTF-8')
                if os.name == "nt":
                    name = name.replace("/", "\\")
                if os.name == "posix":
                    name = name.replace("\\", "/")
                delete(name)
            if action == 'rename':
                s_name = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                old = socket1.recv(s_name).decode('UTF-8')
                socket1.send(b'ok')
                s_name2 = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                new = socket1.recv(s_name2).decode('UTF-8')
                rename(old, new)
            if action == 'update file':
                global path
                s_name = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                name = socket1.recv(s_name).decode('UTF-8')
                socket1.send(b'ok')
                if os.name == "nt":
                    name = name.replace("/", "\\")
                if os.name == "posix":
                    name = name.replace("\\", "/")
                size = int.from_bytes(socket1.recv(4), 'big')
                socket1.send(b'ok')
                data = b''
                # performing the action
                while size > 5000:
                    d = socket1.recv(5000)
                    socket1.send(b'ok')
                    size = size - 5000
                    data = data + d
                data = data + socket1.recv(size)
                write_file(os.path.join(path, name), data)
        action = socket1.recv(2000)
        socket1.send(b'ok')

# the main
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))

# create the dir of this client
if not os.path.exists(path):
    os.mkdir(path)
# if the number of arguments is 6 then got an id number as an argument
if len(sys.argv) == 6:
    id_number = sys.argv[5]
    s.send(b'0')
    s.recv(2)
    byte_id_number = bytes(id_number, 'UTF-8')
    s.send(byte_id_number)  # sending the id number to the server
    s.recv(2)
    s.send(b'ok')
    index = s.recv(4)   # getting an index in order to be recognized by the server in the next communcations
    index = int.from_bytes(index, 'big')
    pull_from_server(s, path)   # pulling all the data from the remote server directory
# else its a first connction with the server, getting a new ID number from the server for future communications
else:
    s.send(b'1')
    s.recv(2)
    id_number = first_connection(s)
    send_dir(s, path, id_number)
    s.close()

event_handler = Event()
observer = Observer()
observer.schedule(event_handler, path, recursive=True)
observer.start()
try:
    while True:
        time.sleep(timeOver)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        time_out_over(s)  # on every timeout, the client gets all of the new changes that made in the server directory
        s.close()

finally:
    observer.stop()
    observer.join()
