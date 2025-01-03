import socket
import time
import sys
import threading

# Function to get the server's address and port from the command line
def get_server_info():
    if len(sys.argv) != 3:
        print("Usage: PingClient.py <server_host> <server_port>")
        sys.exit(1)
    
    # example: localhost 51000
    return sys.argv[1], int(sys.argv[2])  

# Function to initialize the UDP socket
def create_socket():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # set a 5 second timeout
    client_socket.settimeout(5)                                                     

    return client_socket

# Function to take username and password input
def get_user_credentials():
    username = input("Enter your username: ")
    password = input("Enter your password: ")  

    return username, password

# Function to authenticate the user by sending credentials to the server
def authenticate_with_server(client_socket, server_host, server_port, username, password):
    credentials = f"AUTH {username} {password}"
    client_socket.sendto(credentials.encode(), (server_host, server_port))

    try:
        response, _ = client_socket.recvfrom(1024)
        response_message = response.decode()

        if response_message == "AUTH_SUCCESS":
            print("Authentication successful!")
            return True
        
        elif response_message == "AUTH_ALREADY_ACTIVE":
            print("This account is already logged in from another device.")
            return False
        
        elif response_message == "AUTH_FAILED":
            print("Invalid username or password.")
            return False
        
        else:
            print("Unknown response from server.")
            return False
    
    except socket.timeout:
        print("Authentication request timed out.")
        return False


# Get unique static TCP port for each username 
def get_tcp_port(username):
    base_port = 55000
    max_port_range = 5000  # Allows ports between 55000 and 60000

    # Ensure username is at least 2 characters long - potential limitation
    if len(username) < 2:
        raise ValueError("Username must have at least 2 characters.")

    # Get ASCII values of the last two characters
    last_two_letters = username[-2:]
    ascii_sum = sum(ord(char) for char in last_two_letters)

    # Map the ASCII sum to a port within the range (e.g., 55000–60000)
    tcp_port = base_port + (ascii_sum % max_port_range)

    return tcp_port

# Start a TCP server to handle file upload requests
def start_file_server(peer_tcp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", peer_tcp_port))
        tcp_socket.listen(5)

        # Debug statement
        # print(f"TCP File server started on port {peer_tcp_port}")

        while True:
            conn, addr = tcp_socket.accept()
            threading.Thread(target=send_file, args=(conn, addr)).start()


# Send requested file over TCP to downloading peer
def send_file(conn, addr):
    try:
        request = conn.recv(1024).decode()
        if request.startswith("DOWNLOAD "):
            filename = request.split(" ", 1)[1]
            
            # Open and send file in binary mode
            with open(filename, "rb") as file:
                while (chunk := file.read(1024)):
                    conn.sendall(chunk)
        conn.close()

    except Exception as e:
        print(f"Error sending file: {e}")


# Function to send ping requests to a server using UDP
def heart_beat_mechanism(username, client_socket, server_host, server_port):
    while True:
        message = f"HEARTBEAT {username}"
        client_socket.sendto(message.encode(), (server_host, server_port))
        time.sleep(1)  # 1-second interval


# Function to list activer users
def list_of_active_users(username, client_socket, server_host, server_port):
    # Create the message to request active peers
    lap_message = f"ACTIVE_PEERS {username}"
    client_socket.sendto(lap_message.encode(), (server_host, server_port))

    # Receive and decode response from the server
    response, _ = client_socket.recvfrom(1024)
    message = response.decode()

    # Handle the server's response
    if message == "ACTIVE_PEERS_FAIL":
        print("Active peers request unsuccessful.")
        return

    # Parse the response to get the list of active peers
    active_peers_list = message[len("ACTIVE_PEERS "):].split(", ")

    # Filter out the current user from the list
    active_peers_list = [peer for peer in active_peers_list if peer != username]

    # Number of active peers
    number_of_peers = len(active_peers_list)

    # Display active peers or a message if there are none
    if number_of_peers > 0:
        peer_label = "peer" if number_of_peers == 1 else "peers"
        print(f"{number_of_peers} active {peer_label}:")
        
        for name in active_peers_list:
            print(name)
    else:
        print("No active peers found.")


# Publish function                                                                  
def publish_file(username, client_socket, server_host, server_port, filename, tcp_port):
    message = f"PUBLISH {username} {filename} {tcp_port}"
    client_socket.sendto(message.encode(), (server_host, server_port))

    try:
        response, _ = client_socket.recvfrom(1024)
        if response.decode() == "PUB_SUCCESS":
            print(f"File published successfully.")

        elif response.decode() == "PUB_ALREADY":               
            print(f"File published successfully.")

        elif response.decode() == "PUB_FAIL":
            print("File publish unsuccesful")

    except socket.timeout:
        print("Publish request timed out.")


# Unpublish function
def unpublish_file(username, client_socket, server_host, server_port, filename, tcp_port):
    message = f"UNPUBLISH {username} {filename} {tcp_port}"
    client_socket.sendto(message.encode(), (server_host, server_port))

    try:
        response, _ = client_socket.recvfrom(1024)
        if response.decode() == "UNPUB_SUCCESS":
            print(f"File unpublished successfully.")

        elif response.decode() == "UNPUB_FAIL":
            print("File unpublishing failed")

    except socket.timeout:
        print("Publish request timed out.")


# Listed published files function
def listed_published_files(username, client_socket, server_host, server_port):
    # Create the message to request the list of published files
    request_message = f"LIST_FILES {username}"
    client_socket.sendto(request_message.encode(), (server_host, server_port))

    # Receive response from the server
    response, _ = client_socket.recvfrom(1024)
    message = response.decode()

    # Process the server's response
    if message.startswith("PUBLISHED_FILES"):
        # Extract the list of files from the message
        files_list = message[len("PUBLISHED_FILES "):].strip()  # Remove any trailing whitespace
        file_names = files_list.split(", ") if files_list else []  # Split into a list

        number_of_uploads = len(file_names)

        if number_of_uploads == 1:
            print(f"{number_of_uploads} file published:")
            for name in file_names:
                print(name)
        else:
            print(f"{number_of_uploads} files published:")
            for name in file_names:
                print(name)

    elif message == "FAIL_PUBLISHED_FILES":
        print("No file published")
    
    else:
        print("No file published")


# Search for files published by active peers
def query_active_peers_files(substring, username, client_socket, server_host, server_port):
    # Create the message to request the list of files containing the substring
    request_message = f"SEARCH_FILES {substring} {username}"
    client_socket.sendto(request_message.encode(), (server_host, server_port))

    # Receive response from the server
    response, _ = client_socket.recvfrom(1024)
    message = response.decode()

    # Process the server's response
    if message.startswith("FAIL"):
        print(f"No files found")

    elif message.startswith("FOUND_FILES"):
        # Extract the list of files from the message
        files_list = message[len("FOUND_FILES "):].strip()
        file_names = files_list.split(", ") if files_list else []

        number_of_matches = len(file_names)

        if number_of_matches > 0:
            print(f"{number_of_matches} file(s) found containing '{substring}':")
            for name in file_names:
                print(name)
        else:
            print(f"No files found")
    else:
        print(f"No files found")


# Function to query the server for an active peer with a file and download it
def query_peer_for_file(filename, username, client_socket, server_host, server_port):
    query_message = f"QUERY_FILE {filename} {username}"
    client_socket.sendto(query_message.encode(), (server_host, server_port))

    try:
        response, _ = client_socket.recvfrom(1024)
        response_message = response.decode()

        if response_message.startswith("QUERY_SUCCESS"):
            _, peer_ip, peer_port = response_message.split(" ")
            peer_port = int(peer_port)

            # download file from peer
            download_file_from_peer(filename, peer_ip, peer_port)
            
        else:
            print("File not found or no active peer available.")
    except socket.timeout:
        print("Query request timed out.")


# function do download file from peer
def download_file_from_peer(filename, peer_ip, peer_port):
    try:
        # Create a TCP socket to connect to the peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            # Connect to the peer
            tcp_socket.connect((peer_ip, peer_port))

            # Debug statement
            # print(f"Connected to {peer_ip}:{peer_port}")

            # Send the download request
            request = f"DOWNLOAD {filename}"
            tcp_socket.sendall(request.encode())

            # Open a local file to save the downloaded data
            with open(f"{filename}", "wb") as file:
                # Debug statement
                # print(f"Downloading {filename}...")
                
                # Receive the file data in chunks of 1024 bytes
                while True:
                    chunk = tcp_socket.recv(1024)
                    
                    if not chunk:  # If no more data, break out of the loop
                        break

                    file.write(chunk)  # Write the received chunk to the file

            print(f"{filename} downloaded successfully.")

    except Exception as e:
        print(f"Error downloading file: {e}")


# Main function to bring it all together
def main():

    server_host, server_port = get_server_info()
    
    client_socket = create_socket()

    # Loop until successful authentication
    authenticated = False
    username, password = get_user_credentials()                                                     # yoda wise@!man, c3p0 droid#gold, chewy wookie+aaaawww

    while not authenticated:
        if authenticate_with_server(client_socket, server_host, server_port, username, password):
            print("Welcome to BitTrickle!")
            authenticated = True  # Exit the loop on success
        else:
            print("Authentication failed. Please try again.")
            username, password = get_user_credentials()


    # Start a TCP port that listens in a seperate thread
    tcp_port = get_tcp_port(username)
    tcp_server_thread = threading.Thread(target=start_file_server, args=(tcp_port,))
    tcp_server_thread.daemon = True  # Daemonize thread
    tcp_server_thread.start()

    # Start the heartbeat mechanism in a separate thread
    heartbeat_thread = threading.Thread(target=heart_beat_mechanism, args=(username, client_socket, server_host, server_port))
    heartbeat_thread.daemon = True  # Daemonize thread
    heartbeat_thread.start()

    # Command handling loop
    print("Available commands are: get, lap, lpf, pub, sch, unp, xit")
    while True:
        # Get user input
        command = input("> ").strip() 
        if command in ['get', 'lap', 'lpf', 'sch', 'unp', 'xit'] or command.startswith("pub ") or command.startswith("unp ") or command.startswith("sch ") or command.startswith("get "):
            
            # xit - Exit function
            if command == 'xit':
                print("Goodbye")
                break  

            # List of active users function
            if command == 'lap':
                list_of_active_users(username, client_socket, server_host, server_port)

            # Publish command
            if command.startswith("pub "):
                _, filename = command.split(maxsplit=1)
                publish_file(username, client_socket, server_host, server_port, filename, tcp_port)

            # Unpublish command
            if command.startswith("unp "):
                _, filename = command.split(maxsplit=1)
                unpublish_file(username, client_socket, server_host, server_port, filename, tcp_port)
            
            # List of published files function
            if command == 'lpf':
                listed_published_files(username, client_socket, server_host, server_port)
            
            # Search for files published by active peers
            if command.startswith("sch "):
                _, substring = command.split(maxsplit=1)
                query_active_peers_files(substring, username, client_socket, server_host, server_port)
            
            # Get a file command
            if command.startswith("get "):
                _, filename = command.split(maxsplit=1)
                query_peer_for_file(filename, username, client_socket, server_host, server_port)

        else:
            print("Invalid command. Please enter one of: get, lap, lpf, pub, sch, unp, xit")

    client_socket.close()

# Run the main function
if __name__ == "__main__":
    main()