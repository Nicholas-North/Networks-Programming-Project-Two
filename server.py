import socket
import threading
import signal
import sys
import pickle
from os.path import exists
import datetime
import copy

# Define the max number of connections
MAX_CONNECTIONS = 5


class Server:
    def __init__(self, host, port) -> None:
        """Initialize the server."""
        self.host = host
        self.port = port
        self.client_ids = 0
        self.connected_clients = {}
        self.groups = {"default": []}
        self.boards = {"default": {}}
        self.lock = threading.Lock()

    def server_shutdown(self, signum, frame):
        """Shutdown server and save data for next startup."""
        print("\nCtrl+C pressed. Starting shutdown...")
        # Shut down the process.
        print("Done! See you later.")
        sys.exit(0)

    def server_startup(self):
        """Startup server and restore data from previous shutdown."""
        # Get instance of a socket for the server
        self.server_socket = socket.socket()
        # Bind host address and port
        self.server_socket.bind((self.host, self.port))
        # Set max amount of users to MAX_CONNECTIONS
        self.server_socket.listen(MAX_CONNECTIONS)

        # Listen for incoming connections
        print("Listening for connections on %s:%s..." % (self.host, self.port))
        self.server_socket.listen()
        while True:
            # Send each client to open_connections
            client_socket, client_address = self.server_socket.accept()
            threading.Thread(
                target=self.open_connection,
                args=(client_socket, client_address),
                daemon=True,
            ).start()

    def open_connection(self, client_socket, client_address):
        """Open a socket connection to a given client. Active on separate thread from main server execution."""
        # Receive the client username and group
        client_info = client_socket.recv(1024).decode()
        client_name = client_info.split(" ")[0]
        client_group = client_info.split(" ")[1]
        client_id = self.client_ids
        
        
        # Announce that a client has been connected.
        print("A client with ID #%d has connected, waiting for queries." % (client_id))

        # Manage client, group, and board data
        self.add_clients_groups(client_id, client_name, client_group, client_socket)

        # Broadcast to all clients that a new client has joined
        self.broadcast_client_join(client_id, client_name)

        # List up to 5 groups when a user connects
        example_groups = list(self.groups)[0:5]
        if len(example_groups) > 0:
            example_groups_message = " Current server groups: " + ", ".join(example_groups)
            if len(example_groups) > 5:
                example_groups_message += "..."

        # Send client ID to client to confirm connection + exmaple groups
        client_socket.send(("id " + str(client_id) + example_groups_message).encode())

        # Handle client requests
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            command = data.split(" ")[0]
            params = data.split(" ")[1:]
            match command:
                case "help":
                    help_msg = (
                        "A %connect command followed by the address and port number of a running bulletin board server to connect to.\n"
                        "A %join command to join the single message board.\n"
                        "A %post command followed by the message subject and the message content or main body to post a message to the board.\n"
                        "A %users command to retrieve a list of users in the same group.\n"
                        "A %leave command to leave the group.\n"
                        "A %message command followed by message ID to retrieve the content of the message.\n"
                        "An %exit command to disconnect from the server and exit the client program.\n"
                        "A %groups command to retrieve a list of all groups that can be joined.\n"
                        "A %groupjoin command followed by the group id/name to join a specific group.\n"
                        "A %grouppost command followed by the group id/name, the message subject, and the message content or main body to post a message to a message board owned by a specific group.\n"
                        "A %groupusers command followed by the group id/name to retrieve a list of users in the given group.\n"
                        "A %groupleave command followed by the group id/name to leave a specific group.\n"
                        "A %groupmessage command followed by the group id/name and message ID to retrieve the content of the message posted earlier on a message board owned by a specific group."
                    )
                    client_socket.send(help_msg.encode())
                case "join":
                    self.handle_join(client_id, "default")
                case "post":
                    if len(params) < 2:
                        client_socket.send("Error: Missing subject or message.".encode())
                        break
                    self.handle_post(client_id, "default", *params)
                case "users":
                    group_users = ", ".join(self.groups["default"])
                    client_socket.send(("Users in 'default': " + group_users).encode())
                case "leave":
                    self.handle_leave(client_id, "default")
                case "message":
                    if len(params) < 1:
                        client_socket.send("Error: Missing message ID.".encode())
                        break
                    self.handle_message(client_id, "default", *params)
                case "exit":
                    # Remove the current user from the server.
                    client_socket.send("You have been disconnected from the server.".encode())
                    print("A client with ID #%d has disconnected from the server." % (client_id))
                    # Close the client socket
                    self.connected_clients[client_id]["client_socket"].close()
                    # Remove the entry the current client in the connected clients list
                    self.connected_clients.pop(client_id)
                    # Return 0. This kills the thread for the current client request.
                    return 0
                case "groups":
                    response = "Available groups: "
                    for group in self.groups.keys():
                        response += group + ", "
                    client_socket.send(response[:-2].encode())
                case "groupjoin":
                    if len(params) != 1:
                        client_socket.send("Invalid %groupsjoin command. Please supply a group name to join.".encode())
                        break
                    else:
                        self.handle_join(client_id, params[0])
                case "grouppost":
                    if len(params) < 3:
                        client_socket.send("Error: Missing group, subject, or message.".encode())
                        break
                    self.handle_post(client_id, *params)
                case "groupusers":
                    if len(params) < 1 or params[0] not in self.groups:
                        client_socket.send("Error: Invalid group name".encode())
                        break
                    # Ensure client is part of group
                    if client_name not in self.groups[params[0]]:
                        client_socket.send(f"Error: Client not member of group '{params[0]}'.".encode())
                        break
                    group_users = ", ".join(self.groups[params[0]])
                    client_socket.send((f"Users in '{params[0]}': " + group_users).encode())
                case "groupleave":
                    if len(params) < 1 or params[0] not in self.groups:
                        client_socket.send("Error: Invalid group name.".encode())
                        break
                    self.handle_leave(client_id, params[0])
                case "groupmessage":
                    if len(params) < 2:
                        client_socket.send("Error: Missing group ID or message ID.".encode())
                        break
                    self.handle_message(client_id, *params)
                case _:
                    client_socket.send("Invalid command.".encode())

    def add_clients_groups(self, client_id, client_name, client_group, client_socket):
        """Add the client to the list of users in a group.
        All users are added to the group "default" unless a group name is specified.
        The list of users in a group is saved on shutdown and recalled on boot as
        a user should stay in a group unless they
            1. connect with another group name instead or
            2. use the %groupleave command.
        Users can be in multiple groups.
        """
        with self.lock:
            # Increment client_ids for the next client
            self.client_ids += 1

            # Add client to the connected clients list
            self.connected_clients[client_id] = {
                "name": client_name,
                "group": client_group,
                "client_socket": client_socket,
            }

            # GROUPS
            # If the user supplied a group on connect that doesn't exist, create the group.
            if client_group not in self.groups.keys():
                self.groups[client_group] = [client_name]
            # If user supplied group on connect that does exist, add them to the group.
            elif client_name not in self.groups[client_group]:
                self.groups[client_group].append(client_name)

            # BOARDS
            # Create a board for default if it doesn't exist yet
            if "default" not in self.boards.keys():
                self.boards["default"] = {}
            # Add blank boards for all groups that don't have a board yet
            for group in self.groups.keys():
                if group not in self.boards.keys():
                    self.boards[group] = {}

    def broadcast_client_join(self, client_id, client_name):
        """Broadcast to all clients that a new client has joined."""
        with self.lock:
            encodedMessage = str(
                "%s has joined the server (client ID #%d). "
                % (client_name, client_id)
            ).encode()
            for cid, client in self.connected_clients.items():
                # Exclude the current connected client
                if cid != client_id:
                    # Print to all other clients on their socket that *this* client has joined with its information
                    client["client_socket"].send(encodedMessage)
    
    def handle_join(self, client_id, group):
        with self.lock:
            client_name = self.connected_clients[client_id]["name"]
            client_socket = self.connected_clients[client_id]["client_socket"]
            if group not in self.groups.keys():
                # Add new group and board.
                self.groups[group] = [client_name]
                self.boards[group] = {}
                client_socket.send(f"Added to new group '{group}'.".encode())
                return
            else:
                if client_name in self.groups[group]:
                    client_socket.send(f"Already part of group '{group}'.".encode())
                else:
                    self.groups[group].append(client_name)
                    # Broadcast new message to all clients in the group
                    for cid, info in self.connected_clients.items():
                        if info["name"] is not client_name and info["name"] in self.groups[group]:
                            info["client_socket"].send(f"New member {client_name} has joined group '{group}'.".encode())
                    return_message = f"Added to group '{group}'.\nCurrent Members: " + ", ".join(self.groups[group])
                    client_socket.send(return_message.encode())

    def handle_post(self, client_id, group, subject, *message):
        """Post a message to a group's board with a given subject and message. Notifies all group members of post."""
        with self.lock:
            # Ensure client is part of group
            sender_name = self.connected_clients[client_id]["name"]
            if not sender_name in self.groups[group]:
                self.connected_clients[client_id]["client_socket"].send("Error: Client not member of group.".encode())
                return
            
            print( self.groups[group])
            message_id = len(self.boards[group])
            self.boards[group][message_id] = {
                "sender": sender_name,
                "date": datetime.datetime.now().date(),
                "subject": subject,
                "message": " ".join(message),
                "users_at_time_of_posting": copy.deepcopy(self.groups[group]),
            }
            # Broadcast new message to all clients in the group
            for cid, info in self.connected_clients.items():
                if info["name"] in self.groups[group]:
                    info["client_socket"].send(f"New message posted in {group} by {sender_name} with ID#{message_id}.".encode())

    def handle_message(self, client_id, group, message_id):
        """View a message from a group's board with a given message ID."""
        client_socket = self.connected_clients[client_id]["client_socket"]

        # Ensure client is part of group
        sender_name = self.connected_clients[client_id]["name"]
        if not sender_name in self.groups[group]:
            client_socket.send("Error: Client not member of group.".encode())
            return
        
        # Ensure message exists
        try:
            message = self.boards[group][int(message_id)]
            if message is not None:
                if sender_name not in self.boards[group][int(message_id)]['users_at_time_of_posting']:
                    # Check if they're in the list of members two posts from now.
                    if (sender_name in self.boards[group][int(message_id)+1]['users_at_time_of_posting'] or
                        sender_name in self.boards[group][int(message_id)+2]['users_at_time_of_posting']):
                        encodedMessage = f"{message['sender']} on {message['date']} ({message['subject']}): {message['message']}".encode()
                        client_socket.send(encodedMessage)
                    else:
                        client_socket.send("Error: You are trying to access a message from too far in the past from when you joined the current group. (Limit: 2)".encode())
                else:
                    encodedMessage = f"{message['sender']} on {message['date']} ({message['subject']}): {message['message']}".encode()
                    client_socket.send(encodedMessage)
            else:
                raise Exception
        except:
            client_socket.send("Error: Message ID does not exist.".encode())

    def handle_leave(self, client_id, group):
        """Removes a user from a given group. Notifies all group members that user has left."""
        with self.lock:
            client_socket = self.connected_clients[client_id]["client_socket"]
            
            # Ensure client is part of group
            sender_name = self.connected_clients[client_id]["name"]
            if not sender_name in self.groups[group]:
                client_socket.send(f"Error: Client not member of group '{group}'.".encode())
                return
            
            # Remove client from group
            self.groups[group].remove(sender_name)
            client_socket.send(f"You have left group '{group}'.".encode())

            # Broadcast leave message to all clients in the group
            for cid, info in self.connected_clients.items():
                if info["name"] in self.groups[group]:
                    info["client_socket"].send(f"User {sender_name} has left group '{group}'.".encode())


def main():
    host = input("Specify host IP (RETURN for localhost): ")
    port = input("Enter port (>=1024, default 1024): ")
    server = Server(
        host if host != "" else socket.gethostbyname(socket.gethostname()),
        int(port) if port != "" else 1024,
    )
    # Register the Ctrl+C signal handler
    signal.signal(signal.SIGINT, server.server_shutdown)
    # Start the server.
    server.server_startup()

    return 0


if __name__ == "__main__":
    main()
