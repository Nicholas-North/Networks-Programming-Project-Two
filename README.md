# Networks-Programming-Project-Two

Nick Bryant, Nick Krouse

# bulletin-board

Bulletin board group programming project for CS4065 Computer Networks.

# Compilation and Running

Both the client and server are built using Python 3.10.
Required packages: `socket threading signal sys pickle os datetime copy`

To start the server, execute `python server.py`. You will be asked for the host IP and the port which the server will be run on. Following this, the groups and boards will be loaded and the server will listen for connections.

To start a new client, execute `python client.py`. You will be asked for a username as well as the group you wish to be part of. Following this, you will be able to execute commands as that user with reference to the specific group you are part of.

Instructions on how certain commands work can be found within the program by running `%help` in the client terminal.

# Commands

- %connect command followed by the address and port number of a running bulletin board server to connect to.
- %join command to join the single message board.
- %post command followed by the message subject and the message content or main body to post a message to the board.
- %users command to retrieve a list of users in the same group.
- %leave command to leave the group.
- %message command followed by message ID to retrieve the content of the message.
- %exit command to disconnect from the server and exit the client program.
- %groups command to retrieve a list of all groups that can be joined.
- %groupjoin command followed by the group id/name to join a specific group.
- %grouppost command followed by the group id/name, the message subject, and the message content or main body to post a message to a message board owned by a specific group.
- %groupusers command followed by the group id/name to retrieve a list of users in the given group.
- %groupleave command followed by the group id/name to leave a specific group.
- %groupmessage command followed by the group id/name and message ID to retrieve the content of the message posted earlier on a message board owned by a specific group.
