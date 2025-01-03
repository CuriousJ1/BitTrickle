import socket
import sys
import os
from datetime import datetime, timedelta
import time
import threading

# Dictionary to store active peers and their last heartbeat time
active_peers = {}                                                                   # Format: {"username": last_heartbeat}

# Dictionary to store published files for each user
published_files = {}                                                                # Format: {filename: {“username”: datetime.datetime(YYYY, MM, DD, MM, SS, ..}

# Set the allowed heartbeat interval
HEARTBEAT_INTERVAL = timedelta(seconds=3)  

# Function to handle incoming requests from clients (UDP)
def handle_request(server_socket):

    # Receive request data and client address
    request, client_address = server_socket.recvfrom(1024)
    message = request.decode()

    # User authenticaion function
    if message.startswith("AUTH "):
        handle_authentication(server_socket, message, client_address)

    # Heartbeat function
    elif message.startswith("HEARTBEAT "):
        handle_heartbeat(client_address, message)

    # Active peers function
    elif message.startswith("ACTIVE_PEERS"):
        send_active_peers_list(server_socket, message, client_address)
    
    # Publish files function
    elif message.startswith("PUBLISH"):
        handle_published_files(server_socket, message, client_address)

    # Unpublish files function
    elif message.startswith("UNPUBLISH"):  
        handle_unpublish_file(server_socket, message, client_address)

    # list of published files function
    elif message.startswith("LIST_FILES"):  
        handle_list_published_files(server_socket, message, client_address)

    # Search for files published by active users
    elif message.startswith("SEARCH_FILES"):  
        handle_search_files(server_socket, message, client_address)
    
    # Query and Download file in TCP
    elif message.startswith("QUERY_FILE"):
       handle_query_file(server_socket, message, client_address)

    # If any weird values occur in the handle request portion
    else:
        print(f"Received unrecognized message from {client_address}: {message}")


# Function to handle authentication requests - Helper function for authenticate user funcyoon.
def handle_authentication(server_socket, message, client_address):

    # extract username and password
    _, username, password = message.split(" ", 2)
    
    print(f"Received AUTH request from {username}")

    # Authenticate the user
    auth_response = authenticate_user(username, password)

    # Send the appropriate response to the client
    if auth_response == "AUTH_SUCCESS":

        # Add the user to the active peers list if authentication is successful
        active_peers[username] = client_address
        server_socket.sendto("AUTH_SUCCESS".encode(), client_address)
        print(f"Sent AUTH_SUCCESS to {username}")


        # If user is already active
    elif auth_response == "AUTH_ALREADY_ACTIVE":
        server_socket.sendto("AUTH_ALREADY_ACTIVE".encode(), client_address)
        print(f"Sent AUTH_ALREADY_ACTIVE to {username}")

    else:
        server_socket.sendto("AUTH_FAILED".encode(), client_address)
        print(f"Sent AUTH_FAILED to {username}")


# Function to authenticate user from credentials file and check if they have already logged in
def authenticate_user(username, password):

    # Set the default credentials path which is in the working directory                   
    credentials_file = os.getenv("CREDENTIALS_PATH", "./credentials.txt")

    # Check if the user is already active
    if username in active_peers:
        print(f"Authentication failed: {username} is already logged in.")
        return "AUTH_ALREADY_ACTIVE"

    # Validate credentials from the credentials file
    try:
        with open(credentials_file, "r") as file:
            for line in file:
                stored_username, stored_password = line.strip().split()
                if username == stored_username and password == stored_password:
                    return "AUTH_SUCCESS"
                
    except FileNotFoundError:
        print("Credentials file not found.")

    except Exception as e:
        print(f"Error reading credentials file: {e}")
    
    return "AUTH_FAILED"


# Function to send the list of active peers to the client
def send_active_peers_list(server_socket, message, client_address):
    try:
        # Get the username out of the message.
        key, username = message.split(" ", 1)
    
        # Extract the usernames of active peers
        active_usernames = list(active_peers.keys())

        # Format the list as a comma-separated string with active peers
        active_list_message = "ACTIVE_PEERS " + ", ".join(active_usernames)
    
        # Send the message back to the client
        server_socket.sendto(active_list_message.encode(), client_address)
    
        print(f"Sent OK to {username}")
    
    except Exception as e:
        # Handle any error that occurs
        print(f"Sent Error to {username}")
        message = "ACTIVE_PEERS_FAIL"

         # Send the message back to the client
        server_socket.sendto(active_list_message.encode(), client_address)


# Function to publish a file
def handle_published_files(server_socket, message, client_address):
    try:
        # Extract username, filename and TCP port from the message
        _, username, filename, tcp_port = message.split(" ")

        # Check if the file is already published
        if filename in published_files:

            # Check if this specific peer has already published the file
            if any(peer[0] == username for peer in published_files[filename]):                                                 
                response = "PUB_SUCCESS"
            
            else:
                # Add the peer's information to the list for this file
                published_files[filename].append((username, client_address[0], tcp_port))
                response = "PUB_SUCCESS"

        else:
            # Create a new entry for the file with the current peer as the first entry
            published_files[filename] = [(username, client_address[0], tcp_port)]
            response = "PUB_SUCCESS"

        print(f"Sent OK to {username}")

    except Exception as e:
        print(f"Sent Error to {username}: {e}")
        response = "PUB_FAIL"

    # Send response to the client
    server_socket.sendto(response.encode(), client_address)


# Function to unpublish a file
def handle_unpublish_file(server_socket, message, client_address):
    try:
        # Extract username and filename from the message
        _, username, filename, tcp_port = message.split(" ")

        # Check if the filename exists in published_files
        if filename in published_files:

            # Filter out only the entries where both username and client address match
            initial_length = len(published_files[filename])
            
            published_files[filename] = [
                peer for peer in published_files[filename]
                if not (peer[0] == username and peer[1] == client_address[0] and peer[2] == tcp_port)
            ]

            # If an entry was removed (meaning unpublish was successful)
            if len(published_files[filename]) < initial_length:
                
                # If the list becomes empty, remove the filename from the dictionary
                if not published_files[filename]:
                    del published_files[filename]
                
                response = "UNPUB_SUCCESS"
                print(f"Sent OK to {username} for unpublishing {filename}")
            
            else:
                response = "UNPUB_FAIL"
                print(f"Sent Error to {username}: not authorized to unpublish {filename}.")
        
        else:
            response = "UNPUB_FAIL"
            print(f"Sent Error to {username}: file not found or not published.")
    

    except Exception as e:
        print(f"Sent Error to {username}: {e}")
        response = "UNPUB_FAIL"

    # Send response back to the client
    server_socket.sendto(response.encode(), client_address)


# Function to handle requests for listing published files
def handle_list_published_files(server_socket, message, client_address):
    try:
        # Extract key and username
        _, username = message.split(" ", 1)

        # Gather all files published by the requesting user
        user_files = [
            filename for filename, peers in published_files.items()
            if any(peer[0] == username for peer in peers)  # Check if username is in the list of peers
        ]

        if user_files:
            # Join the list of published files into a comma-separated string
            files_list = ", ".join(user_files)
            response = f"PUBLISHED_FILES {files_list}"
            print(f"Sent OK to {username}")

        else:
            # If no files are published by the user
            response = "FAIL_PUBLISHED_FILES"
            print(f"Sent Error to {username}: no published files found.")

    except Exception as e:
        print(f"Sent Error to {username}: {e}")
        response = "FAIL_PUBLISHED_FILES"

    # Send response to the client
    server_socket.sendto(response.encode(), client_address)


#Search for files published by active users, using parts of a string 
def handle_search_files(server_socket, message, client_address):
    try:
        # extract substring and username
        _, substring, username = message.split(" ", 2)

        # Gather files published by active peers excluding the requesting user
        matching_files = []

        # Loop through published files to find matches
        for filename, peers in published_files.items():

            # Check if the file matches the substring i.e. "."
            if substring in filename:

                # Exclude files if the requesting user has published them
                if any(peer[0] == username for peer in peers):
                    continue  # Skip this file if the requester has published it

                # Check if there is any active peer (other than the requester) who published the file
                if any(peer[0] in active_peers for peer in peers):
                    matching_files.append(filename)

        # If search criteria finds relevant files
        if matching_files:
            files_list = ", ".join(matching_files)
            response = f"FOUND_FILES {files_list}"
            print(f"Sent OK to {username} with matching files: {files_list}")

        else:
            response = "FAIL_FOUND_FILES"
            print(f"Sent OK to {username}: no matching files found.")

    except Exception as e:
        print(f"Sent Error to {username}: {e}")  
        response = "FAIL_FOUND_FILES"

    # Send response to the client
    server_socket.sendto(response.encode(), client_address)


# Function to handle file query requests
def handle_query_file(server_socket, message, client_address):
    try:
        # extract file name and username from message
        _, filename, username = message.split(" ", 2)

        # Check if the file is published and find an active peer
        if filename in published_files:
            for peer in published_files[filename]:

                # Check if the peer is active
                if peer[0] in active_peers:     
                    # Sends Peer's IP and port number to client.                           
                    peer_ip, peer_port = peer[1], peer[2]  
                    response = f"QUERY_SUCCESS {peer_ip} {peer_port}"
                    print(f"Sent OK to {username}")
                    break

            else:
                response = "QUERY_FAIL"  
                print(f"Sent Error to {username}, no active peer for given file")  
                
        else:
            response = "QUERY_FAIL"  
            print(f"Sent Error to {username}, file not found")  

    except Exception as e:
        print(f"Sent Error to {username}")
        response = "QUERY_FAIL"

    server_socket.sendto(response.encode(), client_address)


# Background function to check for inactive peers 
def monitor_peers():
    while True:
        current_time = datetime.now()

        # Hearbeat interval set at 3 seconds
        inactive_peers = [username for username, last_heartbeat in active_peers.items()
                          if current_time - last_heartbeat > HEARTBEAT_INTERVAL]

        # Remove inactive peers and log them
        for username in inactive_peers:
            print(f"{current_time}: {username} is inactive (last heartbeat at {active_peers[username]})")
            del active_peers[username]

        # Wait before checking again
        time.sleep(HEARTBEAT_INTERVAL.total_seconds() / 2)  # Check twice within the interval


# Function to handle heartbeat messages
def handle_heartbeat(client_address, message):
    _, username = message.split(" ", 1)
    current_time = datetime.now()
    
    # Update peer's last heartbeat time
    active_peers[username] = current_time  
    
    # print(active_peers)
    # print(published_files)

    print(f"{current_time}: ({client_address}) Received HEARTBEAT from {username}")


# Function to start the UDP server
def start_server(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(("", port))

        # Debug statement for UDP server
        # print(f"Ping Server running on port {port}")

        # Start monitoring peers in a separate thread *********
        monitor_thread = threading.Thread(target=monitor_peers, daemon=True)
        monitor_thread.start()

        # Run server loop to handle requests continuously
        while True:
            handle_request(server_socket)


# Main function to get the port from command line arguments and start the server
def main():
    # User input for port number
    if len(sys.argv) != 2:
        print("Usage: PingServer.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    # start server function
    start_server(port)

# Run the main function
if __name__ == "__main__":
    main()