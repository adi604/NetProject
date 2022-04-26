import socket
import string
import os
import random
import sys
import time

port = int(sys.argv[1])
dict = {}

# param: path file_name, bytes data
# function writes the data to the file
def write_file(file_name, data):
    file = open(file_name, "wb")
    file.write(data)
    file.close()

# the function pulls all of the client's directory conetent
# param: socket s3, path path.
def pull_from_client(s3, path):
    number_of_files = int.from_bytes(s3.recv(4), 'big')
    s3.send(b'ok')
    while number_of_files > 0:
        s_name = int.from_bytes(s3.recv(4), 'big')
        s3.send(b'ok')
        name = s3.recv(s_name).decode('UTF-8')
        s3.send(b'ok')
        if os.name == "nt":
            name = name.replace("/", "\\")
        if os.name == "posix":
            name = name.replace("\\", "/")
        new_path = os.path.join(path, name)
        is_dir = s3.recv(1)
        s3.send(b'ok')
        if is_dir == b'1':  # if the file is a directory then performing a recursive call
            os.mkdir(new_path)
            pull_from_client(s3, new_path)
        else:   # otherwise writing the file
            size = int.from_bytes(s3.recv(4), 'big')
            s3.send(b'ok')
            data = b''
            # getting all of the file's data
            while size > 5000:
                d = s3.recv(5000)
                s3.send(b'ok')
                size = size - 5000
                data = data + d
            data = data + s3.recv(size)
            s3.send(b'ok')
            # writing the data to the file
            write_file(new_path, data)
        number_of_files = number_of_files - 1


# param: socket s2, path path1, string id
# function sending the directory (= path1) and all of it's content to the client
def send_dir(s2, path1, id):
    num_of_files = len(os.listdir(path1))
    s2.send(num_of_files.to_bytes(4, 'big'))    # sending the number of the files in the directory
    s2.recv(2)
    for file in os.listdir(path1):
        if not file.isascii():
            s2.send(b'-1')
        else:
            s2.send(len(file.encode('UTF-8')).to_bytes(4, 'big'))
            s2.recv(2)
            s2.send(file.encode('UTF-8'))
            s2.recv(2)
            if os.path.isdir(os.path.join(path1, file)): # if the file is a directory, then performing a recursive call
                s2.send(b'1')
                s2.recv(2)
                send_dir(s2, os.path.join(path1, file), id)
            else:   # else sending the file and it's data
                s2.send(b'0')
                s2.recv(2)
                size = (os.path.getsize(os.path.join(path1, file)))
                s2.send(size.to_bytes(4, 'big'))
                s2.recv(2)
                data = open((os.path.join(path1, file)), "rb").read()
                i = 0
                k = size
                while size > 5000:
                    d = data[i:i + 5000]
                    s2.send(d)
                    s2.recv(2)
                    size = size - 5000
                    i = i + 5000
                d = data[i:k]
                s2.send(d)


def update_new_file(s, path4, id, client_index):
    s_name = int.from_bytes(s.recv(4), 'big')
    s.send(b'ok')
    name = s.recv(s_name).decode('utf-8')
    s.send(b'ok')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    size = int.from_bytes(s.recv(4), 'big')
    s.send(b'ok')
    data1 = b''
    while size > 5000:
        d = s.recv(5000)
        s.send(b'ok')
        size = size - 5000
        data1 = data1 + d
    data1 = data1 + s.recv(size)
    write_file(os.path.join(path4, name), data1)
    update_dict(id, client_index, os.path.join(path4, name), '0', 'update file')

# param: socket s, path path2, int client_index
# function crating a new directory in path2
def create_new_dir(s, path2, id, client_index):
    s_name = int.from_bytes(s.recv(4), 'big')   # getting the name of the new directory
    s.send(b'ok')
    name = s.recv(s_name).decode('UTF-8')
    s.send(b'ok')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    p = os.path.join(path2, name)
    if os.path.isdir(p):
        return
    os.mkdir(p)
    update_dict(id, client_index, os.path.join(path2, name), '0', 'create dir')  # updating the dictionary actions

# param: socket s, path path2, string id, int client_index
# function creating a new file in path2
def create_new_file(s, path2, id, client_index):
    s_name = int.from_bytes(s.recv(4), 'big')
    s.send(b'ok')
    name = s.recv(s_name).decode('UTF-8')
    s.send(b'ok')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    if os.path.isfile(os.path.join(path2, name)):   # if there is already a file with the same name in this path
        return
    f = open(os.path.join(path2, name), 'x')    # creating the file
    f.close()
    update_dict(id, client_index, os.path.join(path2, name), '0', 'create file')    # updating the dictionary actions

# param: socket s, path path1, string id, int client_index
# function gets from the server a name and delete the file / directory and it's content
def delete(s, path1, id, client_index, is_update=0):
    s_name = int.from_bytes(s.recv(4), 'big')
    s.send(b'ok')
    name = s.recv(s_name).decode('UTF-8')
    s.send(b'ok')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    new_path3 = os.path.join(path1, name)
    if not os.path.isdir(new_path3) and not os.path.isfile(new_path3):
        return
    if os.path.isdir(new_path3):    # if the file is a direcotry then performs a recursive call
        delete_recurse(os.path.join(path1, name))
        os.rmdir(os.path.join(path1, name))
    else:   # else' removing the file
        os.remove(new_path3)
    if is_update == 0:      # updating the dictionary
        update_dict(id, client_index, new_path3, '0', 'delete')

# function performs a recursive deletion of directory in the path given
def delete_recurse(path):
    for file in os.listdir(path):
        if not os.path.isdir(os.path.join(path, file)) and not os.path.isfile(os.path.join(path, file)):
            return
        if os.path.isdir(os.path.join(path, file)):
            delete_recurse(os.path.join(path, file))
            os.rmdir(os.path.join(path, file))
        else:
            os.remove(os.path.join(path, file))

# function generate a random ID number with 128 chars for the client's first connection
def random_id(s):
    global next_index
    id = ''.join(
        random.choice(string.ascii_lowercase + string.ascii_letters + string.ascii_uppercase) for i in range(128))
    s.send(id.encode('UTF-8'))
    s.recv(2)
    s.send(next_index.to_bytes(4, 'big'))
    next_index = next_index + 1
    return id, next_index - 1

# param: Path path1, string id1, socket s5, int client_index
# function get a name from the client and renaming the file
def rename(path1, id1, s5, client_index):
    s_name = int.from_bytes(client_socket.recv(4), 'big')   # gets the old name from the server
    client_socket.send(b'ok')
    name = client_socket.recv(s_name).decode('UTF-8')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    old_path = os.path.join(path1, os.path.join(id1, name))
    s5.send(b'ok')
    s_name2 = int.from_bytes(client_socket.recv(4), 'big')
    client_socket.send(b'ok')
    name2 = client_socket.recv(s_name2).decode('UTF-8')  #gets the new name from the server
    if os.name == "posix":
        name2 = name2.replace("\\", "/")
    if os.name == "nt":
        name2 = name2.replace("/", "\\")
    dest_path = os.path.join(path1, os.path.join(id1, name2))
    s5.send(b'ok')
    if os.path.isdir(dest_path) or os.path.isfile(dest_path):
        return
    if os.path.isdir(old_path) or os.path.isfile(old_path):
        os.rename(old_path, dest_path)  # renaming the file
        update_dict(id1, client_index, old_path, dest_path, 'rename')   #updating the dictionary actions

# param: string id, int client_index, path path_old, path path_new, string action
# the function adds the action to all of the clients with the same id number
# but other index.
def update_dict(id, client_index, path_old, path_new, action):
    for i in dict.keys():
        if i[0] == id and i[1] != client_index:
            if action != 'rename':
                dict[i].append((action, path_old))
            else:
                dict[i].append((action, path_old, path_new))

# param: dict actions, string id, int index
# function returns the list of new updates that the client with the id and index
# given has to perform in time put
def get_new_updates(actions, id, index):
    for identity in actions.keys():
        if identity[0] == id and identity[1] == index:
            return actions[identity]

# param: socket client_socket, dictionary dict, string id, int index
# when the client in a timeout, then the server updates the client with all of the
# action he needs to do.
def update_client(client_socket, dict, id, index):
    actions = get_new_updates(dict, id, index)
    for action in actions:
        if action[0] == 'delete':
            client_socket.send(b'delete')
            client_socket.recv(2)
            send_name(client_socket, action[1], id)

# param: socket s5, path path5, string id
# function sends the name of the name of the file / directory to the client
def send_name(s5, path5, id):
    size = len(os.path.join(os.getcwd(), id))
    name = path5[size + 1:]
    s5.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
    s5.recv(2)
    s5.send(name.encode('UTF-8'))
    s5.recv(2)

# param: socket s, path path4
# function return true if the file in the in the client is identical to the server and false otherwise
def already_update(s, path4):
    s_name = int.from_bytes(s.recv(4), 'big')   #getting the name of the file from the client
    s.send(b'ok')
    name = s.recv(s_name).decode('utf-8')
    s.send(b'ok')
    if os.name == "posix":
        name = name.replace("\\", "/")
    if os.name == "nt":
        name = name.replace("/", "\\")
    size = int.from_bytes(s.recv(4), 'big')     # getting the size of the file
    s.send(b'ok')
    data1 = b''
    # getting all of the file's data from the client
    while size > 5000:
        d = s.recv(5000)
        s.send(b'ok')
        size = size - 5000
        data1 = data1 + d
    data1 = data1 + s.recv(size)
    if not os.path.exists(os.path.join(path4, name)):
        return True
    # reading the data in the server directory
    server_data = open(os.path.join(path4, name), "rb").read()
    # if equals then the file is identical in both client and server
    if server_data == data1:
        return True
    else:
        return False

# param: string id_c, index_c, socket s
# on every time out the client asking for the server wether there are new changes
# made in his directory, if there are any then the server sending those changes ti the client
def time_out_over(id_c, index_c, s):
    global path
    global dict
    actions = dict[id_c, index_c]   # every value in the dictionary is a list of action
    j = 0
    for i in actions:
        act = i[0]
        if act != "rename" and act != "update file":
            s.send(act.encode('UTF-8'))
            s.recv(2)
            size = len(os.path.join(os.getcwd(), id))
            name = i[1][size + 1:]
            s.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
            s.recv(2)
            s.send(name.encode('UTF-8'))
        if act == 'rename':     # updating the client to rename the file
            s.send(act.encode('UTF-8'))
            s.recv(2)
            size = len(os.path.join(os.getcwd(), id))
            old = i[1][size + 1:]       # getting the old name file and sends it
            s.send(len(old.encode('UTF-8')).to_bytes(4, 'big'))
            s.recv(2)
            s.send(old.encode('UTF-8'))
            s.recv(2)
            new = i[2][size + 1:]       # getting the new name of the file sends it
            s.send(len(new.encode('UTF-8')).to_bytes(4, 'big'))
            s.recv(2)
            s.send(new.encode('UTF-8'))
        if act == 'update file':
            if not os.path.exists(i[1]):
                s.send(act.encode('UTF-8'))     # sending the action to the client
                s.recv(2)
                size = len(os.path.join(os.getcwd(), id))
                name = actions[j + 1][2][size + 1:]
                s.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
                s.recv(2)
                s.send(name.encode('UTF-8'))
                s.recv(2)
                size = (os.path.getsize(actions[j + 1][2]))
                s.send(size.to_bytes(4, 'big'))
                s.recv(2)
                data = open((actions[j + 1][2]), "rb").read()
                i = 0
                k = size
                while size > 5000:      # sending all of the data to the client
                    d = data[i:i + 5000]
                    s.send(d)
                    s.recv(2)
                    size = size - 5000
                    i = i + 5000
                d = data[i:k]
                s.send(d)
                actions.append(('delete', actions[j + 1][1]))       #removing the action
            else:
                s.send(act.encode('UTF-8'))
                s.recv(2)
                size = len(os.path.join(os.getcwd(), id))
                name = i[1][size + 1:]
                s.send(len(name.encode('UTF-8')).to_bytes(4, 'big'))
                s.recv(2)
                s.send(name.encode('UTF-8'))
                s.recv(2)
                size = (os.path.getsize(i[1]))
                s.send(size.to_bytes(4, 'big'))
                s.recv(2)
                data = open((i[1]), "rb").read()
                i = 0
                k = size
                while size > 5000:
                    d = data[i:i + 5000]
                    s.send(d)
                    s.recv(2)
                    size = size - 5000
                    i = i + 5000
                d = data[i:k]
                s.send(d)
        j = j + 1
        time.sleep(2)
    s.send(b'0')
    s.recv(2)
    dict[id_c, index_c] = []

# main
next_index = 1
client_index = 0
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', port))
server.listen(5)
path = os.getcwd()
while True:
    client_socket, client_address = server.accept()
    data = client_socket.recv(2)
    client_socket.send(b'ok')
    if data == b'0':    # first connection with the client but the client already has an id number
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_socket.recv(2)
        client_index = next_index
        client_socket.send(client_index.to_bytes(4, 'big'))     # sendig the client an index to be recognized with
        next_index = next_index + 1
        dict[(id, client_index)] = []
        send_dir(client_socket, os.path.join(path, id), id)     # sending the client all of the directory
    if data == b'1':    # in this case, the cient doesnt have an id number
        id, client_index = random_id(client_socket)     # generating an id number and an index
        print(id)
        os.mkdir(os.path.join(path, id))
        pull_from_client(client_socket, os.path.join(path, id))
        dict[(id, client_index)] = []       # adding a new list to the client with the id number and index
    if data == b'4':        # creating a new directory
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        client_socket.send(b'ok')
        create_new_dir(client_socket, os.path.join(path, id), id, client_index)
    if data == b'5':        # deleting a directory
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        client_socket.send(b'ok')
        delete(client_socket, os.path.join(path, id), id, client_index)
    if data == b'7':        # reanaming a directory
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        client_socket.send(b'ok')
        rename(path, id, client_socket, client_index)
    if data == b'8':        # creating file
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        client_socket.send(b'ok')
        create_new_file(client_socket, os.path.join(path, id), id, client_index)
    if data == b'9':         # modify file
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        client_socket.send(b'ok')
        if not already_update(client_socket, os.path.join(path, id)):       #modifieng the file if it didnt modify already
            client_socket.send(b'0')
            delete(client_socket, os.path.join(path, id), '0', client_index, 1)
            update_new_file(client_socket, os.path.join(path, id), id, client_index)
        else:
            client_socket.send(b'1')
    if data == b'10':           # time out updates
        id = client_socket.recv(128).decode('UTF-8')
        client_socket.send(b'ok')
        client_index = int.from_bytes(client_socket.recv(4), 'big')
        time_out_over(id, client_index, client_socket)
    client_socket.close()
