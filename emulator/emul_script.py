import subprocess
import re
import yaml


# Method for capturing necessary info out of the source code
def search_and_assign(filename, pattern):
    try:
        with open(filename, 'r') as file:
            for line in file:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)
        return None
    except FileNotFoundError:
        println(f"Error: File '{filename}' not found.")
        return None


# Method for creating a yaml file 
def config_generator(service_name, app_dir, image_name, http_port):
    docker_config = {
        "services": {
            "odgm": {
                "network_mode": "host",
                "image": "harbor.129.114.109.85.nip.io/oaas/odgm",
                "environment": {
                    "RUST_LOG": "INFO",
                    "ODGM_HTTP_PORT": "10001",
                    "ODGM_CLASS": f"example.{extracted_class}"
                }
            },
            "dev-pm": {
                "network_mode": "host",
                "image": "harbor.129.114.109.85.nip.io/oaas/dev-pm",
                "environment": {
                    "HTTP_PORT": "10002",
                    "RUST_LOG": "INFO",
                    "PM_CLS_LIST": pm_cls_list
                }
            },
            "grpcui": {
                "image": "fullstorydev/grpcui",
                "network_mode": "host",
                "command": [
                    "-plaintext",
                    "-port",
                    "18080",
                    "localhost:10001"
                ]
            },
            "funcion1": {
            }
        }
    }

    with open("docker-compose.yml", "w") as file:
        yaml.dump(docker_config, file, default_flow_style=False, sort_keys=False)


# Main method 
if __name__ == "__main__":
    println("This is an emulator developed for testing a program within an isolated OaaS-IoT platform.\n\
            Note that docker should be running in the background to successfully deploy an emulated environment")

    source_file = input("Type your file name below. Specify the absolute path if necessary:\n")

    # Create an configuration (yaml) file
    config_generator(source_file)

    # Establish an emulator environment
    docker_file = "docker-compose.yml"
    command = "docker compose -f {file_name} up"
    process = subprocess.run(["powershell", "-Command", command])

    while True:
        # Receiving user command
        command = input("Type your command below, \"quit\" to terminate the program:\n")
        # Terminate the emulator if the user input is "quit"
        if command == "quit":
            break

        # Execute the command 
        process = subprocess.run(["powershell", "-Command", command])
