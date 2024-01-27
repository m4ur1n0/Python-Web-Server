import socket
import sys
import os
import select


# failure exit code key
# 1 = port number lower than 1024 or not an int

def receive(client_sock):
    recvd = b""
    while (True):
        # not worrying about if .htm is in the string until I know the above condition is even relevant
        chunk = client_sock.recv(1024)
        if (not chunk):
            break

        recvd += chunk

        if (b"\n\r\n\r" in recvd) or (b"\n\n" in recvd) or (b"\r\r" in recvd) or (b"\r\n"  in recvd):
            break


    # now recvd should be a full http request made to our server
    response = recvd.decode("utf-8")
    # debug --------
    # print("\n\n" + response + "\n\n")
    # debug -------- 
    return response

def get_header_from_path(path):
    # expects a file path relevant to this directory
    # returns a tuple with the header and the path to serve
    # now we have to make sure the file exists, and that its an html file
    return_path = ""

    # assign a code based on existence/servability of file
    if (not os.path.exists(path)):
        code = "404"
    else:
        if ((path[-5:].lower() != ".html") and (path[-4].lower() != ".htm")):
            code = "403"
        else:
            code = "200"

    
    code_dict = {"200": "OK", "403": "Forbidden", "404": "Not Found"}
    status_line = "HTTP/1.0 " + code + " " + code_dict.get(code)

    # just hard coding text/html as the content type right now for ease
    content_type = "Content-Type: text/html"

    # assign content lengths based on respective file sizes
    if (code == "403"):
        content_length = "Content-Length: " + str(os.path.getsize("403.html"))
        return_path = "403.html"

    if (code == "404"):
        content_length = "Content-Length: " + str(os.path.getsize("404.html"))
        return_path = "404.html"
    
    if (code == "200"):
        content_length = "Content-Length: " + str(os.path.getsize(path))
        return_path = path

    # now to build the header
    header = status_line + "\n" + content_type + "\n" + content_length + "\n\n"
    return (header, return_path)


    


# set port to the argument passed on the command line
port = sys.argv[1]
try:
    port = int(port)
except:
    print("port numbers are supposed to be numbers...", file=sys.stderr)
    exit(1)

if (port < 1024):
    print("Port # reserved", file=sys.stderr)
    exit(1)

accept_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# host the server on port port, "" means it doesn't care what ip tries to connect to it
accept_sock.bind(("", port))
# allowing for a connection backlog of 5 to minimize rejections
accept_sock.listen(5)

# the list that will house the active connections 
open_connections = [accept_sock]


while True:
    # read list holds the list of open connections which are ready to be read
    # but we must initialize it with accept_sock included to begin accepting
    read_list = open_connections


    readable, writable, exceptional = select.select(read_list, read_list, read_list)
    #STOLEN RIGHT HERE

    # debug -------
    # print(len(read_list))
    # debug -------


    for client_sock in readable:
        # if the readable socket is our accept_sock then it is readable
        # meaning it is ready to accept something 
        if client_sock == accept_sock:
            new_conn, new_ip = accept_sock.accept()
            read_list.append(new_conn)

        # if it isn't our accept socket then it's a socket looking to share some info
        else:
            response = receive(client_sock)
            # debug --------
            # print(response + "\n response \n")
            # debug --------

            # if we don't get a GET request, close the connection and move on
            if (response[0:4].lower() != "get "):
                
                # Only configured to handle get requests :( 
                client_sock.close()
                read_list.remove(client_sock)
                continue

            # assuming it WAS a get request, now we know how to find the file path
            # the file path is everything after the '/' between the first two
            # spaces in the first line of the get request 
            lines = response.split("\n")
            file_path = lines[0].split(" ")[1][1:]
            # debug --------
            # print(file_path)
            # debug --------

            # debug ------
            # print(file_path)
            # debug ------

            hnp = get_header_from_path(file_path)
            header = hnp[0]
            path = hnp[1]
            # now to push the header and the file back through the socket
            # print(header)
            client_sock.send(header.encode("utf-8"))
            with open(path, "r") as file:
                data = file.read(1024)  # read the file in chunks
                while data:
                    client_sock.send(data.encode("utf-8"))
                    data = file.read(1024)

            # now we've transmitted the file and can close the socket
            client_sock.close()
            read_list.remove(client_sock)

        