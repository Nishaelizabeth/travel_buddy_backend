import socket

def find_available_port(start_port=8000, max_port=9000):
    """Find an available port by trying ports in sequence."""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Setting a timeout to avoid hanging
            sock.settimeout(0.1)
            # Returns 0 if successful, error code otherwise
            result = sock.connect_ex(('127.0.0.1', port))
            if result != 0:  # If connection failed, port is available
                return port
    return None

if __name__ == "__main__":
    port = find_available_port()
    if port:
        print(f"Available port found: {port}")
        # Write the port to a file for other scripts to use
        with open('available_port.txt', 'w') as f:
            f.write(str(port))
    else:
        print("No available ports found")
