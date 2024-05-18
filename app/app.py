import socketserver

from kubernetes import client, config
from http.server import BaseHTTPRequestHandler
from prettytable import PrettyTable


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, kube_config, *args, **kwargs):
        self.kube_config = kube_config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Catch all incoming GET requests"""
        if self.path == "/healthz":
            self.healthz()
        elif self.path == "/deployment/status":
            self.deployment_status()
        # elif self.path == "/deployment/status":
        #     self.deployment_status()
        else:
            self.send_error(404)

    def healthz(self):
        """Responds with the health status of the application"""
        self.respond(200, "ok")

    def respond(self, status: int, content: str):
        """Writes content and status code to the response socket"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(bytes(content, "UTF-8"))

    def deployment_status(self, namespace='all'):
        """Responds with the status of the deployment"""
        config.load_kube_config(self.kube_config)
        kube_api_client = client.AppsV1Api()

        if namespace == 'all':
            deployments = kube_api_client.list_deployment_for_all_namespaces()
        else:
            deployments = kube_api_client.list_namespaced_deployment(namespace)

        table = PrettyTable(['Deployment Name', 'Expected Replicas', 'Ready Replicas', 'Unavailable Replicas'])
        for deployment in deployments.items:
            table.add_row([deployment.metadata.name, deployment.status.replicas, deployment.status.ready_replicas,
                           deployment.status.unavailable_replicas])

        self.respond(200, table.get_string())


def get_kubernetes_version(api_client: client.ApiClient) -> str:
    """
    Returns a string GitVersion of the Kubernetes server defined by the api_client.

    If it can't connect an underlying exception will be thrown.
    """
    version = client.VersionApi(api_client).get_code()
    return version.git_version


def start_server(address, kube_config):
    """
    Launches an HTTP server with handlers defined by AppHandler class and blocks until it's terminated.

    Expects an address in the format of `host:port` to bind to.

    Throws an underlying exception in case of error.
    """
    try:
        host, port = address.split(":")
    except ValueError:
        print("invalid server address format")
        return

    with socketserver.TCPServer((host, int(port)), lambda *args, **kwargs: AppHandler(kube_config, *args, **kwargs)) as httpd:
        print("Server listening on {}".format(address))
        httpd.serve_forever()

