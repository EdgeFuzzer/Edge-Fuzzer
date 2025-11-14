"""
Connection Manager Module

This module handles socket communication, port management, and message
formatting for the fuzzing framework. It manages the connection between
the fuzzing application and the SmartThings Edge Driver hub.
"""

import socket
import json
import psutil
import time
import os
from types import SimpleNamespace
from typing import Optional, Dict, Any

from config.constants import (
    SOCKET_BUFFER_SIZE,
    SOCKET_RESPONSE_BUFFER_SIZE,
    HTTP_CONTENT_TYPE_JSON,
    HTTP_OK,
    HTTP_BAD_REQUEST
)


def check_and_close_port(port: int) -> None:
    """
    Check if a port is in use and attempt to close it.
    
    This function finds any process using the specified port and attempts
    to terminate it to free up the port for the fuzzing application.
    
    Args:
        port: The port number to check and free
    """
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port:
            pid = conn.pid
            try:
                process = psutil.Process(pid)
                process.terminate()
                print(f"Port {port} was in use and has been closed (process {pid} terminated).")
            except psutil.AccessDenied:
                print(f"Access denied: Unable to terminate process with PID {pid}. "
                      f"You might need elevated permissions.")
            except psutil.NoSuchProcess:
                print(f"Process with PID {pid} no longer exists.")
            except psutil.ZombieProcess:
                print(f"Process with PID {pid} is a zombie process and cannot be terminated.")
            return
    
    print(f"Port {port} is not in use.")


def start_server(ip: str, port: int) -> int:
    """
    Start a server socket to receive the port number from the fuzzing app.
    
    The fuzzing app will connect to this server and send a port number
    that will be used for subsequent communication.
    
    Args:
        ip: IP address to bind the server to
        port: Port number to bind the server to
        
    Returns:
        The port number received from the fuzzing app
    """
    server_socket = None
    
    # Ensure the port is available
    check_and_close_port(port)
    
    while True:
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((ip, port))
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"Port {port} is already in use. Trying to free it...")
                check_and_close_port(port)
                time.sleep(1)
            else:
                raise
    
    server_socket.listen(5)
    print(f"Start the server on fuzzing app and listening on {ip}:{port}...")
    
    # Wait for connection from fuzzing app
    while True:
        client_socket, addr = server_socket.accept()
        
        try:
            while True:
                data = client_socket.recv(SOCKET_BUFFER_SIZE)
                if not data:
                    break
                    
                decoded_data = data.decode()
                print(f"Received: {decoded_data}")
                
                try:
                    port_num = int(decoded_data)
                    print(f'Port number received: {port_num}')
                    
                    # Send HTTP response with port number
                    response = (f"HTTP/1.1 {HTTP_OK}\r\n"
                              f"Content-Length: {len(str(port_num))}\r\n\r\n"
                              f"{port_num}")
                    
                    # Send response in chunks
                    response_chunks = [response[i:i+10] for i in range(0, len(response), 10)]
                    for chunk in response_chunks:
                        client_socket.sendall(chunk.encode())
                    break
                except ValueError:
                    print("Invalid port number received.")
                    response = f"HTTP/1.1 {HTTP_BAD_REQUEST}\r\nContent-Length: 0\r\n\r\n"
                    client_socket.sendall(response.encode())
        finally:
            client_socket.close()
            print("Connection closed with", addr)
        break
    
    return port_num


def receive_response(ip: str, port: int) -> Optional[Dict[str, Any]]:
    """
    Receive and parse JSON response from the hub.
    
    This function sets up a server socket to receive responses from the
    SmartThings Edge Driver hub after test case execution.
    
    Args:
        ip: IP address to bind the server to
        port: Port number to bind the server to
        
    Returns:
        Parsed JSON response dictionary, or None if parsing fails
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip, port))
    server_socket.listen(5)
    print(f"Listening on {ip}:{port}...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected by {addr}")
        
        try:
            data = b""
            while True:
                part = client_socket.recv(SOCKET_BUFFER_SIZE)
                data += part
                if len(part) < SOCKET_BUFFER_SIZE:
                    break
            
            if data:
                decoded_data = data.decode()
                print(f"Received: {decoded_data}")
                
                # Parse HTTP response
                header, _, body = decoded_data.partition("\r\n\r\n")
                if body:
                    try:
                        json_data = json.loads(body)
                        print("JSON data received successfully.")
                        client_socket.sendall(b"JSON received successfully.")
                        return json_data
                    except json.JSONDecodeError as e:
                        print(f"Failed to decode JSON: {e}")
                        client_socket.sendall(b"Invalid JSON received.")
                else:
                    print("No JSON body received.")
                    client_socket.sendall(b"No JSON body received.")
        finally:
            client_socket.close()
    
    return None


def build_json_request(fuzzing_api_name: str, test_case: list) -> SimpleNamespace:
    """
    Build a JSON request object from test case data.
    
    Args:
        fuzzing_api_name: Name of the API being fuzzed
        test_case: List containing test case data in format:
                   [Test_Case, API_Name, Function_Name, Description, Code_Snippets, Pre-operation_Python]
        
    Returns:
        SimpleNamespace object representing the JSON request
    """
    json_request = {
        "Test_Case": test_case[0],
        "API_Name": fuzzing_api_name,
        "Function_Name": test_case[2],
        "Description": test_case[3],
        "Code_Snippets": test_case[4],  # List of code snippets
    }
    return SimpleNamespace(**json_request)


def send_message(ip: str, port: int, json_message: str) -> Optional[Dict[str, Any]]:
    """
    Send a JSON message to the hub and receive the response.
    
    This function establishes a connection to the SmartThings Edge Driver hub,
    sends a test case as JSON, and receives the execution response.
    
    Args:
        ip: IP address of the hub
        port: Port number of the hub
        json_message: JSON string containing the test case
        
    Returns:
        Parsed JSON response dictionary, or None if communication fails
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((ip, port))
        
        # Build HTTP POST request
        request = (f"POST / HTTP/1.1\r\n"
                  f"Host: {ip}\r\n"
                  f"Content-Type: {HTTP_CONTENT_TYPE_JSON}\r\n"
                  f"Content-Length: {len(json_message)}\r\n\r\n"
                  f"{json_message}")
        
        client_socket.sendall(request.encode('utf-8'))
        
        # Receive response
        response = ''
        while True:
            chunk = client_socket.recv(SOCKET_RESPONSE_BUFFER_SIZE)
            if not chunk:
                break
            response += chunk.decode('utf-8')
        
        # Parse HTTP response
        if "\r\n\r\n" in response:
            header, body = response.split("\r\n\r\n", 1)
            if body.strip():
                try:
                    json_response = json.loads(body)
                    print(f"Response received: {json_response} \n")
                    return json_response
                except json.JSONDecodeError as json_err:
                    print(f"JSON decoding error: {json_err}")
            else:
                print("Received an empty body.")
        else:
            print("Invalid HTTP response format.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client_socket.close()
    
    return None

