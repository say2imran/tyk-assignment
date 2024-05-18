import socketserver

from kubernetes import client, config
from http.server import BaseHTTPRequestHandler


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, kube_config, *args, **kwargs):
        self.kube_config = kube_config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Catch all incoming GET requests"""
        if self.path == "/healthz":
            self.healthz()
        else:
            self.send_error(404)

    def healthz(self):
        """Responds with the health status of the application"""
        print(self.kube_config)
        self.respond(200, "ok")

    def respond(self, status: int, content: str):
        """Writes content and status code to the response socket"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(bytes(content, "UTF-8"))

    def deployment_status(self, namespace='all'):
        """Responds with the status of the deployment"""
        self.respond(200, "ok")


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

