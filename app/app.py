import socketserver

from kubernetes import client, config
from http.server import BaseHTTPRequestHandler
from prettytable import PrettyTable
from urllib.parse import urlparse, parse_qs


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, kube_config, *args, **kwargs):
        self.kube_config = kube_config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Catch all incoming GET requests"""

        # Parse URL to get query variable if any
        seperator = self.path.find('?')
        url_path = self.path[:seperator] if seperator != -1 else self.path
        query_vars = parse_qs(urlparse(self.path).query)

        if self.path == "/healthz":
            self.healthz()

        elif url_path == "/deployments/status":
            # If namespace has been providedin the query string, then use it to filter deployments
            if query_vars.get('namespace'):
                self.deployment_status(query_vars.get('namespace')[0])
            else:
                self.deployment_status()

        elif url_path == "/networkpolicies":
            self.get_network_polices()

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

    def deployment_status(self, namespace=None):
        """Responds with the status of the deployment"""
        config.load_kube_config(self.kube_config)
        kube_api_client = client.AppsV1Api()
        print(namespace)
        if namespace is None:
            deployments = kube_api_client.list_deployment_for_all_namespaces()
        else:
            deployments = kube_api_client.list_namespaced_deployment(namespace)

        table = PrettyTable(['Deployment Name', 'Expected Replicas', 'Ready Replicas', 'Unavailable Replicas'])
        for deployment in deployments.items:
            table.add_row([deployment.metadata.name, deployment.status.replicas, deployment.status.ready_replicas,
                           deployment.status.unavailable_replicas])

        self.respond(200, table.get_string())

    def get_network_polices(self):
        config.load_kube_config(self.kube_config)
        kube_api_client = client.NetworkingV1Api()
        network_policies = kube_api_client.list_network_policy_for_all_namespaces()
        print (network_policies)
        self.respond(200, **network_policies.items)

    def disable_traffic(self):
        #kube_api_client = client.NetworkingV1alpha1Api
        kube_api_client = client.CustomObjectsApi()
        kube_api_client.create_cluster_custom_object()
        #from kubernetes.client import CustomObjectsApi
        group = "crd.projectcalico.org"
        v = "v3"
        plural = "networkpolicies"
        #kube_api_client.
        global_network_sets = kube_api_client.list_cluster_custom_object(group, v, plural)
        print(global_network_sets)
        # kube_api_client.create_namespaced_custom_object(
        #     group="projectcalico.org",
        #     version="v3",
        #     namespace="target-namespace",
        #     plural="networkpolicies",
        #     body=calico_policy_object
        # )

        # api_response = api_instance.create_namespaced_custom_object(
        #     group="crd.projectcalico.org",
        #     version="v1",
        #     namespace="default",
        #     plural="networkpolicies",
        #     body=calico_policy,
        #     pretty=True
        # )


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
